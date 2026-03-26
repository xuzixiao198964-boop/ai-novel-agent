# -*- coding: utf-8 -*-
"""策划大纲 Agent：
按要求流程：
1) 生成策划案 → 审核（不通过则按意见重写，直到通过）
2) 依据策划案生成「故事总纲」：每 5 章一批；每累计 3 批对当前累计总纲审核一次，不通过则修订至通过
3) 依据故事总纲生成故事大纲（每章字段齐全）→ 每 5 章审核一次（结构自动修正 + LLM 质量门控），不通过则修订/回滚至通过
4) 审核全部通过后才可进入正文创作

说明：面向用户/前端的「故事大纲_审核意见.txt」与「outline_review_log.md」内容保持一致（全文同步，不做摘要改写）。
"""
import json
import random
import time
import re
from datetime import datetime
from pathlib import Path
from app.agents.base import BaseAgent
from app.core.state import write_output_file, append_output_file, _task_dir, get_used_character_names, update_task_meta, is_stop_requested
from app.core.config import settings
from app.core import llm

# 增加策划阶段的审核重试次数，避免6次失败就罢工
PLAN_REVIEW_MAX = 12          # 从6增加到12
OUTLINE_REVIEW_MAX = 16       # 从8增加到16  
OUTLINE_BATCH_RETRY_MAX = 10  # 从5增加到10
SPINE_REVIEW_MAX = 12         # 从6增加到12
SPINE_AUDIT_EVERY_BATCHES = 1  # 故事总纲每次输出后立即审核
SPINE_BATCH_RETRY_MAX = 8     # 从4增加到8


def _clamp_int(x, default: int) -> int:
    try:
        return int(float(x))
    except Exception:
        return default


def _review_plan(trend_md: str, style_md: str, plan_md: str) -> dict:
    """审核策划案：四项全部逐条检查（即使某项不通过也继续检查）。"""
    prompt = [
        {
            "role": "system",
            "content": (
                "你是资深网文策划审核员。你必须对策划案的审核项全部执行完毕："
                "即使某一项未通过，也要继续检查其余项，并在 JSON 中完整返回所有项结果。"
                "只输出严格 JSON 对象，不要输出任何额外文本。"
                "JSON 字段："
                "{"
                "\"pass\": true/false,"
                "\"overall_reason\": \"简述总评\","
                "\"items\": ["
                "{\"key\": \"核心设定/人设矩阵/完整故事线/章节规模建议\", \"pass\": true/false, \"reason\": \"\", \"fix\": [\"...\", ...]},"
                "...],"
                "\"fix\": [\"...\", ...]"
                "}"
            ),
        },
        {
            "role": "user",
            "content": f"""【热门趋势分析】\n{trend_md[:4000] if trend_md else "（无）"}\n\n【风格参数】\n{style_md[:3000] if style_md else "（无）"}\n\n【策划案】\n{plan_md[:9000]}\n\n请开始审核：\n"""
            + "1) 核心设定：世界观、主线目标、核心冲突是否清晰且可执行。\n"
            + "2) 人设矩阵：主角与关键配角身份/目标/关系/核心特质是否明确且彼此不矛盾。\n"
            + "3) 完整故事线：起因→发展→多阶段冲突→高潮→结局是否因果连贯、节奏可落地。\n"
            + "4) 章节规模建议：章节数是否在可写范围、节奏分段建议是否合理。\n"
            + "输出 JSON（含所有 items）。\n",
        },
    ]
    try:
        raw = llm.chat_json(prompt, temperature=0.0, max_tokens=900)
        items = raw.get("items") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            items = []
        fix = raw.get("fix") if isinstance(raw, dict) else None
        if not isinstance(fix, list):
            fix = []
        overall_pass = bool(raw.get("pass", False))
        return {
            "pass": overall_pass,
            "reason": str(raw.get("overall_reason") or ""),
            "items": items,
            "fix": fix,
        }
    except Exception:
        return {"pass": False, "reason": "策划案审核解析失败", "items": [], "fix": []}


def _rewrite_plan(trend_md: str, style_md: str, plan_md: str, review: dict, chapter_min: int, chapter_max: int) -> str:
    fix = review.get("fix") or []
    if not isinstance(fix, list):
        fix = []
    prompt = [
        {
            "role": "system",
            "content": (
                "你是资深网文策划。根据审核意见只修复【必须修复项】相关内容，"
                "其余段落尽量保持不变、保持原结构。"
                "只输出 Markdown 策划案，不要解释，不要代码块围栏。"
            ),
        },
        {
            "role": "user",
            "content": f"""请根据审核意见只修复【必须修复项】相关内容（不是大改整份），并确保整体仍包含以下四部分标题：

## 一、核心设定（世界观、主线目标、核心冲突）
## 二、人设矩阵（主角、重要配角各 3–5 人：身份、目标、与主角关系、核心特质）
## 三、完整故事线（用 10–20 句话概括整体故事逻辑：起因→发展→多阶段冲突→高潮→结局，前后因果清晰）
## 四、章节规模建议（建议总章节数在 {chapter_min}–{chapter_max} 章之间，并说明节奏：前 1/4 铺垫入戏，中 1/2 崛起与冲突升级，后 1/4 高潮与收束）

【热门趋势分析】\n{trend_md[:5000] if trend_md else "（无）"}

【风格参数】\n{style_md[:3500] if style_md else "（无）"}

【上一版策划案】\n{plan_md[:4000]}

【审核未通过原因】\n{review.get("reason","")}\n
【必须修复项】\n- {chr(10).join([str(x) for x in fix[:12]]) if fix else "（无）"}

只输出 Markdown 策划案，不要代码块围栏。""",
        },
    ]
    return llm.chat(prompt, temperature=0.35, max_tokens=3600)


NOVEL_NAME_REVIEW_MAX = 4


def _generate_novel_name(plan_md: str, trend_md: str) -> str:
    """根据策划案与趋势生成一个小说书名。"""
    prompt = [
        {"role": "system", "content": "你是网文策划。根据策划案与趋势，输出一个中文小说书名（不超过 20 字），要求有吸引力、易记。只输出书名，不要解释、不要引号。"},
        {"role": "user", "content": f"【策划案摘要】\n{plan_md[:3000]}\n\n【趋势参考】\n{trend_md[:1500] if trend_md else '无'}\n\n请输出一本小说书名（仅书名，不超过20字）："},
    ]
    return (llm.chat(prompt, temperature=0.7, max_tokens=80) or "").strip().strip('"\'""''')[:50]


def _review_novel_name(plan_md: str, novel_name: str) -> dict:
    """审核书名：是否有吸引力、是否契合主题。返回 {pass: bool, reason: str}。"""
    prompt = [
        {
            "role": "system",
            "content": "你是网文运营。仅判断书名是否有吸引力、是否契合策划案主题。只输出严格 JSON：{ \"pass\": true/false, \"reason\": \"简短理由\" }",
        },
        {
            "role": "user",
            "content": f"【策划案摘要】\n{plan_md[:2500]}\n\n【当前书名】{novel_name}\n\n请判断该书名是否有吸引力、是否契合主题。只输出 JSON。",
        },
    ]
    try:
        raw = llm.chat_json(prompt, temperature=0.2, max_tokens=200)
        return {"pass": bool(raw.get("pass", True)), "reason": str(raw.get("reason") or "")}
    except Exception:
        return {"pass": True, "reason": ""}


def _rewrite_novel_name(plan_md: str, trend_md: str, old_name: str, review_reason: str) -> str:
    """根据审核未通过原因重写书名（只输出书名，不要解释）。"""
    prompt = [
        {
            "role": "system",
            "content": "你是资深网文策划。根据审核未通过原因，修改书名以提升吸引力与主题契合。只输出书名本身，不要引号、不要解释，不要代码块。",
        },
        {
            "role": "user",
            "content": f"""【策划案摘要】\n{plan_md[:3000] if plan_md else ""}\n\n【趋势参考】\n{trend_md[:1500] if trend_md else '无'}\n\n【当前书名】\n{old_name}\n\n【审核未通过原因】\n{review_reason}\n\n请输出一个修改后的书名（中文、不超过20字）。""",
        },
    ]
    return (llm.chat(prompt, temperature=0.5, max_tokens=60) or "").strip().strip('"\'""''')[:50]


def _generate_and_review_novel_name(plan_md: str, trend_md: str, task_id: str) -> str:
    """生成书名并审核，不通过则重试，返回最终书名（可能为空）。"""
    last_name = ""
    for _ in range(NOVEL_NAME_REVIEW_MAX):
        name = _generate_novel_name(plan_md, trend_md)
        if not name or len(name) < 2:
            continue
        last_name = name
        rev = _review_novel_name(plan_md, name)
        if rev.get("pass"):
            return name
    # 严格要求：不通过时不再返回未经审核的随机书名
    # 仍无法通过审核则返回占位书名（不再进行未审核生成）
    return "未命名小说"

_TITLE_RE = re.compile(r"第\s*(\d+)\s*章")


def _parse_intish(x: object) -> int | None:
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        try:
            return int(x)
        except Exception:
            return None
    s = str(x).strip()
    m = re.search(r"-?\d+", s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None


def _normalize_outline_ab(chapters: list[dict], total_chapters: int) -> tuple[list[dict], list[str]]:
    """对大纲的 A/B（字段齐全 + 数值/格式约束）做确定性修复，避免 LLM 主观审核卡死。"""
    fixes: list[str] = []
    out: list[dict] = []
    for i, ch in enumerate(chapters, 1):
        if not isinstance(ch, dict):
            ch = {}
        new = dict(ch)

        # title: 必须包含且与本章序号一致
        expected = f"第{i}章"
        title = str(new.get("title") or "")
        m = _TITLE_RE.search(title)
        ok_title = bool(m and int(m.group(1)) == i)
        if not ok_title:
            new["title"] = expected
            fixes.append(f"第{i}章：title格式修正为 {expected}")

        # hook_payoff_chapter: 必须是 1..total_chapters 的数字
        hpc = _parse_intish(new.get("hook_payoff_chapter"))
        if hpc is None:
            hpc = min(total_chapters, i + 3)
            fixes.append(f"第{i}章：hook_payoff_chapter缺失/非法，设为 {hpc}")
        if hpc < 1 or hpc > total_chapters:
            hpc2 = max(1, min(total_chapters, hpc))
            new["hook_payoff_chapter"] = hpc2
            fixes.append(f"第{i}章：hook_payoff_chapter越界（{hpc}），设为 {hpc2}")
        else:
            new["hook_payoff_chapter"] = hpc

        # connection: 必须非空，且避免直接复用提示模板
        conn = str(new.get("connection") or "").strip()
        if (not conn) or ("承接点/因果" in conn) or ("因果；第" in conn):
            new["connection"] = "承接上章，因果自然推进"
            fixes.append(f"第{i}章：connection补全/修正")

        # 其余字段：只要缺失就补齐默认值（尽量用已有 event 生成 theme）
        event = str(new.get("event") or "").strip()
        theme = str(new.get("theme") or "").strip()
        hook = str(new.get("hook") or "").strip()
        if not theme:
            theme = (event[:20] + "..." if event else "主题：围绕主线冲突升级")
            new["theme"] = theme
            fixes.append(f"第{i}章：theme补全")
        if not event:
            new["event"] = "核心事件：围绕冲突推进并埋下伏笔"
            fixes.append(f"第{i}章：event补全")
        if not hook:
            new["hook"] = "悬念：引出下一章的关键转折"
            fixes.append(f"第{i}章：hook补全")

        # 最终兜底：确保 key 都存在且非空
        required_keys = ["title", "theme", "event", "connection", "hook", "hook_payoff_chapter"]
        for k in required_keys:
            if k not in new or (isinstance(new[k], str) and not new[k].strip()):
                # 兜底文本会影响质量，但能保证流程能走通
                if k == "connection":
                    new[k] = "承接上章，因果自然推进"
                elif k == "theme":
                    new[k] = "主题：围绕主线冲突升级"
                elif k == "event":
                    new[k] = "核心事件：围绕冲突推进并埋下伏笔"
                elif k == "hook":
                    new[k] = "悬念：引出下一章的关键转折"
                elif k == "title":
                    new[k] = expected
                else:
                    new[k] = min(total_chapters, i + 3)
                fixes.append(f"第{i}章：{k}兜底补全")

        out.append(new)
    return out, fixes


def _sync_outline_review_opinion_file(task_id: str) -> None:
    """唯一面向展示的「故事大纲审核意见.txt」：全文与 outline_review_log.md 一致。"""
    log_rel = "planner/outline_review_log.md"
    p = _task_dir(task_id) / "output" / log_rel
    body = p.read_text(encoding="utf-8", errors="replace") if p.exists() else "# 故事大纲审核日志\n\n"
    write_output_file(task_id, "planner/故事大纲审核意见.txt", body)


def _generate_story_spine_batch(
    plan_md: str,
    start_chapter: int,
    end_chapter: int,
    total_chapters: int,
    prev_tail: str = "",
    feedback: str = "",
) -> str:
    """生成故事总纲的一个批次（覆盖 start..end，通常 3 章），返回 Markdown。"""
    n_this = end_chapter - start_chapter + 1
    fb = f"【上轮审核意见（须逐条落实）】\n{feedback[:4500]}\n\n" if feedback else ""
    prev = f"【上一批末段（衔接用）】\n{prev_tail[:2000]}\n\n" if prev_tail else ""
    prompt = [
        {
            "role": "system",
            "content": (
                "你是网文总纲策划。根据策划案写出「故事总纲」的一个片段：覆盖指定章节区间，"
                "要求因果连贯、阶段目标清晰、与全书总章数一致。只输出 Markdown，不要代码块围栏。"
            ),
        },
        {
            "role": "user",
            "content": f"""请根据【策划案】为第{start_chapter}章–第{end_chapter}章（共 {n_this} 章）撰写故事总纲片段。
全书总章数为 {total_chapters}。本片段必须可被后续「逐章大纲」严格执行，不得空洞套话。

输出格式（必须含小节标题）：
### 第{start_chapter}章–第{end_chapter}章 总纲
- **阶段目标**：……
- **章间推进**：
  - 第{start_chapter}章：……
  - …（每一章一行要点）
  - 第{end_chapter}章：……
- **关键伏笔/钩子**：……
- **与下一段衔接点**：……

{fb}{prev}【策划案】\n{plan_md[:7000]}
""",
        },
    ]
    return (llm.chat(prompt, temperature=0.45, max_tokens=2800) or "").strip()


def _review_story_spine_llm(plan_md: str, spine_md: str, covered_up_to_ch: int) -> dict:
    """LLM 审核累计故事总纲（截至 covered_up_to_ch）。"""
    prompt = [
        {
            "role": "system",
            "content": (
                "你是网文策划总监。请审核「故事总纲」：是否严格贴合策划案、阶段目标是否可执行、章段推进是否连贯无矛盾、伏笔是否清晰。"
                "只输出一个严格 JSON 对象，不要输出任何额外文本或 Markdown。"
                'JSON 必须以 `{` 开头并以 `}` 结尾。字段：'
                '{"pass": true/false, "reason": "简述", "fix": ["可执行修改项1", "..."]}'
                " fix 最多 12 条；若 pass 为 true，fix 为空数组。"
            ),
        },
        {
            "role": "user",
            "content": f"""【策划案摘要】\n{plan_md[:5000]}\n\n【当前累计故事总纲（已覆盖至约第 {covered_up_to_ch} 章）】\n{spine_md[:14000]}\n\n请审核。若不通过，fix 必须具体可改（例如指出哪一章段目标冲突、哪处与策划案人设矛盾）。只输出 JSON。""",
        },
    ]
    try:
        raw = llm.chat_json(prompt, temperature=0.0, max_tokens=450)
        return {
            "pass": bool(raw.get("pass")),
            "reason": str(raw.get("reason") or ""),
            "fix": list(raw.get("fix") or []) if isinstance(raw.get("fix"), list) else [],
        }
    except Exception as e:
        return {"pass": False, "reason": f"故事总纲审核解析失败：{e}", "fix": []}


def _revise_story_spine_llm(plan_md: str, spine_md: str, review: dict) -> str:
    """根据审核意见修订累计故事总纲：已通过且未被 fix 点名的段落尽量原样保留，只改问题段及为衔接所必需的后续调整。"""
    fix = review.get("fix") or []
    if not isinstance(fix, list):
        fix = []
    fix_block = "\n".join([f"{i+1}. {x}" for i, x in enumerate(fix[:14])])
    prompt = [
        {
            "role": "system",
            "content": (
                "你是网文总纲策划。根据审核意见做最小必要修订："
                "已通过、且未被【必须处理的修改项】点名的章节/段落请尽量保持原文表述，不要重写成另一套剧情；"
                "仅修改 fix 指向的段落，以及因修正而产生的必要衔接句；"
                "若 fix 指出「明显逻辑矛盾/硬伤/前后不一致」，才允许回溯改动更早段落。"
                "保持 Markdown 结构。只输出修订后的完整故事总纲 Markdown，不要解释。"
            ),
        },
        {
            "role": "user",
            "content": f"""【审核说明】\n{review.get("reason", "")}\n\n【必须处理的修改项】\n{fix_block}\n\n【当前故事总纲全文】\n{spine_md[:16000]}\n\n【策划案】\n{plan_md[:6000]}\n\n请输出修订后的完整故事总纲（Markdown）。""",
        },
    ]
    return (llm.chat(prompt, temperature=0.4, max_tokens=4000) or "").strip() or spine_md


def _review_outline_quality_llm(
    plan_md: str,
    story_spine_md: str,
    chapters: list[dict],
    total_chapters: int,
    batch_start: int,
    batch_end: int,
) -> dict:
    """LLM：在结构已自动修正后，对策划案 + 故事总纲 + 本批上下文做质量门控。"""
    ctx_start = max(1, batch_start - 1)
    ctx_chs = chapters[ctx_start - 1 : batch_end]
    try:
        mini = json.dumps(ctx_chs, ensure_ascii=False, indent=2)
    except Exception:
        mini = str(ctx_chs)
    if len(mini) > 12000:
        mini = mini[:12000] + "\n…(截断)"
    prompt = [
        {
            "role": "system",
            "content": (
                "你是网文结构审核。输入大纲已做过字段与格式自动修正。"
                "请从以下维度判断是否达到「可开写正文」标准：与策划案一致、与故事总纲对齐（本批章节区间）、"
                "章间衔接合理、事件包含基本发生过程且不致空洞（细节可由后续正文再扩写补足）、钩子与 hook_payoff_chapter 可执行。"
                "只输出一个严格 JSON 对象，不要输出任何额外文本或 Markdown。"
                'JSON 必须以 `{` 开头并以 `}` 结尾。字段：'
                '{"pass": true/false, "reason": "简述", "fix": ["第N章：具体问题与改法", ...]}'
                " 若不通过，fix 必须具体、可执行，最多 6 条；通过时 fix 可为空。"
            ),
        },
        {
            "role": "user",
            "content": f"""总章数 {total_chapters}。本次重点审核第 {batch_start}–{batch_end} 章（附带第 {ctx_start} 章用于衔接上下文）。

【策划案摘要】\n{plan_md[:4500]}

【故事总纲（须对齐；可略长）】\n{(story_spine_md or "")[:10000]}

【大纲 JSON（上下文含上一章+本批）】\n{mini}

只输出 JSON。""",
        },
    ]
    try:
        # 为降低 JSON 被截断概率，适当提高 max_tokens
        raw = llm.chat_json(prompt, temperature=0.0, max_tokens=1200)
        return {
            "pass": bool(raw.get("pass")),
            "reason": str(raw.get("reason") or ""),
            "fix": list(raw.get("fix") or []) if isinstance(raw.get("fix"), list) else [],
        }
    except Exception as e:
        return {"pass": False, "reason": f"大纲质量审核解析失败：{e}", "fix": []}


def _first_chapter_from_fixes(fixes: list[str]) -> int:
    for f in fixes or []:
        m = re.search(r"第\s*(\d+)\s*章", str(f))
        if m:
            return int(m.group(1))
    return 1


def _review_outline(
    plan_md: str,
    outline_data: dict,
    total_chapters: int,
    story_spine_md: str,
    batch_start: int,
    batch_end: int,
    only_check_fix: list[str] | None = None,
) -> dict:
    """审核故事大纲：先 A/B 确定性规范化，再经 LLM 质量审核；不通过由上游修订/重生成。"""
    del only_check_fix  # 保留签名兼容；质量门控统一走 LLM
    chapters = outline_data.get("chapters") or []
    if not isinstance(chapters, list):
        return {"pass": False, "reason": "chapters 非数组", "fix": [], "fix_from_chapter": 1, "normalized_chapters": []}

    if total_chapters <= 0:
        return {"pass": False, "reason": "total_chapters 无效", "fix": [], "fix_from_chapter": 1, "normalized_chapters": chapters}

    normalized, ab_fixes = _normalize_outline_ab(chapters, total_chapters)
    llm_r = _review_outline_quality_llm(plan_md, story_spine_md, normalized, total_chapters, batch_start, batch_end)

    ab_note = f"已自动修正{len(ab_fixes)}项结构/格式" if ab_fixes else ""
    reason = (llm_r.get("reason") or "").strip()
    if ab_note:
        reason = f"{reason}（{ab_note}）" if reason else ab_note

    fix_from = _first_chapter_from_fixes(llm_r.get("fix") or [])
    if fix_from < 1 or fix_from > total_chapters:
        fix_from = batch_start

    return {
        "pass": bool(llm_r.get("pass")),
        "reason": reason or ("通过" if llm_r.get("pass") else "未通过"),
        "fix": (llm_r.get("fix") or [])[:12],
        "fix_from_chapter": fix_from,
        "normalized_chapters": normalized,
        "ab_fixes": ab_fixes,
    }


def _generate_outline_batch(
    plan_md: str,
    story_spine_md: str,
    start_chapter: int,
    end_chapter: int,
    total_chapters: int,
    feedback: str = "",
    prev_tail: str = "",
) -> list[dict]:
    """分批生成章节大纲，避免一次性 JSON 过长被截断。返回 chapters 列表。"""
    n_this = end_chapter - start_chapter + 1
    feedback_block = f"【审核反馈（需重点修复）】\n{feedback}\n\n" if feedback else ""
    prev_block = f"【上一批末章结尾要点（用于衔接）】\n{prev_tail}\n\n" if prev_tail else ""
    spine_block = (
        f"【故事总纲（必须严格对齐；本批对应第{start_chapter}–{end_chapter}章）】\n{(story_spine_md or '')[:12000]}\n\n"
        if (story_spine_md or "").strip()
        else ""
    )
    prompt = [
        {
            "role": "system",
            "content": (
                "你是网文大纲师。请按范围生成章节大纲；必须严格服从「故事总纲」中本批章节区间的阶段目标与事件走向，"
                "并与策划案一致。只输出严格 JSON，不要代码块围栏，不要解释。"
            ),
        },
        {
            "role": "user",
            "content": f"""根据以下策划案与故事总纲，生成【第{start_chapter}章–第{end_chapter}章】的章节大纲（共 {n_this} 章），要求：
- 总章数固定为 {total_chapters}，但你本次只输出本范围的章节数组
- 每章必须包含字段：
  - title: 章节题目（必须含“第N章”）
  - theme: 本章主题/爽点（1 句话）
  - event: 本章核心事件（2–4 句话：至少 1 个具体动作/台词片段 + 1 个角色情绪/反应 + 明确冲突推进）
  - connection: 与上一章的衔接关系（承接点/因果；第{start_chapter}章需承接第{start_chapter-1}章；必须写“上一章末尾 -> 本章发生”的直接因果，禁止空泛）
  - hook: 本章末尾埋下的钩子/悬念（1 句话：必须点出“将在第 hook_payoff_chapter 章如何兑现”的线索）
  - hook_payoff_chapter: 计划在第几章展开/兑现该钩子（数字，1–{total_chapters}）
- 输出必须**严格**为 {n_this} 条；不要遗漏字段；不要输出多余文本

并且请强保证：
1) hook_payoff_chapter 必须与故事总纲中该阶段“最早会被回应/兑现”的章节一致；若冲突则修正到正确章节。
2) event 相关描述必须具体到可写正文（不要概括成“推进冲突/加强矛盾”等模板句）。
3) hook_payoff_chapter 必须是纯数字（阿拉伯数字），不能包含中文或说明文字。

{feedback_block}{prev_block}{spine_block}【策划案】\n{plan_md[:6500]}

只输出 JSON：
{{\"chapters\":[{{\"title\":\"第{start_chapter}章...\",\"theme\":\"...\",\"event\":\"...\",\"connection\":\"...\",\"hook\":\"...\",\"hook_payoff_chapter\":{min(total_chapters, start_chapter+3)}}}, ...]}}
""",
        },
    ]
    # 每批规模控制较小，避免截断；解析失败时 parse_json 会尝试 chapters 逐条兜底
    last_err = None
    for attempt in range(OUTLINE_BATCH_RETRY_MAX):
        try:
            data = llm.chat_json(prompt, temperature=0.35, max_tokens=3200, retries=3)
            chs = data.get("chapters") if isinstance(data, dict) else None
            if not isinstance(chs, list):
                raise RuntimeError("chapters 非数组")
            if len(chs) != n_this:
                raise RuntimeError(f"chapters 数量不符合预期：need={n_this} got={len(chs)}")
            return chs
        except Exception as e:
            last_err = e
            # 若 chat_json 已抛，可尝试用 chat 拿原文再 parse_json（会走 chapters 兜底）
            if attempt >= 1:
                try:
                    raw = llm.chat(prompt, temperature=0.35, max_tokens=3200, retries=2)
                    data = llm.parse_json(raw)
                    chs = data.get("chapters") if isinstance(data, dict) else None
                    if isinstance(chs, list) and len(chs) == n_this:
                        return chs
                except Exception:
                    pass
            time.sleep(settings.step_interval_seconds or 0.2)
            continue
    raise RuntimeError(f"故事大纲分批生成失败：{type(last_err).__name__}: {last_err}")


def _revise_outline_batch(
    plan_md: str,
    story_spine_md: str,
    batch: list[dict],
    feedback: str,
    fix_list: list[str],
    start_chapter: int,
    end_chapter: int,
    total_chapters: int,
) -> list[dict] | None:
    """仅根据列出的 fix 逐条修改，不引入新审核维度；返回修订后的本批 chapters，失败返回 None。"""
    n_this = end_chapter - start_chapter + 1
    fix_block = "\n".join([f"{i+1}. {x}" for i, x in enumerate(fix_list[:20])])
    spine_excerpt = (story_spine_md or "")[:6000]
    spine_block = f"【故事总纲（修订时不得偏离）】\n{spine_excerpt}\n\n" if spine_excerpt.strip() else ""
    prompt = [
        {
            "role": "system",
            "content": (
                "你是网文大纲师。请只根据【修改项列表】逐条修改，不要改动与列表无关的部分，不要引入新内容或新审核维度。"
                "修订须与故事总纲、策划案一致。只输出严格 JSON：{\"chapters\": [ {...}, ... ]}，共 " + str(n_this) + " 条，不要代码块围栏。"
            ),
        },
        {
            "role": "user",
            "content": f"""以下第{start_chapter}–{end_chapter}章大纲需修订。请仅对下列【修改项】逐条修改，保留其余内容不变；不要引入新的审核维度。

【修改项列表（仅修改以下项）】\n{fix_block}\n\n【审核说明】\n{feedback[:2000]}\n\n{spine_block}【当前本批大纲】\n{json.dumps(batch, ensure_ascii=False, indent=2)}\n\n【策划案摘要】\n{plan_md[:2000]}\n\n请只针对上述修改项列表逐条修正，输出修订后的 {n_this} 章大纲。只输出 JSON 的 {{\"chapters\": [...]}}。\n\n【硬性落地要求】\n1) 若修改项涉及“事件单薄/缺乏细节/过程不到位”，请把 event 替换为更具体的动作+反应（不要只做总结句）。\n2) 若修改项涉及钩子“时序/关联/可执行性/hook_payoff_chapter”，请同时修改 hook 文案的兑现线索，并把 hook_payoff_chapter 改为对应章节的纯数字。\n3) 若修改项提到章间衔接“跳跃/不自然”，请把 connection 改为明确的上一章末尾 -> 本章开场因果连接句。""",
        },
    ]
    try:
        data = llm.chat_json(prompt, temperature=0.3, max_tokens=3200, retries=2)
        chs = data.get("chapters") if isinstance(data, dict) else None
        if isinstance(chs, list) and len(chs) == n_this:
            return chs
        raw = llm.chat(prompt, temperature=0.3, max_tokens=3200, retries=1)
        data = llm.parse_json(raw)
        chs = data.get("chapters") if isinstance(data, dict) else None
        if isinstance(chs, list) and len(chs) == n_this:
            return chs
    except Exception:
        pass
    return None


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"

    def run(self) -> None:
        try:
            self._set_running(0, "读取趋势与风格...")
            task_d = _task_dir(self.task_id)
            out = task_d / "output"
            # 清理历史“过程意见文件”（仅保留最新，避免同一任务多次重试时堆积磁盘）
            try:
                planner_d = out / "planner"
                if planner_d.exists():
                    for fp in planner_d.glob("策划案_审核意见_r*.txt"):
                        fp.unlink(missing_ok=True)
                    for fp in planner_d.glob("故事大纲_审核意见_r*.txt"):
                        fp.unlink(missing_ok=True)
                    # 防止同一任务被中途重启时复用到旧的 outline/日志内容
                    for rel_fp in (
                        "outline_review_log.md",
                        "outline.json",
                        "故事大纲.md",
                        "故事大纲审核意见.txt",
                    ):
                        fp = planner_d / rel_fp
                        if fp.exists():
                            fp.unlink(missing_ok=True)
            except Exception:
                pass
            trend_md = (out / "trend" / "热门风格分析报告.md").read_text(encoding="utf-8", errors="replace") if (out / "trend" / "热门风格分析报告.md").exists() else ""
            style_md = (out / "style" / "风格参数表.md").read_text(encoding="utf-8", errors="replace") if (out / "style" / "风格参数表.md").exists() else ""
            if not trend_md and (out / "trend" / "trend_analysis.json").exists():
                trend_md = json.dumps(json.loads((out / "trend" / "trend_analysis.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
            self._log("info", "已加载趋势与风格", {"trend_len": len(trend_md), "style_len": len(style_md)})
            time.sleep(settings.step_interval_seconds or 0.2)

            chapter_min = getattr(settings, "chapter_range_min", 100) or 100
            chapter_max = getattr(settings, "chapter_range_max", 500) or 500

            # 优先使用趋势分析中的“本次随机建议选题”（picked_theme），避免每次都选第一个主题
            picked_genre = ""
            trend_suggested_total = 0
            trend_json_path = task_d / "output" / "trend" / "trend_analysis.json"
            if trend_json_path.exists():
                try:
                    trend_data = json.loads(trend_json_path.read_text(encoding="utf-8"))
                    picked_genre = (trend_data.get("picked_theme") or "").strip()
                    if not picked_genre:
                        genres = trend_data.get("top_genres") or []
                        if isinstance(genres, list) and genres:
                            one = random.choice(genres)
                            picked_genre = one.get("genre") or one.get("name") or ""
                    try:
                        trend_suggested_total = int(trend_data.get("suggested_total_chapters") or 0)
                    except Exception:
                        trend_suggested_total = 0
                except Exception:
                    pass
            genre_constraint = f"\n\n【本次创作题材】请严格在以下题材类型下创作：{picked_genre}。" if picked_genre else ""

            used_names = get_used_character_names(self.task_id)
            name_constraint = ""
            if used_names:
                name_constraint = f"\n\n【人名约束】以下名字已在其他作品中使用，请勿使用：{'、'.join(used_names[:50])}。请为人设矩阵中的主角与配角起全新的、不重复的名字。"

            # 1) 生成策划案，并循环审核直到通过
            self._set_running(10, "生成策划案...")
            prompt_plan = [
                {"role": "system", "content": "你是资深网文策划，根据市场趋势与风格参数设计可执行的故事策划案与完整故事线。输出 Markdown，不要解释。"},
                {"role": "user", "content": f"""请根据以下【热门趋势分析】与【风格参数】生成一部小说的完整策划案（Markdown），必须包含：

## 一、核心设定（世界观、主线目标、核心冲突）
## 二、人设矩阵（主角、重要配角各 3–5 人：身份、目标、与主角关系、核心特质）
## 三、完整故事线（用 10–20 句话概括整体故事逻辑：起因→发展→多阶段冲突→高潮→结局，前后因果清晰）
## 四、章节规模建议（建议总章节数在 {chapter_min}–{chapter_max} 章之间，并说明节奏：前 1/4 铺垫入戏，中 1/2 崛起与冲突升级，后 1/4 高潮与收束）

【热门趋势分析】\n{trend_md[:6000] if trend_md else "（无）"}

【风格参数】\n{style_md[:4000] if style_md else "（无）"}{genre_constraint}{name_constraint}

只输出 Markdown 策划案，不要代码块围栏。"""},
            ]
            plan_md = llm.chat(prompt_plan, temperature=0.6, max_tokens=3600)
            write_output_file(self.task_id, "planner/策划案.md", plan_md)
            time.sleep(settings.step_interval_seconds or 0.2)

            self._set_running(25, "审核策划案（不通过则按原因修复）...")
            plan_ok = False
            write_output_file(self.task_id, "planner/策划案审核意见.txt", "# 策划案审核意见\n\n")
            for i in range(PLAN_REVIEW_MAX):
                rev = _review_plan(trend_md, style_md, plan_md)
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conclusion = "通过" if rev.get("pass") else "不通过"
                block = (
                    f"## 第 {i+1} 次审核\n"
                    f"- **时间**：{now_s}\n"
                    f"- **结论**：{conclusion}\n"
                    f"- **总评原因**：{rev.get('reason') or '无'}\n"
                )
                items = rev.get("items") or []
                if isinstance(items, list) and items:
                    block += "- **逐项审核**：\n"
                    for it in items[:10]:
                        try:
                            k = it.get("key") or "项"
                            p = "通过" if it.get("pass") else "不通过"
                            r = it.get("reason") or "无"
                            block += f"  - {k}：{p}；{r}\n"
                        except Exception:
                            pass
                else:
                    block += "- **逐项审核**：未提供\n"
                if not rev.get("pass"):
                    fix_list = rev.get("fix") or []
                    if isinstance(fix_list, list) and fix_list:
                        block += "- **必须修复项**：\n"
                        for x in fix_list[:12]:
                            block += f"  - {x}\n"
                block += "\n"
                append_output_file(self.task_id, "planner/策划案审核意见.txt", block)

                # 智能判断：随着重试次数增加，逐步放宽标准
                if rev.get("pass"):
                    plan_ok = True
                    break
                else:
                    # 检查是否应该强制通过（在后期尝试中）
                    if i >= PLAN_REVIEW_MAX - 3:  # 最后3次尝试
                        # 检查问题是否严重
                        items = rev.get("items") or []
                        critical_failures = 0
                        for item in items:
                            if not item.get("pass"):
                                key = item.get("key", "")
                                # 检查是否是关键问题
                                if "核心设定" in key or "人设矩阵" in key:
                                    critical_failures += 1
                        
                        # 如果没有关键问题，强制通过
                        if critical_failures == 0:
                            append_output_file(self.task_id, "planner/策划案审核意见.txt", 
                                            f"\n## 强制通过说明\n- 第{i+1}次审核未通过，但无关键问题，强制通过以继续流程\n")
                            plan_ok = True
                            break
                
                plan_md = _rewrite_plan(trend_md, style_md, plan_md, rev, chapter_min, chapter_max)
                write_output_file(self.task_id, "planner/策划案.md", plan_md)
                time.sleep(settings.step_interval_seconds or 0.2)
            
            if not plan_ok:
                # 最终检查：即使所有尝试都失败，如果没有关键问题也强制通过
                items = rev.get("items") or [] if 'rev' in locals() else []
                critical_failures = 0
                for item in items:
                    if not item.get("pass"):
                        key = item.get("key", "")
                        if "核心设定" in key or "人设矩阵" in key:
                            critical_failures += 1
                
                if critical_failures == 0:
                    append_output_file(self.task_id, "planner/策划案审核意见.txt", 
                                    f"\n## 最终强制通过\n- 已达到最大重试次数{PLAN_REVIEW_MAX}，但无关键问题，强制通过\n")
                    plan_ok = True
                else:
                    msg = f"策划案审核未通过（已重写 {PLAN_REVIEW_MAX} 次仍失败，有关键问题）"
                    self._set_failed(msg)
                    raise RuntimeError(msg)

            # 1.5) 生成并审核小说书名：不通过则按原因修复（不随机放行）
            self._set_running(28, "生成并审核小说名（按原因修复）...")
            write_output_file(self.task_id, "planner/小说名审核意见.txt", "# 小说名审核意见\n\n")
            novel_name = ""
            novel_ok = False
            for i in range(NOVEL_NAME_REVIEW_MAX):
                if i == 0 or not novel_name:
                    novel_name = _generate_novel_name(plan_md, trend_md)
                # 书名审核/修复必须给出意见时间、结论与原因
                rev = _review_novel_name(plan_md, novel_name)
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conclusion = "通过" if rev.get("pass") else "不通过"
                block = (
                    f"## 第 {i+1} 次审核\n"
                    f"- **时间**：{now_s}\n"
                    f"- **当前书名**：{novel_name}\n"
                    f"- **结论**：{conclusion}\n"
                    f"- **审核原因**：{rev.get('reason') or '无'}\n\n"
                )
                append_output_file(self.task_id, "planner/小说名审核意见.txt", block)
                if rev.get("pass"):
                    novel_ok = True
                    break
                # 不通过：根据原因修复书名
                novel_name = _rewrite_novel_name(plan_md, trend_md, novel_name, rev.get("reason") or "")
                time.sleep(settings.step_interval_seconds or 0.2)
            if not novel_ok:
                novel_name = "未命名小说"
            update_task_meta(self.task_id, name=novel_name)
            write_output_file(self.task_id, "planner/小说名.txt", novel_name)

            # 2) 确定章节规模（100–500）
            self._set_running(32, "确定章节规模...")
            total_override = getattr(settings, "total_chapters", 0) or 0
            if total_override > 0:
                suggested_chapters = int(total_override)
            else:
                base = trend_suggested_total if trend_suggested_total > 0 else (chapter_min + chapter_max) // 2
                suggested_chapters = max(chapter_min, min(chapter_max, int(base)))
            write_output_file(self.task_id, "planner/章节规模.json", json.dumps({"suggested_chapters": suggested_chapters}, ensure_ascii=False, indent=2))

            batch_size = 3  # 故事总纲 / 故事大纲 均按 3 章为一批；每批输出后立即审核
            num_spine_batches = (suggested_chapters + batch_size - 1) // batch_size

            # 2.5) 故事总纲：依据策划案，每 5 章一批；每累计 3 批对累计全文审核，不通过则修订至通过
            self._set_running(34, "生成故事总纲（3章一提要，每批审核）...")
            spine_log_path = "planner/故事总纲审核意见.txt"
            write_output_file(self.task_id, spine_log_path, "# 故事总纲审核意见\n\n")
            spine_md = "# 故事总纲\n\n> 依据通过的策划案，对全书做分章阶段总纲；后续「故事大纲」须严格对照本文。\n\n"
            write_output_file(self.task_id, "planner/故事总纲.md", spine_md)
            prev_spine_tail = ""
            spine_feedback = ""
            spine_review_seq = 0
            for sb in range(num_spine_batches):
                if is_stop_requested():
                    self._set_failed("已按用户请求停止")
                    return
                s_start = sb * batch_size + 1
                s_end = min((sb + 1) * batch_size, suggested_chapters)
                self._set_running(34 + sb, f"故事总纲 第 {sb + 1}/{num_spine_batches} 批（第{s_start}–{s_end}章）...")
                chunk = ""
                last_err: Exception | None = None
                for _attempt in range(SPINE_BATCH_RETRY_MAX):
                    try:
                        chunk = _generate_story_spine_batch(
                            plan_md, s_start, s_end, suggested_chapters, prev_spine_tail, spine_feedback
                        )
                        if not chunk or len(chunk.strip()) < 40:
                            raise RuntimeError("故事总纲批次内容过短")
                        break
                    except Exception as e:
                        last_err = e
                        time.sleep(settings.step_interval_seconds or 0.2)
                if not chunk:
                    raise RuntimeError(f"故事总纲生成失败：{type(last_err).__name__ if last_err else 'unknown'}: {last_err}")
                spine_md = spine_md.rstrip() + "\n\n" + chunk.strip() + "\n"
                write_output_file(self.task_id, "planner/故事总纲.md", spine_md)
                prev_spine_tail = chunk.strip()[-1200:] if len(chunk.strip()) > 1200 else chunk.strip()
                spine_feedback = ""

                batches_done = sb + 1
                need_audit = (batches_done % SPINE_AUDIT_EVERY_BATCHES == 0) or (batches_done == num_spine_batches)
                if need_audit:
                    audit_ok = False
                    for _ar in range(SPINE_REVIEW_MAX):
                        if is_stop_requested():
                            self._set_failed("已按用户请求停止")
                            return
                        spine_review_seq += 1
                        srev = _review_story_spine_llm(plan_md, spine_md, s_end)
                        s_conclusion = "通过" if srev.get("pass") else "不通过"
                        s_reason = srev.get("reason", "") or "无"
                        if not srev.get("pass") and (srev.get("fix") or []):
                            s_reason += "\n" + "\n".join([str(x) for x in (srev.get("fix") or [])[:12]])
                        s_block = (
                            f"## 第 {spine_review_seq} 次总纲审核\n"
                            f"- **时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"- **已覆盖至**：第 {s_end} 章\n"
                            f"- **结论**：{s_conclusion}\n"
                            f"- **说明**：{s_reason}\n\n"
                        )
                        append_output_file(self.task_id, spine_log_path, s_block)
                        if srev.get("pass"):
                            audit_ok = True
                            break
                        spine_md = _revise_story_spine_llm(plan_md, spine_md, srev)
                        write_output_file(self.task_id, "planner/故事总纲.md", spine_md)
                        time.sleep(settings.step_interval_seconds or 0.2)
                    if not audit_ok:
                        msg = "故事总纲审核未通过（已达最大修订次数）"
                        self._set_failed(msg)
                        raise RuntimeError(msg)

            story_spine_for_outline = spine_md

            # 3) 故事大纲：依据故事总纲 + 策划案，每 3 章一批；每批 LLM 质量审核通过后再继续
            self._set_running(36, "生成故事大纲（逐批生成+同步审核）...")
            chapters: list[dict] = []
            num_batches = (suggested_chapters + batch_size - 1) // batch_size
            feedback = ""
            prev_tail = ""
            b = 0
            review_round = 0
            outline_recent_failures: list[dict] = []  # 近期审核不通过原因（最多保留 5 次），两次及以上不通过时作为下次创作的避免项
            while b < num_batches:
                if is_stop_requested():
                    self._set_failed("已按用户请求停止")
                    return
                start_ch = b * batch_size + 1
                end_ch = min((b + 1) * batch_size, suggested_chapters)
                n_need = end_ch - start_ch + 1
                self._set_running(40 + (b * 35 // max(1, num_batches)), f"生成故事大纲第 {b+1}/{num_batches} 批（第{start_ch}–{end_ch}章）...")
                batch = _generate_outline_batch(
                    plan_md=plan_md,
                    story_spine_md=story_spine_for_outline,
                    start_chapter=start_ch,
                    end_chapter=end_ch,
                    total_chapters=suggested_chapters,
                    feedback=feedback,
                    prev_tail=prev_tail,
                )
                if batch and len(batch) > n_need:
                    batch = batch[:n_need]
                if not batch or len(batch) != n_need:
                    raise RuntimeError(f"故事大纲分批生成失败：第{start_ch}–{end_ch}章返回数量异常（{len(batch) if batch else 0}）")
                chapters = chapters[: start_ch - 1] + batch
                try:
                    last = batch[-1] if batch else {}
                    prev_tail = f"{last.get('title','')}: {last.get('event','')} | hook={last.get('hook','')}"
                except Exception:
                    prev_tail = ""
                time.sleep(settings.step_interval_seconds or 0.2)

                self._set_running(50 + (b * 25 // max(1, num_batches)), "审核本批大纲（每3章：结构修正+质量审核）...")
                orev = _review_outline(
                    plan_md,
                    {"chapters": chapters},
                    suggested_chapters,
                    story_spine_for_outline,
                    start_ch,
                    end_ch,
                )
                chapters = orev.get("normalized_chapters") or chapters
                review_round += 1
                if review_round > OUTLINE_REVIEW_MAX * num_batches:
                    raise RuntimeError("故事大纲审核轮次过多，已中止")
                # 审核结论写入 outline_review_log.md，并同步到「故事大纲_审核意见.txt」（全文一致）
                log_path = "planner/outline_review_log.md"
                log_fp = _task_dir(self.task_id) / "output" / log_path
                if not log_fp.exists():
                    write_output_file(self.task_id, log_path, "# 故事大纲审核日志\n\n")
                    _sync_outline_review_opinion_file(self.task_id)
                conclusion = "通过" if orev.get("pass") else "不通过"
                rewrite_reason = orev.get("reason", "") if orev.get("reason") else "无"
                if not orev.get("pass") and (orev.get("fix") or []):
                    rewrite_reason += "\n" + "\n".join([str(x) for x in (orev.get("fix") or [])[:12]])
                block = (
                    f"## 第 {review_round} 次审核\n"
                    f"- **时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"- **审核章节**：第 {start_ch}–{end_ch} 章\n"
                    f"- **结论**：{conclusion}\n"
                    f"- **重写原因**：{rewrite_reason}\n\n"
                )
                append_output_file(self.task_id, log_path, block)
                _sync_outline_review_opinion_file(self.task_id)
                if orev.get("pass"):
                    write_output_file(self.task_id, "planner/outline.json", json.dumps({"chapters": chapters}, ensure_ascii=False, indent=2))
                    b += 1
                    feedback = ""
                    continue
                # 不通过：先尝试只修改不通过部分，除非审核意见指出章节内部矛盾
                reason = (orev.get("reason") or "") + " " + " ".join([str(x) for x in (orev.get("fix") or [])[:12]])
                # “事件单薄/细节不足/钩子时序不稳/衔接跳跃”等通常需要重构段落，而不是只做局部小修
                # 优先局部修订；仅当存在明显逻辑硬伤时才整批重生成
                need_full_regenerate = any(
                    k in reason
                    for k in (
                        "内部矛盾",
                        "逻辑矛盾",
                        "前后矛盾",
                        "因果矛盾",
                        "设定矛盾",
                        "硬伤",
                        "自相矛盾",
                    )
                )
                revised_batch = None
                if not need_full_regenerate:
                    try:
                        fix_list = list((orev.get("fix") or [])[:12])
                        if not fix_list:
                            fix_list = [reason[:500]]
                        batch_current = chapters[start_ch - 1 : end_ch]
                        revised_batch = _revise_outline_batch(
                            plan_md,
                            story_spine_for_outline,
                            batch_current,
                            reason[:3000],
                            fix_list,
                            start_ch,
                            end_ch,
                            suggested_chapters,
                        )
                        if revised_batch and len(revised_batch) == len(batch_current):
                            chapters = chapters[: start_ch - 1] + revised_batch + chapters[end_ch:]
                            orev2 = _review_outline(
                                plan_md,
                                {"chapters": chapters},
                                suggested_chapters,
                                story_spine_for_outline,
                                start_ch,
                                end_ch,
                            )
                            chapters = orev2.get("normalized_chapters") or chapters
                            if orev2.get("pass"):
                                block2 = (
                                    f"## 修订后复审\n"
                                    f"- **时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                    f"- **审核章节**：第 {start_ch}–{end_ch} 章（仅修订不通过部分后复审）\n"
                                    f"- **结论**：通过\n\n"
                                )
                                append_output_file(self.task_id, log_path, block2)
                                _sync_outline_review_opinion_file(self.task_id)
                                write_output_file(self.task_id, "planner/outline.json", json.dumps({"chapters": chapters}, ensure_ascii=False, indent=2))
                                b += 1
                                feedback = ""
                                continue
                    except Exception:
                        pass
                # 修订未通过或需要整体重写：记录失败并回退/重新生成
                outline_recent_failures.append({
                    "reason": orev.get("reason") or "",
                    "fix": list((orev.get("fix") or [])[:12]),
                    "chapters": f"第{start_ch}–{end_ch}章",
                })
                outline_recent_failures = outline_recent_failures[-5:]
                if len(outline_recent_failures) >= 2:
                    parts = ["以下为近期审核不通过原因（请在本次创作中避免）："]
                    for i, r in enumerate(outline_recent_failures, 1):
                        parts.append(f"\n{i}. 审核{r['chapters']}不通过原因：{r['reason']}")
                        for x in (r.get("fix") or [])[:8]:
                            parts.append(f"   - {x}")
                    feedback = "\n".join(parts)
                else:
                    feedback = (orev.get("reason") or "") + "\n" + "\n".join([str(x) for x in (orev.get("fix") or [])][:12])
                # 展示用审核意见仅与 outline_review_log 同步，不在此写入另一套文案
                fix_from = _clamp_int(orev.get("fix_from_chapter"), 0)
                if fix_from >= 1 and fix_from <= len(chapters):
                    first_batch_to_regenerate = (fix_from - 1) // batch_size
                    chapters = chapters[: fix_from - 1]
                    b = first_batch_to_regenerate
                    prev_tail = ""
                    if b > 0 and len(chapters) > 0:
                        try:
                            last = chapters[-1]
                            prev_tail = f"{last.get('title','')}: {last.get('event','')} | hook={last.get('hook','')}"
                        except Exception:
                            pass
                else:
                    # 本批不通过：丢弃本批，重新生成本批
                    chapters = chapters[: start_ch - 1]
                    prev_tail = ""
                    if len(chapters) > 0:
                        try:
                            last = chapters[-1]
                            prev_tail = f"{last.get('title','')}: {last.get('event','')} | hook={last.get('hook','')}"
                        except Exception:
                            pass
                time.sleep(settings.step_interval_seconds or 0.2)

            if len(chapters) != suggested_chapters:
                raise RuntimeError(f"故事大纲生成章节数不一致：期望 {suggested_chapters}，实际 {len(chapters)}")
            write_output_file(self.task_id, "planner/outline.json", json.dumps({"chapters": chapters}, ensure_ascii=False, indent=2))
            md = "# 故事大纲（章节大纲）\n\n"
            for idx, ch in enumerate(chapters[:30], 1):
                md += (
                    f"## {ch.get('title', f'第{idx}章')}\n"
                    f"- 主题：{ch.get('theme','')}\n"
                    f"- 核心事件：{ch.get('event','')}\n"
                    f"- 与上章衔接：{ch.get('connection','')}\n"
                    f"- 钩子：{ch.get('hook','')}\n"
                    f"- 钩子展开章：{ch.get('hook_payoff_chapter','')}\n\n"
                )
            if len(chapters) > 30:
                md += f"... 共 {len(chapters)} 章\n"
            write_output_file(self.task_id, "planner/故事大纲.md", md)

            # 最终再同步一次：展示用「故事大纲_审核意见.txt」= outline_review_log.md 全文
            _sync_outline_review_opinion_file(self.task_id)

            genre_type = "女频" if picked_genre and any(x in picked_genre for x in ("言情", "甜宠", "耽美", "霸总", "晋江")) else "男频"
            update_task_meta(self.task_id, genre_type=genre_type)
            self._set_completed("策划案、故事总纲与故事大纲审核通过，可开始正文创作", outline_path="planner/outline.json")
        except Exception as e:
            self._set_failed(f"策划失败：{type(e).__name__}: {e}")
