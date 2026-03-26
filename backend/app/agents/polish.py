# -*- coding: utf-8 -*-
import time
from pathlib import Path
from app.agents.base import BaseAgent
from app.core.state import write_output_file, _task_dir
from app.core.config import settings
from app.core import llm


class PolishAgent(BaseAgent):
    name = "PolishAgent"

    def __init__(self, task_id: str, only_chapter: int | None = None, start_chapter: int | None = None, end_chapter: int | None = None):
        super().__init__(task_id)
        self.only_chapter = only_chapter  # 若指定，仅润色该章
        self.start_chapter = start_chapter
        self.end_chapter = end_chapter

    def run(self) -> None:
        try:
            self._set_running(0, "润色准备中...")
            task_d = _task_dir(self.task_id)
            out_d = task_d / "output" / "chapters"
            if not out_d.exists():
                self._set_failed("润色失败：未找到正文章节")
                return
            style_ref = ""
            sp = task_d / "output" / "style" / "风格参数表.md"
            if sp.exists():
                style_ref = sp.read_text(encoding="utf-8", errors="replace")[:2000]
            only = getattr(self, "only_chapter", None)
            if only is not None:
                fp_one = out_d / f"ch_{only:02d}.md"
                chapters = [fp_one] if fp_one.exists() else []
            else:
                chapters = sorted(out_d.glob("ch_*.md"))
                if self.start_chapter is not None or self.end_chapter is not None:
                    st = self.start_chapter if self.start_chapter is not None else 1
                    ed = self.end_chapter if self.end_chapter is not None else 10**9
                    picked = []
                    for fp in chapters:
                        try:
                            idx = int(fp.stem.split("_")[-1])
                        except Exception:
                            continue
                        if st <= idx <= ed:
                            picked.append(fp)
                    chapters = picked
            total = len(chapters)
            for i, fp in enumerate(chapters):
                pct = (i + 1) * 100 // total if total else 0
                self._set_running(pct, f"章节润色中（第{i+1}章/共{total}章）", current_chapter=i + 1, total_chapters=total)
                raw = fp.read_text(encoding="utf-8")
                prompt = [
                    {"role": "system", "content": "你是网文责编，负责润色：修正病句、优化句式、增强画面感、统一文风、删除冗余，不改变情节与人设。只输出润色后的正文，不要解释。\n硬性要求：禁止截断输出末尾；禁止以“……”/“但……”/未闭合引号/未完成句结束；必须以完整的句号/问号/感叹号收尾。"},
                    {"role": "user", "content": f"""请对以下章节进行润色。要求：语句通顺、前后句意思连贯、无病句、无重复灌水；不要删掉章末关键内容；若有风格参考请尽量贴合。\n\n【风格参考】\n{style_ref[:1500] if style_ref else "短句为主，节奏快，对话自然"}\n\n【待润色正文】\n{raw[:12000]}"""},
                ]
                # 输出上限放大，避免润色阶段因“输出截断”导致句子不完整（审计会把这类问题当作连贯性缺陷）
                polished = llm.chat(prompt, temperature=0.4, max_tokens=8192)
                write_output_file(self.task_id, f"chapters_polished/{fp.name}", polished)
                self._log("info", f"润色完成 {fp.name}")
                time.sleep(settings.step_interval_seconds or 0.2)
            self._set_completed("润色完成")
        except Exception as e:
            self._set_failed(f"润色失败：{type(e).__name__}: {e}")
