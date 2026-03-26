# -*- coding: utf-8 -*-
"""审计 Agent：判断前后章故事性、语句连贯、符合大纲；不满足则输出需重写的章节及后续"""
import json
import time
from pathlib import Path
from app.agents.base import BaseAgent
from app.core.state import write_output_file, append_output_file, _task_dir
from app.core.config import settings
from app.core import llm


def _get_outline_summary(task_id: str) -> str:
    task_d = _task_dir(task_id)
    for name in ("planner/章节目录.json", "planner/outline.json"):
        p = task_d / "output" / name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                chs = data.get("chapters") or []
                return json.dumps([{"title": c.get("title"), "event": c.get("event")} for c in chs[:20]], ensure_ascii=False, indent=2)
            except Exception:
                pass
    return ""


def audit_chapter(task_id: str, chapter_index_1based: int) -> dict:
    """
    单章审计：判断该章与上文连贯、符合大纲、逻辑与人设一致。
    返回 {"pass": bool, "reason": str}，不通过时供流水线重写该章。
    """
    task_d = _task_dir(task_id)
    out_d = task_d / "output" / "chapters_polished"
    if not out_d.exists():
        out_d = task_d / "output" / "chapters"
    if not out_d.exists():
        return {"pass": False, "reason": "未找到章节目录"}
    ch_path = out_d / f"ch_{chapter_index_1based:02d}.md"
    if not ch_path.exists():
        return {"pass": False, "reason": "本章文件不存在"}
    outline_p = task_d / "output" / "planner" / "outline.json"
    chapters_outline = []
    if outline_p.exists():
        try:
            data = json.loads(outline_p.read_text(encoding="utf-8"))
            chapters_outline = data.get("chapters") or []
        except Exception:
            pass
    ch_outline = chapters_outline[chapter_index_1based - 1] if chapter_index_1based <= len(chapters_outline) else {}
    current_content = ch_path.read_text(encoding="utf-8", errors="replace")[:5000]
    prev_parts = []
    for i in range(1, chapter_index_1based):
        p = out_d / f"ch_{i:02d}.md"
        if p.exists():
            prev_parts.append(p.read_text(encoding="utf-8", errors="replace")[-1200:])
    prev_text = "\n\n".join(prev_parts[-3:]) if prev_parts else "（无前文）"
    plan_md = ""
    plan_file = task_d / "output" / "planner" / "策划案.md"
    if plan_file.exists():
        plan_md = plan_file.read_text(encoding="utf-8", errors="replace")[:2500]
    prompt = [
        {
            "role": "system",
            "content": "你是网文质量审计。仅判断本章：1) 与上文是否连贯、有无断裂或矛盾；2) 是否贴合大纲中本章主题/事件；3) 人设与逻辑是否一致。只输出严格 JSON：{ \"pass\": true/false, \"reason\": \"简短理由\" }",
        },
        {
            "role": "user",
            "content": f"""【策划案摘要】\n{plan_md[:2000]}\n\n【本章大纲要求】\n{json.dumps(ch_outline, ensure_ascii=False)}\n\n【前文摘要】\n{prev_text[:2000]}\n\n【当前章正文】\n{current_content}\n\n请判断本章是否与上文连贯、符合大纲、逻辑人设一致。只输出 JSON。""",
        },
    ]
    try:
        raw = llm.chat_json(prompt, temperature=0.2, max_tokens=400)
    except Exception:
        return {"pass": True, "reason": "审计调用异常，放行"}
    return {"pass": bool(raw.get("pass", True)), "reason": str(raw.get("reason") or "")}


def _chapter_index_from_stem(stem: str) -> int | None:
    """ch_01 -> 1, ch_02 -> 2"""
    if stem.startswith("ch_") and len(stem) >= 5:
        try:
            return int(stem[3:5])
        except ValueError:
            pass
    return None


class AuditorAgent(BaseAgent):
    name = "AuditorAgent"

    def __init__(self, task_id: str, only_chapter_range: tuple[int, int] | None = None):
        super().__init__(task_id)
        self.only_chapter_range = only_chapter_range  # (start_1based, end_1based) 仅审计该区间

    def run(self) -> None:
        try:
            self._set_running(0, "审计准备中...")
            task_d = _task_dir(self.task_id)
            out_d = task_d / "output" / "chapters_polished"
            if not out_d.exists():
                out_d = task_d / "output" / "chapters"
            if not out_d.exists():
                self._set_failed("审计失败：未找到可审计章节")
                return
            all_files = sorted(out_d.glob("ch_*.md"))
            range_s, range_e = self.only_chapter_range or (1, 9999)
            chapters = []
            for fp in all_files:
                idx = _chapter_index_from_stem(fp.stem)
                if idx is not None and range_s <= idx <= range_e:
                    chapters.append(fp)
            if not chapters:
                self._set_completed("指定范围内无章节，跳过审计", score=10, chapters_to_rewrite=[])
                return
            total_in_range = len(chapters)
            outline_summary = _get_outline_summary(self.task_id)

            full_text_parts = []
            for fp in chapters:
                full_text_parts.append(f"[{fp.stem}]\n{fp.read_text(encoding='utf-8')[:1500]}")
            full_sample = "\n\n".join(full_text_parts)[:12000]

            self._set_running(25, f"审计第{range_s}–{range_e}章（共{total_in_range}章）...")
            scope_hint = f"本节仅审计第{range_s}–{range_e}章；chapters_to_rewrite 只填该范围内的章节编号。" if self.only_chapter_range else ""
            prompt = [
                {"role": "system", "content": "你是网文质量审计。必须对以下所有审核项逐一检查，不要有一项不通过就停止；每一项都要检查并填写完整，把所有不通过的原因都列在对应的 issues 列表中。"},
                {"role": "user", "content": f"""请对以下小说章节做质量审计。要求：对 1–5 项全部逐项审核，不要发现一项有问题就停止；每一项的检查结果都要填写，不通过的原因都列在对应列表中。

**重写范围原则（重要）**：
- chapters_to_rewrite 只填「确实需要重写」的章节编号（整数），尽量少填；
- 不要为「已通过、仅后续需衔接」的章节编号；除非该章存在明显逻辑错误/硬伤；
- 若问题主要是「与后文衔接/因果断裂」，可从最早有问题的一章起列编号，但不要把明显无问题的章节也列入；
- 不要为了省事把整段区间都标成需重写。

审核项：
1. 前后章故事是否连贯、语句是否通顺（有无断裂、矛盾）→ coherence_issues
2. 是否符合大纲要求（每章核心事件是否与目录一致）→ outline_violations
3. 人设是否一致 → ooc_issues
4. 伏笔是否合理、有无逻辑漏洞 → logic_issues、plot_hole_issues
5. 以上各项均需给出 scores 中对应分数

{scope_hint}

【章节目录摘要】\n{outline_summary[:2000]}\n\n【正文样本】\n{full_sample[:9000]}

输出 JSON（所有列表都要按实际检查结果填完整，无问题可填 []）：
{{
  "coherence_issues": ["前后章不连贯的具体位置与描述", ...],
  "logic_issues": ["逻辑漏洞或时间线错误", ...],
  "ooc_issues": ["人设崩坏或言行不符", ...],
  "plot_hole_issues": ["伏笔未闭环或遗漏", ...],
  "outline_violations": ["与大纲不符的章节及说明", ...],
  "chapters_to_rewrite": [ 本节内确需重写的章节编号，尽量少 ],
  "scores": {{ "coherence": 0-10, "logic": 0-10, "character_consistency": 0-10, "plot_completeness": 0-10, "outline_compliance": 0-10, "overall": 0-10 }},
  "summary": "一段总评（2–4句），可汇总所有不通过项"
}}

只输出 JSON。"""},
            ]
            audit_data = llm.chat_json(prompt, temperature=0.2, max_tokens=1400)
            chapters_to_rewrite = audit_data.get("chapters_to_rewrite")
            if not isinstance(chapters_to_rewrite, list):
                chapters_to_rewrite = []
            reason_blob = (audit_data.get("summary") or "") + " " + " ".join(
                str(x) for x in (
                    (audit_data.get("coherence_issues") or [])[:3]
                    + (audit_data.get("logic_issues") or [])[:3]
                )
            )
            # 限制在本审计范围内；默认只重写列出的章节；若明确「衔接/连贯/因果/断裂」则扩展到从最早问题章到 batch 末
            if chapters_to_rewrite:
                in_range = sorted({c for c in chapters_to_rewrite if isinstance(c, int) and range_s <= c <= range_e})
                if not in_range:
                    chapters_to_rewrite = []
                else:
                    coherence_like = any(
                        k in reason_blob
                        for k in ("衔接", "连贯", "断裂", "因果", "接续", "接不上", "突兀")
                    )
                    if coherence_like:
                        chapters_to_rewrite = list(range(min(in_range), range_e + 1))
                    else:
                        chapters_to_rewrite = list(range(min(in_range), max(in_range) + 1))
            audit_data["chapters_to_rewrite"] = chapters_to_rewrite

            self._set_running(70, "生成审计报告...")
            report_lines = [
                "# 质量审计报告",
                "",
                "## 综合评分",
                f"- 前后章连贯性: {audit_data.get('scores', {}).get('coherence', 0)}/10",
                f"- 剧情逻辑: {audit_data.get('scores', {}).get('logic', 0)}/10",
                f"- 人设一致性: {audit_data.get('scores', {}).get('character_consistency', 0)}/10",
                f"- 伏笔/剧情完整: {audit_data.get('scores', {}).get('plot_completeness', 0)}/10",
                f"- 大纲符合度: {audit_data.get('scores', {}).get('outline_compliance', 0)}/10",
                f"- **综合: {audit_data.get('scores', {}).get('overall', 0)}/10**",
                "",
                "## 总评",
                audit_data.get("summary", ""),
                "",
                "## 需重写章节（尽量少；衔接类问题可从最早章起至本批末）",
                str(chapters_to_rewrite) if chapters_to_rewrite else "无",
                "",
                "## 连贯性问题",
            ]
            for x in audit_data.get("coherence_issues", [])[:15]:
                report_lines.append(f"- {x}")
            report_lines.extend(["", "## 逻辑问题"])
            for x in audit_data.get("logic_issues", [])[:15]:
                report_lines.append(f"- {x}")
            report_lines.extend(["", "## 大纲不符"])
            for x in audit_data.get("outline_violations", [])[:10]:
                report_lines.append(f"- {x}")
            report_lines.extend(["", "## 人设/OOC 问题"])
            for x in audit_data.get("ooc_issues", [])[:10]:
                report_lines.append(f"- {x}")
            report_lines.extend(["", "## 伏笔/漏洞"])
            for x in audit_data.get("plot_hole_issues", [])[:10]:
                report_lines.append(f"- {x}")
            report_md = "\n".join(report_lines)
            write_output_file(self.task_id, "audit/质量审计报告.md", report_md)
            write_output_file(self.task_id, "audit/audit_result.json", json.dumps(audit_data, ensure_ascii=False, indent=2))
            # 质量审计结论写入单一日志文件（随任务消亡）
            from datetime import datetime
            log_path = "audit/audit_log.md"
            try:
                log_fp = _task_dir(self.task_id) / "output" / log_path
                if not log_fp.exists():
                    write_output_file(self.task_id, log_path, "# 质量审计日志\n\n")
                conclusion = "通过" if not chapters_to_rewrite else "需重写"
                rewrite_reason = audit_data.get("summary", "") or "无"
                if chapters_to_rewrite:
                    rewrite_reason += f"\n需重写章节：第 {min(chapters_to_rewrite)}–{max(chapters_to_rewrite)} 章"
                block = (
                    f"## 第 {range_s}–{range_e} 章审计\n"
                    f"- **时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"- **审核章节**：第 {range_s}–{range_e} 章\n"
                    f"- **结论**：{conclusion}\n"
                    f"- **重写原因**：{rewrite_reason}\n\n"
                )
                append_output_file(self.task_id, log_path, block)
            except Exception:
                pass
            overall = audit_data.get("scores", {}).get("overall", 0)
            msg = f"审计完成，综合评分 {overall}/10"
            if chapters_to_rewrite:
                msg += f"；第{chapters_to_rewrite[0]}章及后续需重写"
            self._set_completed(msg, score=overall, chapters_to_rewrite=chapters_to_rewrite)
        except Exception as e:
            self._set_failed(f"审计失败：{type(e).__name__}: {e}")
