# -*- coding: utf-8 -*-
import json
import time
from pathlib import Path
from app.agents.base import BaseAgent
from app.core.state import write_output_file, _task_dir
from app.core.config import settings
from app.core import llm


class ReviserAgent(BaseAgent):
    name = "ReviserAgent"

    def __init__(self, task_id):
        super().__init__(task_id)

    def run(self) -> None:
        try:
            self._set_running(0, "修订准备中...")
            task_d = _task_dir(self.task_id)

            # 1) 读取 outline：用于生成“完整目录（200+章）”
            outline_p = task_d / "output" / "planner" / "outline.json"
            if not outline_p.exists():
                self._set_failed("修订失败：未找到 planner/outline.json（无法构建完整目录）")
                return
            outline_data = json.loads(outline_p.read_text(encoding="utf-8"))
            outline_chapters = outline_data.get("chapters") or []
            outline_total = len(outline_chapters)
            if outline_total <= 0:
                self._set_failed("修订失败：outline.json 的 chapters 为空")
                return

            # 2) 真实参与修订的只有已生成章节（通常是前 N 章）
            out_d = task_d / "output" / "chapters_polished"
            if not out_d.exists():
                out_d = task_d / "output" / "chapters"
            if not out_d.exists():
                self._set_failed("修订失败：未找到可修订章节")
                return

            def _idx_from_name(fp: Path) -> int:
                stem = fp.stem  # ch_01
                try:
                    return int(stem.split("_")[-1])
                except Exception:
                    return 0

            polished_files = sorted(out_d.glob("ch_*.md"), key=_idx_from_name)
            if not polished_files:
                self._set_failed("修订失败：未找到 ch_*.md 章节文件")
                return

            # 3) 审计意见摘要（供修订 prompt）
            audit_summary = ""
            audit_json = task_d / "output" / "audit" / "audit_result.json"
            if audit_json.exists():
                try:
                    data = json.loads(audit_json.read_text(encoding="utf-8"))
                    audit_summary = data.get("summary", "") or ""
                    for k in ["coherence_issues", "logic_issues", "ooc_issues", "plot_hole_issues"]:
                        for x in data.get(k, [])[:8]:
                            audit_summary += "\n- " + str(x)
                except Exception:
                    pass
            if not audit_summary:
                audit_md = task_d / "output" / "audit" / "质量审计报告.md"
                if audit_md.exists():
                    audit_summary = audit_md.read_text(encoding="utf-8", errors="replace")[:2000]

            # 4) 修订已生成章节，并缓存到 revised_map
            revised_map: dict[int, str] = {}
            total_revised = len(polished_files)
            for i, fp in enumerate(polished_files):
                chap_idx = _idx_from_name(fp)
                pct = (i + 1) * 100 // total_revised if total_revised else 0
                self._set_running(
                    pct,
                    f"章节修订中（第{chap_idx}章/共{outline_total}章）",
                    current_chapter=chap_idx,
                    total_chapters=outline_total,
                    iteration=1,
                )
                content = fp.read_text(encoding="utf-8")
                prev_tail = revised_map.get(_idx_from_name(polished_files[i - 1]), "")[-800:] if i > 0 else ""
                next_head = ""
                if i + 1 < len(polished_files):
                    next_head = polished_files[i + 1].read_text(encoding="utf-8")[:600]

                prompt = [
                    {
                        "role": "system",
                        "content": "你是网文修订编辑。根据审计意见修订正文，修正前后章不连贯、逻辑漏洞、人设不一致、伏笔遗漏，保持情节与风格不变。只输出修订后的本章正文，不要解释。",
                    },
                    {
                        "role": "user",
                        "content": f"""【审计意见摘要】\n{audit_summary[:1500]}\n\n【上一章结尾（供衔接）】\n{prev_tail}\n\n【当前章正文】\n{content[:4500]}\n\n【下一章开头（供衔接）】\n{next_head[:400]}\n\n请输出修订后的当前章完整正文（保持字数与情节，只改不连贯、逻辑与人设问题）：""",
                    },
                ]
                revised_content = llm.chat(prompt, temperature=0.3, max_tokens=3200)
                revised_map[chap_idx] = revised_content
                write_output_file(self.task_id, f"final/{fp.name}", revised_content)
                time.sleep(settings.step_interval_seconds or 0.2)

            # 5) 组装“完整目录 + 正文仅前 N 章有内容”
            self._set_running(90, "定稿输出中...")
            try:
                # 优先使用 Planner 已审核通过的小说名，避免绕过审核口径
                title_fp = task_d / "output" / "planner" / "小说名.txt"
                if title_fp.exists():
                    title = title_fp.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0][:20]
                else:
                    title = llm.chat(
                        [
                            {
                                "role": "system",
                                "content": "你是网文编辑，擅长给爽文起爆款书名。只输出书名本身，不要引号，不要解释。",
                            },
                            {"role": "user", "content": "请给这部快节节奏爽文起一个书名（6–12字），要求有爆款感、可读性强。"},
                        ],
                        temperature=0.9,
                        max_tokens=30,
                    ).strip().splitlines()[0][:20]
            except Exception:
                title = "自动生成小说"

            toc_lines = ["# " + title, "", "## 目录", ""]
            body_lines = ["", "## 正文", ""]

            for i in range(1, outline_total + 1):
                outline = outline_chapters[i - 1] if i - 1 < len(outline_chapters) else {}
                chap_label = outline.get("title") or f"第{i}章"
                anchor = f"chapter-{i:02d}"
                toc_lines.append(f"- [{chap_label}](#{anchor})")
                body_lines.append(f"\n### {chap_label}\n<a id=\"{anchor}\"></a>\n")
                if i in revised_map:
                    body_lines.append(revised_map[i])

            novel_md = "\n".join(toc_lines + body_lines) + "\n"
            write_output_file(self.task_id, "final/成书_含目录可跳转.md", novel_md)
            write_output_file(
                self.task_id,
                "final/修订报告.md",
                "# 修订报告\n\n已根据审计意见修订已生成的章节正文；其余章节仅保留目录占位。\n",
            )
            self._set_completed("定稿完成", output_dir="final", novel_path="final/成书_含目录可跳转.md")
        except Exception as e:
            self._set_failed(f"修订失败：{type(e).__name__}: {e}")
