# -*- coding: utf-8 -*-
"""
ScorerAgent：同类型对比版打分。六维打分（总分100），不达标时保留旧作并输出差异报告与重生成建议。
支持单章打分：每章写完后可调用 score_chapter() 判断是否契合大纲、连贯、合主题，不通过则重写。
"""
import json
from pathlib import Path
from app.agents.base import BaseAgent
from app.core.state import write_output_file, _task_dir
from app.core.config import settings
from app.core import llm


def score_chapter(task_id: str, chapter_index_1based: int) -> dict:
    """
    对单章进行打分：结合当前章及之前章节、故事大纲，判断是否契合大纲、与上文连贯、与主题一致。
    返回 { "pass": bool, "reason": str, "fix": [str] }，不通过时写入 chapter_feedback_ch_XX.md 供 Writer 重写。
    """
    task_d = _task_dir(task_id)
    outline_p = task_d / "output" / "planner" / "outline.json"
    if not outline_p.exists():
        return {"pass": True, "reason": "无大纲", "fix": []}
    try:
        outline_data = json.loads(outline_p.read_text(encoding="utf-8"))
        chapters_outline = outline_data.get("chapters") or []
    except Exception:
        return {"pass": True, "reason": "大纲解析失败", "fix": []}
    if chapter_index_1based < 1 or chapter_index_1based > len(chapters_outline):
        return {"pass": True, "reason": "章节超出范围", "fix": []}

    polished_d = task_d / "output" / "chapters_polished"
    raw_d = task_d / "output" / "chapters"
    content_d = polished_d if polished_d.exists() else raw_d
    ch_path = content_d / f"ch_{chapter_index_1based:02d}.md"
    if not ch_path.exists():
        return {"pass": False, "reason": "本章文件不存在", "fix": ["请重新生成本章"]}

    current_content = ch_path.read_text(encoding="utf-8", errors="replace")[:5000]
    prev_contents: list[str] = []
    for i in range(1, chapter_index_1based):
        p = content_d / f"ch_{i:02d}.md"
        if p.exists():
            prev_contents.append(p.read_text(encoding="utf-8", errors="replace")[-1500:])
    prev_text = "\n\n".join(prev_contents[-3:]) if prev_contents else "（无前文）"
    ch_outline = chapters_outline[chapter_index_1based - 1] if chapter_index_1based <= len(chapters_outline) else {}
    plan_md = ""
    plan_file = task_d / "output" / "planner" / "策划案.md"
    if plan_file.exists():
        plan_md = plan_file.read_text(encoding="utf-8", errors="replace")[:2500]

    prompt = [
        {
            "role": "system",
            "content": (
                "你是网文单章质量审核。仅判断：1) 本章是否契合故事大纲中该章的主题/事件；2) 与上文是否连贯；3) 是否与整体主题一致。"
                "只输出严格 JSON：{ \"pass\": true/false, \"reason\": \"简短理由\", \"fix\": [\"可执行修改建议1\", ...] }"
            ),
        },
        {
            "role": "user",
            "content": f"""【策划案摘要】\n{plan_md[:2000]}\n\n【本章大纲要求】\n{json.dumps(ch_outline, ensure_ascii=False)}\n\n【前文摘要（供衔接判断）】\n{prev_text[:2000]}\n\n【当前章正文】\n{current_content}\n\n请判断本章是否契合大纲、与上文连贯、与主题一致。只输出 JSON。""",
        },
    ]
    try:
        raw = llm.chat_json(prompt, temperature=0.2, max_tokens=500)
    except Exception:
        return {"pass": True, "reason": "打分调用异常", "fix": []}
    pass_ = raw.get("pass", True)
    reason = raw.get("reason") or ""
    fix = raw.get("fix") or []
    if not isinstance(fix, list):
        fix = []

    if not pass_:
        feedback_md = f"# 第{chapter_index_1based}章打分未通过\n\n**原因**：{reason}\n\n**修改建议**：\n" + "\n".join(f"- {x}" for x in fix[:8])
        write_output_file(task_id, f"score/chapter_feedback_ch_{chapter_index_1based:02d}.md", feedback_md)
    return {"pass": pass_, "reason": reason, "fix": fix}


# 六维权重（与需求一致）
DIMENSIONS = [
    ("style", "风格贴合度", 25),
    ("character", "人设一致性", 20),
    ("plot", "剧情逻辑与节奏", 20),
    ("emotion", "爽点与情绪价值", 15),
    ("language", "语言表达", 10),
    ("originality", "原创性", 10),
]
TOTAL_MAX = 100

# 等级阈值
GRADE_S = (90.0, 100.0)
GRADE_A = (80.0, 89.9)
GRADE_B = (70.0, 79.9)
GRADE_C = (60.0, 69.9)
# D: <60


def _grade(total: float) -> str:
    if total >= GRADE_S[0]:
        return "S"
    if total >= GRADE_A[0]:
        return "A"
    if total >= GRADE_B[0]:
        return "B"
    if total >= GRADE_C[0]:
        return "C"
    return "D"


def _need_regenerate(grade: str) -> bool:
    return grade in ("C", "D")


class ScorerAgent(BaseAgent):
    name = "ScorerAgent"

    def run(self) -> None:
        try:
            self._set_running(0, "打分准备中...")
            task_d = _task_dir(self.task_id)
            # 优先用定稿，其次润色稿
            novel_path = task_d / "output" / "final" / "成书_含目录可跳转.md"
            if not novel_path.exists():
                novel_path = task_d / "output" / "final" / "成书.md"
            if not novel_path.exists():
                out_d = task_d / "output" / "chapters_polished"
                if not out_d.exists():
                    out_d = task_d / "output" / "chapters"
                if not out_d.exists():
                    self._set_failed("打分失败：未找到可打分正文")
                    return
                chapters = sorted(out_d.glob("*.md"))
                novel_text = "\n\n".join(fp.read_text(encoding="utf-8") for fp in chapters[:20])
            else:
                novel_text = novel_path.read_text(encoding="utf-8", errors="replace")

            # 截断用于 API，避免超长
            sample = novel_text[:12000]
            if len(novel_text) > 12000:
                sample += "\n\n...（后续省略）"

            self._set_running(20, "六维打分中...")
            prompt = [
                {
                    "role": "system",
                    "content": "你是网文质量评分专家。以同类型热门小说为参照，对生成小说进行六维量化打分，每项保留1位小数。只输出JSON，不要其他文字。",
                },
                {
                    "role": "user",
                    "content": f"""请对以下AI生成小说样本，以同类型热门网文为参照基准，进行六维打分。参照标准：风格贴合度(25)、人设一致性(20)、剧情逻辑与节奏(20)、爽点与情绪价值(15)、语言表达(10)、原创性(10)，总分100。

输出严格按以下JSON格式（不要换行、不要注释）：
{{
  "style": 0-25,
  "character": 0-20,
  "plot": 0-20,
  "emotion": 0-15,
  "language": 0-10,
  "originality": 0-10,
  "reference_avg_style": 20-25,
  "reference_avg_character": 15-20,
  "reference_avg_plot": 15-20,
  "reference_avg_emotion": 10-15,
  "reference_avg_language": 7-10,
  "reference_avg_originality": 7-10,
  "weak_dimensions": ["得分明显低于参照的维度名，如 style, character"],
  "brief_reason": "一句话说明与参照的主要差距"
}}

【正文样本】\n{sample}
""",
                },
            ]
            raw = llm.chat_json(prompt, temperature=0.2, max_tokens=800)
            scores = {
                "style": min(25, max(0, float(raw.get("style", 0)))),
                "character": min(20, max(0, float(raw.get("character", 0)))),
                "plot": min(20, max(0, float(raw.get("plot", 0)))),
                "emotion": min(15, max(0, float(raw.get("emotion", 0)))),
                "language": min(10, max(0, float(raw.get("language", 0)))),
                "originality": min(10, max(0, float(raw.get("originality", 0)))),
            }
            total = round(sum(scores.values()), 1)
            grade = _grade(total)
            def _num(v):
                try:
                    return float(v) if v is not None else 0.0
                except (TypeError, ValueError):
                    return 0.0
            reference_avgs = {
                k: _num(raw.get(f"reference_avg_{k}")) for k in scores
            }
            weak = raw.get("weak_dimensions") or []
            brief_reason = raw.get("brief_reason") or ""

            self._set_running(60, "差异分析中...")
            diff_prompt = [
                {
                    "role": "system",
                    "content": "你是网文质量分析专家。根据各维度得分与参照平均分的差距，输出具体可落地的参数更新建议（面向StyleAgent/ReviserAgent/AuditorAgent等），只输出JSON。",
                },
                {
                    "role": "user",
                    "content": f"""生成小说六维得分：{json.dumps(scores, ensure_ascii=False)}，总分{total}，等级{grade}。参照平均分：{json.dumps(reference_avgs, ensure_ascii=False)}。弱项维度：{weak}。简要原因：{brief_reason}。

请输出差异分析与参数更新建议的JSON：
{{
  "dimension_diffs": {{ "style": 差值, "character": 差值, ... }},
  "key_shortcomings": ["重点不足1", "重点不足2"],
  "suggestions": [
    {{ "agent": "StyleAgent/ReviserAgent/AuditorAgent", "action": "具体可执行建议" }}
  ],
  "need_regenerate": true或false
}}
""",
                },
            ]
            try:
                diff_raw = llm.chat_json(diff_prompt, temperature=0.2, max_tokens=600)
            except Exception:
                diff_raw = {
                    "dimension_diffs": {k: round(scores[k] - reference_avgs.get(k, 0), 1) for k in scores},
                    "key_shortcomings": [brief_reason] if brief_reason else [],
                    "suggestions": [],
                    "need_regenerate": _need_regenerate(grade),
                }
            need_regen = diff_raw.get("need_regenerate", _need_regenerate(grade))

            report = {
                "total_score": total,
                "grade": grade,
                "dimension_scores": scores,
                "reference_avg": reference_avgs,
                "weak_dimensions": weak,
                "brief_reason": brief_reason,
                "dimension_diffs": diff_raw.get("dimension_diffs", {}),
                "key_shortcomings": diff_raw.get("key_shortcomings", []),
                "suggestions": diff_raw.get("suggestions", []),
                "need_regenerate": need_regen,
            }
            write_output_file(
                self.task_id,
                "score/scorer_report.json",
                json.dumps(report, ensure_ascii=False, indent=2),
            )
            write_output_file(
                self.task_id,
                "score/suggestions.json",
                json.dumps(
                    {
                        "need_regenerate": need_regen,
                        "suggestions": diff_raw.get("suggestions", []),
                        "key_shortcomings": diff_raw.get("key_shortcomings", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            md_lines = [
                "# ScorerAgent 打分报告",
                "",
                f"**总分**：{total}  **等级**：{grade}",
                "",
                "## 六维得分",
            ]
            for key, label, _ in DIMENSIONS:
                s = scores.get(key, 0)
                ref = reference_avgs.get(key, 0)
                md_lines.append(f"- {label}：{s}（参照约 {ref}）")
            md_lines.extend(["", "## 与参照差距", brief_reason, "", "## 重点不足"])
            for x in diff_raw.get("key_shortcomings", [])[:10]:
                md_lines.append(f"- {x}")
            md_lines.extend(["", "## 参数更新建议"])
            for s in diff_raw.get("suggestions", [])[:8]:
                md_lines.append(f"- [{s.get('agent','')}] {s.get('action','')}")
            if need_regen:
                md_lines.extend(["", "**结论**：未达标，建议保留当前作品并依建议更新参数后重生成新作。"])
            write_output_file(self.task_id, "score/打分报告.md", "\n".join(md_lines))

            msg = f"打分完成 总分{total} 等级{grade}"
            if need_regen:
                msg += "；未达标，已输出建议并保留当前作品"
            self._set_completed(msg, score=total, grade=grade, need_regenerate=need_regen)
        except Exception as e:
            self._set_failed(f"打分失败：{type(e).__name__}: {e}")
