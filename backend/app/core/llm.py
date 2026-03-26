# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import time
from typing import Any, Optional

import httpx

from app.core.config import settings


class LLMError(RuntimeError):
    pass


def llm_enabled() -> bool:
    return bool(settings.llm_api_base and settings.llm_model)


def _chat_completions_urls() -> list[str]:
    """
    返回可尝试的 chat/completions 地址（按优先级）。
    - OpenAI 兼容：优先 /v1/chat/completions
    - OpenClaw：部分部署可能是 /chat/completions，因此增加回退
    """
    base = settings.llm_api_base.rstrip("/")
    if not base:
        return []
    if base.endswith("/chat/completions"):
        return [base]

    primary = f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"
    urls = [primary]

    provider = (getattr(settings, "llm_provider", "") or "").strip().lower()
    if provider == "openclaw":
        fallback = f"{base}/chat/completions"
        if fallback not in urls:
            urls.append(fallback)
    return urls


def _chat_completions_url() -> str:
    # 兼容旧测试与调用方
    urls = _chat_completions_urls()
    return urls[0] if urls else ""


def _mock_chat(messages: list[dict[str, str]], max_tokens: int) -> str:
    """桩数据：用于 MOCK_LLM=1 时跑通全流程，不调真实 API。"""
    raw = str(messages)
    # 仅在明确要求生成章节大纲 JSON（且包含 hook_payoff_chapter 语义）时返回 {"chapters": [...]}。
    # 否则会误伤：例如“策划案/书名”生成 prompt 中带到 chapters 字样时也被错误返回 JSON。
    if (
        "chapters" in raw
        and "hook_payoff_chapter" in raw
        and ("只输出" in raw or "JSON" in raw)
    ):
        stub_chapters = [
            {
                "title": f"第{i}章 桩数据",
                "theme": "主题",
                "event": "核心事件",
                "connection": "承接上章",
                "hook": "悬念",
                "hook_payoff_chapter": min(i + 3, 500),
            }
            for i in range(1, 501)
        ]
        return json.dumps({"chapters": stub_chapters}, ensure_ascii=False)
    if "请对以下章节" in raw or "润色" in raw or "修订" in raw:
        return "# 第1章\n\n（桩数据正文内容）\n\n" + "测试段落。\n" * 50
    return "# 桩数据报告\n\n## 一、数据概览\n\n本报告为 MOCK_LLM 模式。\n"


def chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 1200,
    timeout_s: float = 60,
    retries: int = 3,
    retry_backoff_s: float = 1.5,
) -> str:
    """
    调用 OpenAI 兼容 chat/completions，返回文本。
    适配 DeepSeek：base_url=https://api.deepseek.com model=deepseek-chat/deepseek-reasoner
    """
    if getattr(settings, "mock_llm", False):
        return _mock_chat(messages, max_tokens)
    if not llm_enabled():
        raise LLMError("LLM 未配置：请设置 LLM_API_BASE / LLM_MODEL（以及 LLM_API_KEY）")

    urls = _chat_completions_urls()
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    # 多数 API（如 DeepSeek）上限 8192，超出会 400
    max_tokens_capped = min(max_tokens, 8192)
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens_capped,
        "stream": False,
    }

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            data: dict[str, Any] | None = None
            errs: list[str] = []
            with httpx.Client(timeout=timeout_s) as client:
                for url in urls:
                    r = client.post(url, headers=headers, json=payload)
                    if r.status_code >= 400:
                        errs.append(f"{url} -> HTTP {r.status_code}: {r.text[:300]}")
                        continue
                    data = r.json()
                    break
            if data is None:
                raise LLMError("; ".join(errs) if errs else "请求失败")
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if isinstance(content, list):
                # 兼容部分实现返回分段结构（如 [{"type":"text","text":"..."}]）
                content = "".join(
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in content
                )
            if not content:
                raise LLMError("返回内容为空")
            return content
        except Exception as e:
            last_err = e
            if attempt >= retries:
                break
            time.sleep(retry_backoff_s * (attempt + 1))
    raise LLMError(f"LLM 调用失败：{type(last_err).__name__}: {last_err}")


def _mock_chat_json(messages: list[dict[str, str]]) -> dict[str, Any]:
    """桩数据：chat_json 的 mock 返回，保证各 Agent 能解析。"""
    raw = str(messages)
    # 策划案审核：PlannerAgent 需要固定 schema（pass/overall_reason/items/fix）
    # 放在最前面，避免被“风格打分”之类的宽松 mock 分支误命中。
    if (
        "核心设定" in raw
        and "人设矩阵" in raw
        and "完整故事线" in raw
        and "章节规模建议" in raw
    ):
        return {
            "pass": True,
            "overall_reason": "MOCK 通过",
            "items": [
                {"key": "核心设定", "pass": True, "reason": "", "fix": []},
                {"key": "人设矩阵", "pass": True, "reason": "", "fix": []},
                {"key": "完整故事线", "pass": True, "reason": "", "fix": []},
                {"key": "章节规模建议", "pass": True, "reason": "", "fix": []},
            ],
            "fix": [],
        }
    if "top_genres" in raw or "平台" in raw:
        return {
            "analysis_time": "2024-01-01",
            "platforms": ["起点", "番茄"],
            "top_genres": [{"genre": "玄幻/修仙", "share": 0.35, "notes": ["桩"]}],
            "top_tags": ["逆袭", "打脸"],
            "actionable_brief": {"recommended_tracks": ["玄幻系统流"]},
        }
    if "chapters_to_rewrite" in raw or "审计" in raw:
        return {"pass": True, "chapters_to_rewrite": [], "scores": {}}
    if "style" in raw and "character" in raw and "plot" in raw:
        return {
            "style": 20, "character": 18, "plot": 18, "emotion": 12, "language": 9, "originality": 9,
            "need_regenerate": False,
        }

    # 章节大纲分批生成：Planner 使用 llm.chat_json 并期望严格返回 {"chapters": [ ... ]}。
    # mock 也要遵循这个结构，否则会出现 need=N got=0 的校验失败。
    # 仅用于「章节大纲分批生成」：其提示里会明确要求 hook_payoff_chapter 的语义。
    # 否则其它审计 JSON（只需 pass/fix）会误命中，导致缺少 pass 字段从而被判不通过。
    if (
        "hook_payoff_chapter" in raw
        and "计划在第几章展开" in raw
        and "chapters" in raw
        and ("只输出" in raw or "JSON" in raw)
    ):
        import re as _re
        n = 5
        m = _re.search(r"共\s*(\d+)\s*章", raw)
        if not m:
            m = _re.search(r"为\s*(\d+)\s*条", raw)
        if m:
            try:
                n = int(m.group(1))
            except Exception:
                n = 5
        stub_chapters = [
            {
                "title": f"第{i}章 桩数据",
                "theme": "主题",
                "event": "核心事件",
                "connection": "承接上章",
                "hook": "悬念",
                "hook_payoff_chapter": min(i + 3, n),
            }
            for i in range(1, n + 1)
        ]
        return {"chapters": stub_chapters}

    return {"pass": True, "reason": "MOCK 通过", "fix": [], "chapters": []}


def chat_json(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    timeout_s: float = 60,
    retries: int = 3,
) -> dict[str, Any]:
    """
    要求模型输出 JSON（严格），并解析返回 dict。
    """
    if getattr(settings, "mock_llm", False):
        return _mock_chat_json(messages)
    text = chat(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_s=timeout_s,
        retries=retries,
    )
    try:
        return parse_json(text)
    except LLMError as e0:
        # 尝试用“JSON 修复器”多次兜底，避免 planner/review 只因轻微 JSON 问题失败。
        if getattr(settings, "mock_llm", False):
            raise e0

        fix_prompt = [
            {
                "role": "system",
                "content": "你是 JSON 修复器。请把用户给的内容修复成严格 JSON（RFC8259）。只输出 JSON，不要围栏，不要解释。",
            },
            {
                "role": "user",
                "content": f"请修复以下内容为严格 JSON：\n\n{text[:20000]}",
            },
        ]
        last_err: Exception | None = e0
        # 追加修复回合：有些模型会先给半截 JSON，再补完整
        for _ in range(3):
            fixed_text = chat(
                fix_prompt,
                temperature=0.0,
                max_tokens=min(max_tokens, 2200),
                timeout_s=timeout_s,
                retries=retries,
            )
            try:
                return parse_json(fixed_text)
            except LLMError as e1:
                last_err = e1

        raise last_err if last_err else e0


def parse_json(text: str) -> dict[str, Any]:
    """
    更稳健的 JSON 解析：
    - 去掉 ```json 围栏
    - 尝试截取第一个 { 到最后一个 } 之间的内容
    """
    t = text.strip()
    if t.startswith("```"):
        # 去掉首尾围栏
        t = t.strip().strip("`")
        if t.lower().startswith("json"):
            t = t[4:].strip()
    # 优先尝试原文
    try:
        return json.loads(t)
    except Exception:
        pass
    # 兜底策略：
    # 1) 只保留第一个 { 到某个匹配的闭合 } 的完整片段（考虑字符串内的括号）
    # 2) 如果仍失败，尝试简单清理：去尾随逗号、替换 True/False/None

    def _simple_cleanup(s: str) -> str:
        import re as _re
        s2 = s
        # 去除代码块残留反引号
        s2 = s2.replace("```", "")
        # 去除尾随逗号：{ "a":1, } 或 [1, ]
        s2 = _re.sub(r",(\s*[}\]])", r"\1", s2)
        # 对象之间缺少逗号：} 后面紧跟 {（在数组内）改为 },
        s2 = _re.sub(r"\}\s*(\s*)\{", r"}, \1{", s2)
        # True/False/None
        s2 = s2.replace(": True", ": true").replace(": False", ": false").replace(": None", ": null")
        s2 = _re.sub(r":\s*True\b", ": true", s2)
        s2 = _re.sub(r":\s*False\b", ": false", s2)
        s2 = _re.sub(r":\s*None\b", ": null", s2)
        return s2

    # 取第一个对象起点
    try:
        start = t.index("{")
    except ValueError:
        raise LLMError(f"JSON 解析失败：未找到 '{{'；原始输出前 800 字：{text[:800]}")

    s = t[start:]
    # 扫描寻找可解析的最外层 JSON 片段
    in_str = False
    escape = False
    depth = 0
    candidates: list[str] = []
    obj_start = None
    for i, ch in enumerate(s):
        if obj_start is None and ch == "{":
            obj_start = i
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "\"":
                in_str = False
            continue
        else:
            if ch == "\"":
                in_str = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and obj_start is not None:
                    cand = s[obj_start : i + 1]
                    candidates.append(cand)

    # 尝试解析候选
    last_err: Exception | None = None
    for cand in candidates[:5]:
        try:
            return json.loads(_simple_cleanup(cand))
        except Exception as e:
            last_err = e

    # 最后再尝试：从第一个 { 到最后一个 }
    try:
        end = t.rindex("}")
        t2 = t[start : end + 1]
        return json.loads(_simple_cleanup(t2))
    except Exception as e:
        # 追加尝试：若疑似截断导致“缺少尾括号”，尝试补齐 } 再解析
        if last_err is None:
            last_err = e
        try:
            s_full = t[start:]
            # 估算缺少的右括号数（忽略字符串内内容）
            in_str2 = False
            escape2 = False
            depth2 = 0
            for ch in s_full:
                if in_str2:
                    if escape2:
                        escape2 = False
                    elif ch == "\\":
                        escape2 = True
                    elif ch == "\"":
                        in_str2 = False
                    continue
                if ch == "\"":
                    in_str2 = True
                    continue
                if ch == "{":
                    depth2 += 1
                elif ch == "}":
                    depth2 -= 1
                    if depth2 < 0:
                        depth2 = 0
            # 如果模型截断导致缺少尾部 `}`，depth2 可能为 0（例如某些括号在字符串中被误计）。
            # 这种情况下仍尝试补一个 `}`，提高“最后截断 JSON”的可解析性。
            append_count = depth2 if depth2 > 0 else 1
            t2 = s_full + ("}" * append_count)
            return json.loads(_simple_cleanup(t2))
        except Exception:
            pass
        # chapters 专用兜底：从 "chapters":[ 后逐条解析对象，拼成合法 JSON
        if "chapters" in t and "[" in t:
            try:
                import re as _re
                m = _re.search(r'"chapters"\s*:\s*\[', t)
                if m:
                    rest = t[m.end() :]
                    items = []
                    depth = 0
                    start_i = 0
                    for i, ch in enumerate(rest):
                        if ch == "{":
                            if depth == 0:
                                start_i = i
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                seg = rest[start_i : i + 1]
                                try:
                                    obj = json.loads(_simple_cleanup(seg))
                                    items.append(obj)
                                except Exception:
                                    pass
                    if items:
                        return {"chapters": items}
            except Exception:
                pass
        raise LLMError(f"JSON 解析失败：{type(last_err).__name__}: {last_err}；原始输出前 800 字：{text[:800]}")

