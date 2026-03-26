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


class WriterAgent(BaseAgent):
    name = "WriterAgent"

    def __init__(self, task_id: str, start_chapter: int | None = None, end_chapter: int | None = None):
        super().__init__(task_id)
        self.start_chapter = start_chapter  # 仅重写从该章到结尾时使用
        self.end_chapter = end_chapter  # 若与 start_chapter 同时指定，则只写 [start_chapter, end_chapter] 闭区间

    def run(self) -> None:
        try:
            def _extract_audit_segments_for_ch(audit_text: str, chapter_index: int) -> str:
                """
                从审计避免项文本中抽取与指定章节相关的片段。
                以“第X章”作为锚点切段，避免整份文本截断后导致关键信息缺失。
                """
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
                # 保底：若没抽到指定章节片段，则退化使用开头部分
                if not joined:
                    joined = audit_text.strip()[:800]
                return joined

            outline_list = _get_outline(self.task_id)
            # 章节数由大纲/目录决定；若配置有 override 则用配置（如测试时 TOTAL_CHAPTERS=5）
            total_chapters = getattr(settings, "total_chapters", 0) or 0
            if total_chapters <= 0:
                total_chapters = max(1, len(outline_list))
            total_chapters = min(total_chapters, len(outline_list)) if outline_list else total_chapters
            max_write = getattr(settings, "max_chapters_to_write", 0) or 0
            if max_write > 0:
                total_chapters = min(total_chapters, max_write)
            words_per_chapter = getattr(settings, "words_per_chapter", 10000) or 10000
            # 优先使用趋势分析中的建议单章字数
            trend_json = _task_dir(self.task_id) / "output" / "trend" / "trend_analysis.json"
            if trend_json.exists():
                try:
                    import json as _json
                    td = _json.loads(trend_json.read_text(encoding="utf-8"))
                    w = int(td.get("suggested_words_per_chapter") or 0)
                    if 500 <= w <= 10000:
                        words_per_chapter = w
                except Exception:
                    pass

            start = self.start_chapter or 1
            end = self.end_chapter if getattr(self, "end_chapter", None) is not None else total_chapters
            end = min(end, total_chapters)
            if start > 1:
                # 重写从 start 到结尾，需要上一章摘要
                prev_path = _task_dir(self.task_id) / "output" / "chapters" / f"ch_{start-1:02d}.md"
                if prev_path.exists():
                    prev_text = prev_path.read_text(encoding="utf-8")[:2000]
                    prev_summary = prev_text[-800:] if len(prev_text) > 800 else prev_text
                else:
                    prev_summary = ""
            else:
                prev_summary = ""

            task_d = _task_dir(self.task_id)
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
                # 本次审计文件体量通常不大，避免过早截断导致后续章节修复缺失
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

                # 本章反馈（打分/审计）：用于判断是否走修订模式
                ch_feedback_path = task_d / "output" / "score" / f"chapter_feedback_ch_{ch:02d}.md"
                ch_feedback = ""
                if ch_feedback_path.exists():
                    ch_feedback = ch_feedback_path.read_text(encoding="utf-8", errors="replace")[:1500]
                existing_ch_path = task_d / "output" / "chapters" / f"ch_{ch:02d}.md"
                existing_content = ""
                if existing_ch_path.exists():
                    existing_content = existing_ch_path.read_text(encoding="utf-8", errors="replace")
                feedback_combined = (ch_feedback or "") + " " + (audit_avoid or "")
                # 当审计避免项包含“矛盾/混淆/遗漏/断裂/不完整”等结构性问题时，
                # 只做局部修改往往无法真正修复（容易留下残留错误），改为整章重写更稳。
                # 注意：审计文本里“衔接/过渡/跳跃”等也常伴随“断裂/漏洞”出现，这里一并收紧触发条件。
                force_full_rewrite = any(
                    k in feedback_combined
                    for k in (
                        "内部矛盾",
                        "逻辑矛盾",
                        "矛盾",
                        "混淆",
                        "遗漏",
                        "未回收",
                        "未完成",
                        "不完整",
                        "断裂",
                        "衔接",
                        "过渡",
                        "跳跃",
                        "生硬",
                        "漏洞",
                        "伏笔",
                        "解释",
                        "解释缺失",
                        "规则",
                        "触发条件",
                        "限制范围",
                        "时间线",
                        "数量",
                        "平台概念",
                    )
                )
                use_revise = bool(
                    existing_content.strip()
                    and (ch_feedback or audit_avoid)
                    and not force_full_rewrite
                )

                if use_revise:
                    # 仅修改不通过部分，保留其余内容
                    user_content = (
                        f"以下为第{ch}章当前正文，审核/打分未通过。请仅根据意见修改未通过的部分，保留其余内容；若意见中明确提到章节内部逻辑矛盾则可整章重写。\n\n"
                        f"【审核/打分意见】\n{feedback_combined[:2500]}\n\n"
                        f"【当前正文】\n{existing_content[:6000]}\n\n"
                        f"请直接输出修订后的完整正文（可含 # 第{ch}章），不要解释。字数尽量不少于 {words_per_chapter} 字。"
                    )
                    prompt = [
                        {"role": "system", "content": "你是中文网文作者。根据审核意见只修改不通过的部分，尽量保留原文；只输出修订后的完整正文，不要解释。"},
                        {"role": "user", "content": user_content},
                    ]
                    content = llm.chat(prompt, temperature=0.5, max_tokens=8192)
                else:
                    audit_avoid_for_ch = _extract_audit_segments_for_ch(audit_avoid, ch)
                    # 对同一章节的修复清单做二次截断，避免 prompt 过长影响模型重点。
                    audit_avoid_for_ch = audit_avoid_for_ch[:2200]
                    user_content = f"""请严格按照章节目录写本小说的第{ch}章正文，要求：
- 字数：不少于 {words_per_chapter} 字（尽量写满，保证情节完整）
- 章节标题/核心事件：{title} — {event}
- 章末钩子/悬念：{hook}
- 与上章衔接：{connection}
- 风格：节奏快、短句为主、对话占比高；开头 1–2 段要有钩子，结尾留悬念
- 不要出现“我作为AI”等字样；只输出正文，可含 Markdown 标题“第{ch}章”和段落

"""
                    if prev_summary:
                        user_content += f"【上一章结尾/摘要（请自然衔接）】\n{prev_summary[:600]}\n\n"
                    if plan_md:
                        user_content += f"【故事设定参考】\n{plan_md[:2000]}\n\n"
                    if scorer_hint:
                        user_content += f"【本轮改进要求（请在本章中体现）】\n{scorer_hint[:1200]}\n\n"
                    if audit_avoid:
                        # 将“审计避免项”明确改写为“修复清单”，避免模型误以为只是要回避表述而不做补全。
                        user_content += (
                            f"【质量审计修复清单（本章需要补全/对齐的点）】\n{audit_avoid_for_ch}\n\n"
                        )
                        user_content += (
                            "【硬性落地要求】请把以上条目当作“必须修复清单”，逐条落实到本章正文的具体过程里（对话/动作/过渡句）。"
                            "不要只写泛化结论；如果某条目描述的是“缺失过程”，必须在本章补齐到关键动作/关键句为止，"
                            "并确保下一章开头能自然接续。若某条目指出与大纲/设定矛盾（如金额、地点、人物动作），"
                            "必须改为与审计要求一致的版本。最后：章末hook必须兑现，且衔接句要能承接 connection。 \n\n"
                        )
                    if ch_feedback:
                        user_content += f"【本章打分未通过，请按以下意见重写】\n{ch_feedback}\n\n"
                    user_content += "请直接输出本章正文（可先写 # 第N章 再写内容）："

                    prompt = [
                        {"role": "system", "content": "你是中文网文作者，擅长快节奏爽文，严格按章节目录与衔接要求写作，输出正文不要解释。单章字数须达标。"},
                        {"role": "user", "content": user_content},
                    ]
                    if is_stop_requested():
                        self._set_failed("已按用户请求停止")
                        return
                    content = llm.chat(prompt, temperature=0.8, max_tokens=8192)
                write_output_file(self.task_id, f"chapters/ch_{ch:02d}.md", content)
                total_words += len(content)

                try:
                    sum_prompt = [
                        {"role": "system", "content": "你只输出 2–4 句话的情节摘要，不要其他内容。"},
                        {"role": "user", "content": f"请对以下章节内容写 2–4 句话摘要：\n{content[:2500]}"},
                    ]
                    prev_summary = llm.chat(sum_prompt, temperature=0.3, max_tokens=150)
                except Exception:
                    prev_summary = content[-1200:].replace("\n", " ") if len(content) > 1200 else content[:400].replace("\n", " ")

                time.sleep(settings.step_interval_seconds or 0.2)

            self._set_completed(
                f"第{start}–{end}章生成完成" if (start > 1 or end < total_chapters) else f"全部 {total_chapters} 章生成完成",
                total_chapters=total_chapters,
                words=total_words,
            )
        except Exception as e:
            self._set_failed(f"正文生成失败：{type(e).__name__}: {e}")
