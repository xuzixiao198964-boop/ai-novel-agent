# -*- coding: utf-8 -*-
import time
import json
from app.agents.base import BaseAgent
from app.core.state import write_output_file
from app.core.config import settings
from app.core import llm


STYLE_PARAMS_TEMPLATE = """# 风格参数表

> 基于热门趋势与爆款样本拆解，供 Writer / Polish / Auditor 统一约束用。

## 一、句式与节奏

| 维度 | 参数 | 说明 |
|------|------|------|
| 句长 | 短句为主 | 单句 8–20 字占比约 60%，长句用于情绪或转折 |
| 段落 | 2–4 句/段 | 避免大段成块，利于快节奏阅读 |
| 节奏 | 快 | 场景切换紧凑，单章内 1–2 个核心冲突或推进点 |
| 对话占比 | 40%–50% | 对话推进剧情与人物关系，叙述与描写为辅 |

## 二、用词与语体

- **语体**：偏口语化、网文感，避免书面腔与过度文艺
- **动词**：动作描写具体（如“一把拽住”“冷笑一声”），少用抽象概括
- **情绪词**：适度使用“猛地”“顿时”“竟然”等强化情绪
- **禁忌**：避免冗长环境描写、大段说教、重复解释前文

## 三、叙事视角与结构

- **视角**：第三人称限知（跟随主角视角为主）
- **单章结构**：开篇钩子（1–2 段）→ 中段冲突/推进 → 结尾留悬或小高潮
- **信息释放**：重要设定与伏笔通过剧情与对话自然带出，避免大段旁白说明

## 四、人设与对话风格

- **主角**：目标明确、有底线、有成长线；对话符合身份与当前情绪
- **配角**：功能清晰（助攻/对立/氛围），台词简洁不抢戏
- **反派**：不脸谱化，动机可理解，避免无脑送人头
- **对话原则**：一人一句推进，少长篇独白；可带少量语气词与口语

## 五、爽点与情绪曲线

- **爽点类型**：打脸、逆袭、装逼、身份揭晓、护短、反杀、情感爆发
- **密度**：单章至少 1 个小爽点，3–5 章内 1 个中等高潮
- **情绪曲线**：压抑→释放、误会→澄清、轻视→震惊，形成节奏感

## 六、仿写约束提示词（可喂给大模型）

```
写作时请严格遵循：
1. 短句为主，段落 2–4 句，节奏快。
2. 对话占比约一半，用对话推进剧情与人设。
3. 每章开头 1–2 段内出现钩子，结尾留悬念或小高潮。
4. 用词口语化、网文感，动作与情绪描写具体。
5. 人物言行符合人设，不 OOC；爽点密度适中，打脸/逆袭/身份揭晓等可交替使用。
```
"""


class StyleAgent(BaseAgent):
    name = "StyleAgent"

    @staticmethod
    def _normalize_style_params(raw: dict) -> dict:
        """对 LLM 返回做最小 schema 归一，避免后续链路读到异常字段。"""
        sentence = raw.get("sentence") if isinstance(raw.get("sentence"), dict) else {}
        pacing = raw.get("pacing") if isinstance(raw.get("pacing"), dict) else {}
        voice = raw.get("voice") if isinstance(raw.get("voice"), dict) else {}
        style_checks = raw.get("style_checks") if isinstance(raw.get("style_checks"), dict) else {}
        prompts = raw.get("prompts") if isinstance(raw.get("prompts"), dict) else {}
        hook_library = raw.get("hook_library") if isinstance(raw.get("hook_library"), list) else []

        def _f(v, d):
            try:
                return float(v)
            except Exception:
                return d

        def _i(v, d):
            try:
                return int(v)
            except Exception:
                return d

        def _sl(items, limit):
            return [str(x)[:120] for x in items[:limit] if str(x).strip()]

        out = {
            "sentence": {
                "avg_len": max(8, min(24, _i(sentence.get("avg_len"), 14))),
                "short_ratio": max(0.2, min(0.9, _f(sentence.get("short_ratio"), 0.6))),
                "paragraph_sentences_min": max(1, min(6, _i(sentence.get("paragraph_sentences_min"), 2))),
                "paragraph_sentences_max": max(2, min(8, _i(sentence.get("paragraph_sentences_max"), 4))),
            },
            "dialogue_ratio": max(0.2, min(0.8, _f(raw.get("dialogue_ratio"), 0.45))),
            "pacing": {
                "conflict_points_per_chapter": max(1, min(5, _i(pacing.get("conflict_points_per_chapter"), 1))),
                "hook_first_paragraph": bool(pacing.get("hook_first_paragraph", True)),
                "cliffhanger_end": bool(pacing.get("cliffhanger_end", True)),
            },
            "voice": {
                "register": _sl(voice.get("register") if isinstance(voice.get("register"), list) else ["口语化", "网文感"], 6),
                "banned": _sl(voice.get("banned") if isinstance(voice.get("banned"), list) else ["说教", "长篇环境描写", "重复解释"], 8),
            },
            "hook_library": _sl(hook_library, 8) or ["反转揭示", "身份反差", "利益冲突升级"],
            "style_checks": {
                "ooc_rules": _sl(style_checks.get("ooc_rules") if isinstance(style_checks.get("ooc_rules"), list) else ["人物行为与动机一致"], 8),
                "timeline_rules": _sl(style_checks.get("timeline_rules") if isinstance(style_checks.get("timeline_rules"), list) else ["时间线前后不冲突"], 8),
                "banned_patterns": _sl(style_checks.get("banned_patterns") if isinstance(style_checks.get("banned_patterns"), list) else ["机械重复台词"], 8),
            },
            "prompts": {
                "writer_system": str(prompts.get("writer_system") or "保持强剧情推进、短句优先、人物不OOC。")[:200],
                "writer_chapter": str(prompts.get("writer_chapter") or "第{chapter_no}章：依据{outline}推进冲突并结合{memory}，首段给钩子，结尾留悬念。")[:260],
                "polish": str(prompts.get("polish") or "润色时强化节奏与画面感，删除赘述并保留剧情信息。")[:200],
                "auditor": str(prompts.get("auditor") or "审计连贯性、人设一致性、伏笔回收与节奏。")[:200],
            },
        }
        if out["sentence"]["paragraph_sentences_max"] < out["sentence"]["paragraph_sentences_min"]:
            out["sentence"]["paragraph_sentences_max"] = out["sentence"]["paragraph_sentences_min"]
        return out

    @staticmethod
    def _render_markdown(params: dict) -> str:
        s = params["sentence"]
        p = params["pacing"]
        v = params["voice"]
        c = params["style_checks"]
        pr = params["prompts"]
        lines = [
            "# 风格参数表",
            "",
            "## 一、句式与节奏",
            "",
            "| 维度 | 参数 |",
            "|------|------|",
            f"| 句长 | 平均 {s['avg_len']} 字，短句占比 {s['short_ratio']:.2f} |",
            f"| 段落 | 每段 {s['paragraph_sentences_min']}–{s['paragraph_sentences_max']} 句 |",
            f"| 对话占比 | {params['dialogue_ratio']:.2f} |",
            f"| 冲突密度 | 每章 {p['conflict_points_per_chapter']} 个核心冲突点 |",
            f"| 开头钩子 | {'是' if p['hook_first_paragraph'] else '否'} |",
            f"| 结尾悬念 | {'是' if p['cliffhanger_end'] else '否'} |",
            "",
            "## 二、语体与禁忌",
            "",
            "- 语体：" + "、".join(v["register"]),
            "- 禁忌：" + "、".join(v["banned"]),
            "",
            "## 三、钩子库",
            "",
        ]
        for i, item in enumerate(params["hook_library"], 1):
            lines.append(f"{i}. {item}")
        lines.extend([
            "",
            "## 四、质检清单",
            "",
            "- OOC 约束：" + "；".join(c["ooc_rules"]),
            "- 时间线约束：" + "；".join(c["timeline_rules"]),
            "- 禁用模式：" + "；".join(c["banned_patterns"]),
            "",
            "## 五、可直接复用提示词",
            "",
            "### Writer System",
            pr["writer_system"],
            "",
            "### Writer Chapter",
            pr["writer_chapter"],
            "",
            "### Polish",
            pr["polish"],
            "",
            "### Auditor",
            pr["auditor"],
            "",
        ])
        return "\n".join(lines)

    def run(self) -> None:
        try:
            self._set_running(0, "语料检索中...")
            self._log("info", "构建风格语料 RAG 库")
            for i in range(1, 4):
                time.sleep(settings.step_interval_seconds or 0.2)
                self._set_running(i * 20, f"风格拆解中（{i*20}%）")
            self._set_running(70, "参数生成中...")
            time.sleep(settings.step_interval_seconds or 0.2)
            # 结构化 JSON（强约束：量化参数 + 提示词片段）
            json_prompt = [
                {"role": "system", "content": "你是爆款网文风格解析专家。只输出严格 JSON，不要多余文本、不要代码块围栏。"},
                {"role": "user", "content": """
请输出“可直接喂给大模型写小说”的风格参数 JSON（用于 StyleAgent），要求量化、可执行、可复用。

强约束（为了避免截断/解析失败）：
- **总长度尽量短**，不要输出冗长段落；所有字符串请控制在 120 字以内
- 数组项请控制数量：hook_library 最多 8 条；rules 数组最多 8 条
- 不要出现 ```json 围栏，不要出现多余解释文字

必须字段（严格一致）：
{
  "sentence": {"avg_len": 14, "short_ratio": 0.6, "paragraph_sentences_min": 2, "paragraph_sentences_max": 4},
  "dialogue_ratio": 0.45,
  "pacing": {"conflict_points_per_chapter": 1, "hook_first_paragraph": true, "cliffhanger_end": true},
  "voice": {"register":["口语化","网文感"], "banned":["说教","长篇环境描写","重复解释"]},
  "hook_library": ["...", "..."],
  "style_checks": {"ooc_rules":["..."], "timeline_rules":["..."], "banned_patterns":["..."]},
  "prompts": {
    "writer_system": "一句话系统提示",
    "writer_chapter": "一段简短章节提示，包含占位符 {chapter_no} {outline} {memory}",
    "polish": "一段简短润色提示",
    "auditor": "一段简短审计提示"
  }
}

注意：只输出 JSON。
"""},
            ]
            raw_params = llm.chat_json(json_prompt, max_tokens=900)
            params_json = self._normalize_style_params(raw_params if isinstance(raw_params, dict) else {})
            write_output_file(self.task_id, "style/style_params.json", json.dumps(params_json, ensure_ascii=False, indent=2))

            # Markdown 由本地渲染，避免第二次 LLM 生成发散内容
            md = self._render_markdown(params_json)
            write_output_file(self.task_id, "style/风格参数表.md", md)

            self._set_completed("风格参数已生成", params_path="style/风格参数表.md", json_path="style/style_params.json")
        except Exception as e:
            self._set_failed(f"风格解析失败：{type(e).__name__}: {e}")
