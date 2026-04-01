# -*- coding: utf-8 -*-
import json
import time
import re
from pathlib import Path
from app.agents.base import BaseAgent
from app.core.state import write_output_file, _task_dir, is_stop_requested
from app.core.config import settings
from app.core import llm


def _get_outline(task_id: str):
    """优先章节目录（审核通过），否则 outline.json"""
    task_d = _task_dir(task_id)
    out = task_d / "output" / "planner"
    for name in ("章节目录.json", "outline.json"):
        p = out / name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get("chapters") or []
            except Exception:
                pass
    return []


def _extract_spine_for_chapter(spine_md: str, ch: int) -> str:
    """从故事总纲中提取与当前章节相关的段落"""
    if not spine_md:
        return ""
    lines = spine_md.split("\n")
    ch_marker = f"第{ch}章"
    ch_marker2 = f"第 {ch} 章"
    found = []
    capturing = False
    for ln in lines:
        if ch_marker in ln or ch_marker2 in ln:
            capturing = True
        elif capturing and ln.startswith("#"):
            break
        if capturing:
            found.append(ln)
    if found:
        return "\n".join(found)[:1500]
    batch_idx = (ch - 1) // 3
    start_ln = batch_idx * 20
    end_ln = min(start_ln + 30, len(lines))
    return "\n".join(lines[start_ln:end_ln])[:1500]


class WriterAgent(BaseAgent):
    name = "WriterAgent"

    def __init__(self, task_id: str, start_chapter: int | None = None, end_chapter: int | None = None):
        super().__init__(task_id)
        self.start_chapter = start_chapter
        self.end_chapter = end_chapter

    def run(self) -> None:
        try:
            def _extract_audit_segments_for_ch(audit_text: str, chapter_index: int) -> str:
                if not audit_text.strip():
                    return ""
                chap_re = re.compile(r"第\s*(\d+)\s*章")
                matches = list(chap_re.finditer(audit_text))
                if not matches:
                    return ""
                segments: list[str] = []
                for i, m in enumerate(matches):
                    try:
                        chap = int(m.group(1))
                    except Exception:
                        continue
                    if chap != chapter_index:
                        continue
                    seg_start = m.start()
                    seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(audit_text)
                    seg = audit_text[seg_start:seg_end].strip()
                    if seg:
                        segments.append(seg)
                joined = "\n".join(segments).strip()
                if not joined:
                    joined = audit_text.strip()[:800]
                return joined

            def _load_prev_chapter_half(ch_num: int) -> str:
                """加载上一章后半段原文（约50%），用于章节衔接"""
                if ch_num <= 1:
                    return ""
                prev_path = _task_dir(self.task_id) / "output" / "chapters" / f"ch_{ch_num-1:02d}.md"
                if not prev_path.exists():
                    return ""
                prev_text = prev_path.read_text(encoding="utf-8", errors="replace")
                if len(prev_text) < 500:
                    return prev_text
                half = len(prev_text) // 2
                return prev_text[half:]

            def _load_opening_chapters() -> str:
                """加载前两章全文作为引子，为后续章节提供故事基调和人物初印象"""
                chapters_dir = _task_dir(self.task_id) / "output" / "chapters"
                parts = []
                for i in (1, 2):
                    p = chapters_dir / f"ch_{i:02d}.md"
                    if p.exists():
                        text = p.read_text(encoding="utf-8", errors="replace")
                        if text.strip():
                            parts.append(f"--- 第{i}章 ---\n{text.strip()}")
                return "\n\n".join(parts)

            outline_list = _get_outline(self.task_id)
            total_chapters = getattr(settings, "total_chapters", 0) or 0
            if total_chapters <= 0:
                total_chapters = max(1, len(outline_list))
            total_chapters = min(total_chapters, len(outline_list)) if outline_list else total_chapters
            max_write = getattr(settings, "max_chapters_to_write", 0) or 0
            if max_write > 0:
                total_chapters = min(total_chapters, max_write)
            words_per_chapter = getattr(settings, "words_per_chapter", 10000) or 10000
            trend_json = _task_dir(self.task_id) / "output" / "trend" / "trend_analysis.json"
            if trend_json.exists():
                try:
                    td = json.loads(trend_json.read_text(encoding="utf-8"))
                    w = int(td.get("suggested_words_per_chapter") or 0)
                    if 500 <= w <= 10000:
                        words_per_chapter = w
                except Exception:
                    pass

            start = self.start_chapter or 1
            end = self.end_chapter if getattr(self, "end_chapter", None) is not None else total_chapters
            end = min(end, total_chapters)

            task_d = _task_dir(self.task_id)

            story_spine_md = ""
            spine_file = task_d / "output" / "planner" / "故事总纲.md"
            if spine_file.exists():
                story_spine_md = spine_file.read_text(encoding="utf-8", errors="replace")

            plan_md = ""
            plan_file = task_d / "output" / "planner" / "策划案.md"
            if plan_file.exists():
                plan_md = plan_file.read_text(encoding="utf-8", errors="replace")[:4000]

            scorer_hint = ""
            hint_file = task_d / "output" / "score" / "scorer_params_for_agents.md"
            if hint_file.exists():
                scorer_hint = hint_file.read_text(encoding="utf-8", errors="replace")[:2000]
            audit_avoid = ""
            audit_avoid_file = task_d / "output" / "audit" / "rewrite_avoid.md"
            if audit_avoid_file.exists():
                audit_avoid = audit_avoid_file.read_text(encoding="utf-8", errors="replace")[:8000]
            chapter_feedback = ""
            if start == end and start >= 1:
                cf = task_d / "output" / "score" / f"chapter_feedback_ch_{start:02d}.md"
                if cf.exists():
                    chapter_feedback = cf.read_text(encoding="utf-8", errors="replace")[:1500]

            self._set_running(0, "加载策划与大纲...")
            self._log("info", "按章节目录生成正文", {
                "total_chapters": total_chapters,
                "words_per_chapter": words_per_chapter,
                "start_chapter": start,
            })
            time.sleep(settings.step_interval_seconds or 0.2)

            total_words = 0
            for ch in range(start, end + 1):
                if is_stop_requested():
                    self._set_failed("已按用户请求停止")
                    return
                pct = (ch - start) * 100 // max(1, end - start + 1)
                self._set_running(
                    pct,
                    f"正文生成中（第{ch}章/共{total_chapters}章）",
                    current_chapter=ch,
                    total_chapters=total_chapters,
                    words=total_words,
                )
                ch_outline = outline_list[ch - 1] if ch <= len(outline_list) else {}
                event = ch_outline.get("event", "按主线推进")
                hook = ch_outline.get("hook", "留悬念")
                connection = ch_outline.get("connection", "承接上章")
                title = ch_outline.get("title", f"第{ch}章")

                ch_feedback_path = task_d / "output" / "score" / f"chapter_feedback_ch_{ch:02d}.md"
                ch_feedback = ""
                if ch_feedback_path.exists():
                    ch_feedback = ch_feedback_path.read_text(encoding="utf-8", errors="replace")[:1500]
                existing_ch_path = task_d / "output" / "chapters" / f"ch_{ch:02d}.md"
                existing_content = ""
                if existing_ch_path.exists():
                    existing_content = existing_ch_path.read_text(encoding="utf-8", errors="replace")
                feedback_combined = (ch_feedback or "") + " " + (audit_avoid or "")
                force_full_rewrite = any(
                    k in feedback_combined
                    for k in (
                        "内部矛盾", "逻辑矛盾", "矛盾", "混淆", "遗漏",
                        "未回收", "未完成", "不完整", "断裂", "衔接",
                        "过渡", "跳跃", "生硬", "漏洞", "伏笔",
                        "解释", "解释缺失", "规则", "触发条件",
                        "限制范围", "时间线", "数量", "平台概念",
                    )
                )
                use_revise = bool(
                    existing_content.strip()
                    and (ch_feedback or audit_avoid)
                    and not force_full_rewrite
                )

                prev_half = _load_prev_chapter_half(ch)
                spine_excerpt = _extract_spine_for_chapter(story_spine_md, ch)
                opening_ctx = _load_opening_chapters() if ch >= 3 else ""

                if use_revise:
                    revise_ctx = ""
                    if prev_half:
                        revise_ctx = f"\n\n【上一章后半段原文（修订后开头必须承接此处）】\n{prev_half[:2500]}\n"
                    opening_hint = ""
                    if opening_ctx:
                        opening_hint = f"\n\n【前两章引子（保持角色性格和世界观一致）】\n{opening_ctx[:4000]}\n"
                    user_content = (
                        f"以下为第{ch}章当前正文，审核/打分未通过。请仅根据意见修改未通过的部分，保留其余内容；若意见中明确提到章节内部逻辑矛盾则可整章重写。\n\n"
                        f"【审核/打分意见】\n{feedback_combined[:2500]}\n\n"
                        f"【当前正文】\n{existing_content[:6000]}\n"
                        f"{revise_ctx}{opening_hint}\n"
                        f"请直接输出修订后的完整正文（可含 # 第{ch}章），不要解释。字数尽量不少于 {words_per_chapter} 字。"
                    )
                    prompt = [
                        {"role": "system", "content": "你是中文网文作者。根据审核意见只修改不通过的部分，尽量保留原文；只输出修订后的完整正文，不要解释。"},
                        {"role": "user", "content": user_content},
                    ]
                    content = llm.chat(prompt, temperature=0.5, max_tokens=8192, timeout_s=300)
                else:
                    audit_avoid_for_ch = _extract_audit_segments_for_ch(audit_avoid, ch)
                    audit_avoid_for_ch = audit_avoid_for_ch[:2200]
                    user_content = (
                        f"请严格按照章节目录写本小说的第{ch}章正文，要求：\n"
                        f"- 字数：不少于 {words_per_chapter} 字（尽量写满，保证情节完整）\n"
                        f"- 章节标题/核心事件：{title} — {event}\n"
                        f"- 章末钩子/悬念：{hook}\n"
                        f"- 与上章衔接：{connection}\n"
                        f"- 风格：节奏快、短句为主、对话占比高；开头 1–2 段要有钩子，结尾留悬念\n"
                        f"- 不要出现\"我作为AI\"等字样；只输出正文，可含 Markdown 标题\"第{ch}章\"和段落\n"
                        f"- **极其重要**：本章开头必须自然承接上一章结尾的场景、对话或事件，不能跳跃或重复\n\n"
                    )
                    if opening_ctx:
                        user_content += f"【前两章引子（故事基调与人物初印象，写作时须保持角色性格、语言风格、世界观设定的一致性）】\n{opening_ctx[:6000]}\n\n"
                    if prev_half:
                        user_content += f"【上一章后半段原文（本章开头必须直接承接此处剧情，不要重复、不要跳跃）】\n{prev_half[:3000]}\n\n"
                    if spine_excerpt:
                        user_content += f"【故事总纲（本章对应段落，请严格遵循）】\n{spine_excerpt}\n\n"
                    if plan_md:
                        user_content += f"【故事设定参考（核心人设与世界观）】\n{plan_md[:2000]}\n\n"
                    if scorer_hint:
                        user_content += f"【本轮改进要求（请在本章中体现）】\n{scorer_hint[:1200]}\n\n"
                    if audit_avoid:
                        user_content += (
                            f"【质量审计修复清单（本章需要补全/对齐的点）】\n{audit_avoid_for_ch}\n\n"
                        )
                        user_content += (
                            "【硬性落地要求】请把以上条目当作\"必须修复清单\"，逐条落实到本章正文的具体过程里（对话/动作/过渡句）。"
                            "不要只写泛化结论；如果某条目描述的是\"缺失过程\"，必须在本章补齐到关键动作/关键句为止，"
                            "并确保下一章开头能自然接续。若某条目指出与大纲/设定矛盾（如金额、地点、人物动作），"
                            "必须改为与审计要求一致的版本。最后：章末hook必须兑现，且衔接句要能承接 connection。 \n\n"
                        )
                    if ch_feedback:
                        user_content += f"【本章打分未通过，请按以下意见重写】\n{ch_feedback}\n\n"
                    user_content += "请直接输出本章正文（可先写 # 第N章 再写内容）："

                    prompt = [
                        {"role": "system", "content": (
                            "你是中文网文作者，擅长快节奏爽文，严格按章节目录与衔接要求写作，输出正文不要解释。单章字数须达标。"
                            "角色名字必须严格按照策划案中的人设矩阵使用，不要自行编造新名字或改变已有角色名。"
                        )},
                        {"role": "user", "content": user_content},
                    ]
                    if is_stop_requested():
                        self._set_failed("已按用户请求停止")
                        return
                    content = llm.chat(prompt, temperature=0.8, max_tokens=8192, timeout_s=300)
                write_output_file(self.task_id, f"chapters/ch_{ch:02d}.md", content)
                total_words += len(content)

                time.sleep(settings.step_interval_seconds or 0.2)

            self._set_completed(
                f"第{start}–{end}章生成完成" if (start > 1 or end < total_chapters) else f"全部 {total_chapters} 章生成完成",
                total_chapters=total_chapters,
                words=total_words,
            )
        except Exception as e:
            self._set_failed(f"正文生成失败：{type(e).__name__}: {e}")
