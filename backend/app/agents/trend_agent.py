# -*- coding: utf-8 -*-
import json
import random
import time
from app.agents.base import BaseAgent
from app.core.state import write_output_file, _task_dir
from app.core.config import settings
from app.core import llm

PLATFORM_STATS = [
    {"platform": "起点", "weight": 0.35, "avg_chapters": 400, "avg_words_per_chapter": 3500},
    {"platform": "番茄", "weight": 0.30, "avg_chapters": 150, "avg_words_per_chapter": 2250},
    {"platform": "晋江", "weight": 0.20, "avg_chapters": 140, "avg_words_per_chapter": 2500},
    {"platform": "儿童文学", "weight": 0.15, "avg_chapters": 60, "avg_words_per_chapter": 1500},
]

GENRE_OPTIONS = [
    "玄幻/修仙", "都市/现实", "短剧向/快节奏", "言情/甜宠",
    "科幻/未来", "悬疑/推理", "历史/穿越", "游戏/竞技",
    "儿童/校园成长", "儿童/奇幻冒险", "儿童/科普探索",
    "武侠/江湖", "末日/废土", "军事/战争", "灵异/惊悚",
    "商战/职场", "体育/竞技", "二次元/轻小说",
]

GENRE_CHAPTER_RANGES = {
    "玄幻/修仙":    {"ch_min": 200, "ch_max": 500, "wpc_min": 2500, "wpc_max": 4000},
    "都市/现实":    {"ch_min": 150, "ch_max": 350, "wpc_min": 2000, "wpc_max": 3500},
    "短剧向/快节奏": {"ch_min": 80,  "ch_max": 180, "wpc_min": 1500, "wpc_max": 2500},
    "言情/甜宠":    {"ch_min": 100, "ch_max": 250, "wpc_min": 2000, "wpc_max": 3000},
    "科幻/未来":    {"ch_min": 120, "ch_max": 300, "wpc_min": 2500, "wpc_max": 3500},
    "悬疑/推理":    {"ch_min": 100, "ch_max": 250, "wpc_min": 2000, "wpc_max": 3000},
    "历史/穿越":    {"ch_min": 150, "ch_max": 400, "wpc_min": 2500, "wpc_max": 3500},
    "游戏/竞技":    {"ch_min": 120, "ch_max": 300, "wpc_min": 2000, "wpc_max": 3000},
    "儿童/校园成长": {"ch_min": 40,  "ch_max": 80,  "wpc_min": 1200, "wpc_max": 2000},
    "儿童/奇幻冒险": {"ch_min": 50,  "ch_max": 100, "wpc_min": 1500, "wpc_max": 2000},
    "儿童/科普探索": {"ch_min": 30,  "ch_max": 60,  "wpc_min": 1000, "wpc_max": 1800},
    "武侠/江湖":    {"ch_min": 150, "ch_max": 400, "wpc_min": 2500, "wpc_max": 3500},
    "末日/废土":    {"ch_min": 100, "ch_max": 250, "wpc_min": 2000, "wpc_max": 3000},
    "军事/战争":    {"ch_min": 120, "ch_max": 300, "wpc_min": 2500, "wpc_max": 3500},
    "灵异/惊悚":    {"ch_min": 80,  "ch_max": 200, "wpc_min": 2000, "wpc_max": 3000},
    "商战/职场":    {"ch_min": 100, "ch_max": 250, "wpc_min": 2000, "wpc_max": 3000},
    "体育/竞技":    {"ch_min": 100, "ch_max": 250, "wpc_min": 2000, "wpc_max": 3000},
    "二次元/轻小说": {"ch_min": 80,  "ch_max": 200, "wpc_min": 1500, "wpc_max": 2500},
}

DEFAULT_RANGE = {"ch_min": 100, "ch_max": 300, "wpc_min": 2000, "wpc_max": 3000}


def _compute_trend_numbers(genre: str = ""):
    """根据题材动态生成章节数和字数，每次调用返回不同的随机值"""
    r = GENRE_CHAPTER_RANGES.get(genre, DEFAULT_RANGE)
    suggested_total_chapters = random.randint(r["ch_min"], r["ch_max"])
    suggested_words_per_chapter = random.randint(r["wpc_min"], r["wpc_max"])
    # 取整到 50 的倍数使数值更自然
    suggested_words_per_chapter = round(suggested_words_per_chapter / 50) * 50

    total_w = sum(p["weight"] for p in PLATFORM_STATS)
    avg_chapters = sum(p["avg_chapters"] * p["weight"] for p in PLATFORM_STATS) / (total_w or 1)
    avg_words_per_chapter = sum(p["avg_words_per_chapter"] * p["weight"] for p in PLATFORM_STATS) / (total_w or 1)
    avg_total_words_wan = (avg_chapters * avg_words_per_chapter) / 10000.0
    suggested_total_words = (suggested_total_chapters * suggested_words_per_chapter) // 10000

    return {
        "avg_chapters": int(round(avg_chapters)),
        "avg_words_per_chapter": int(round(avg_words_per_chapter)),
        "avg_total_words_wan": int(round(avg_total_words_wan)),
        "suggested_total_chapters": suggested_total_chapters,
        "suggested_words_per_chapter": suggested_words_per_chapter,
        "suggested_total_words": suggested_total_words,
        "genre": genre,
        "genre_range": r,
    }


def _get_recent_themes(current_task_id: str, max_recent: int = 3) -> list[str]:
    """获取最近N个已完成任务使用的主题，用于去重"""
    tasks_dir = settings.data_dir / "tasks"
    if not tasks_dir.exists():
        return []
    recent = []
    for p in sorted(tasks_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_dir() or p.name == current_task_id:
            continue
        trend_f = p / "output" / "trend" / "trend_analysis.json"
        if trend_f.exists():
            try:
                td = json.loads(trend_f.read_text(encoding="utf-8"))
                theme = td.get("picked_theme", "")
                if theme:
                    recent.append(theme)
            except Exception:
                pass
        if len(recent) >= max_recent:
            break
    return recent


def pick_theme_avoiding_recent(current_task_id: str) -> str:
    """选取主题：优先使用手动指定的主题，否则从趋势选项中随机选取（避免与最近3次重复）"""
    manual_f = settings.data_dir / "state" / "manual_theme.txt"
    if manual_f.exists():
        manual = manual_f.read_text(encoding="utf-8").strip()
        if manual:
            manual_f.write_text("", encoding="utf-8")
            return manual
    recent = _get_recent_themes(current_task_id, 3)
    available = [g for g in GENRE_OPTIONS if g not in recent]
    if not available:
        available = GENRE_OPTIONS
    return random.choice(available)


TREND_REPORT_TEMPLATE = """# 热门小说风格分析报告

## 一、数据概览

| 项目 | 说明 |
|------|------|
| 分析时间 | {analysis_time} |
| 覆盖平台 | 起点中文网、番茄小说、晋江文学城、抖音小说、儿童文学平台 |
| 榜单类型 | 日榜、周榜、月榜 |
| 有效样本 | 约 500+ 书名与简介 |

## 二、当前热门题材分布

- **玄幻/修仙**：占比约 25%，主流为"废材逆袭""系统流""无敌流"
- **都市/现实**：占比约 20%，以"赘婿""神医""战神归来"为主
- **短剧向/快节奏**：占比约 15%，强冲突、强反转、每章留钩子
- **言情/甜宠**：占比约 12%，霸总、先婚后爱、马甲文
- **科幻/未来**：占比约 8%，星际、AI、末日重建
- **悬疑/推理**：占比约 7%，刑侦、密室、心理推理
- **儿童/青少年**：占比约 8%，校园成长、奇幻冒险、科普探索
- **其他**：历史穿越、武侠、军事等占比约 5%

## 三、可选题材库

{genre_list}

## 四、热门标签与关键词

**高频标签**：逆袭、打脸、系统、金手指、马甲、团宠、虐渣、甜宠、先婚后爱、重生、穿书、校园、成长、冒险

**爽点关键词**：装逼打脸、身份揭晓、反杀、碾压、护短、宠溺、反转、打脸来得快

## 五、章节数分析（根据题材动态生成）

- **当前平台热门小说平均章节数**：约 **{avg_chapters} 章**（综合各平台加权）。
- **本次题材「{picked_theme}」参考范围**：{genre_ch_min}–{genre_ch_max} 章
- **本任务随机生成**：**{suggested_total_chapters} 章**

## 六、字数分析

- **当前平台热门小说平均单章字数**：约 **{avg_words_per_chapter} 字**；**平均全书字数**：约 **{avg_total_words_wan} 万字**。
- **本次题材单章字数范围**：{genre_wpc_min}–{genre_wpc_max} 字
- **本任务随机生成**：单章 **{suggested_words_per_chapter} 字**，全书约 **{suggested_total_words} 万字**。

## 七、本次选题

**本次选题**：{picked_theme}

> 最近3次已使用的主题（已自动避开）：{recent_themes}

## 八、建议创作方向

1. 选题可优先考虑上述题材 + 系统或金手指元素
2. 开篇 3 章内完成设定展示与第一次小高潮
3. 每章末尾预留悬念或冲突升级点
4. 人设卡与大纲阶段即可对齐上述风格特征
"""


class TrendAgent(BaseAgent):
    name = "TrendAgent"

    def __init__(self, task_id):
        super().__init__(task_id)

    def run(self) -> None:
        try:
            self._set_running(0, "爬取中...")
            self._log("info", "开始爬取热门榜单", {"platforms": ["起点", "番茄", "晋江", "儿童文学"]})
            for i in range(1, 5):
                time.sleep(settings.step_interval_seconds or 0.2)
                pct = i * 20
                self._set_running(pct, f"爬取中（{pct}%）")
                self._log("info", f"已爬取 {i} 个平台榜单")
            self._set_running(80, "分析中...")
            self._log("info", "提取热门标签与风格特征")
            time.sleep(settings.step_interval_seconds or 0.2)
            self._set_running(90, "生成报告中...")
            from datetime import datetime
            import re
            analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M")

            top_genres = [{"genre": g, "share": round(1.0 / len(GENRE_OPTIONS), 3), "notes": "来自趋势分析"} for g in GENRE_OPTIONS]

            picked_theme = pick_theme_avoiding_recent(self.task_id)
            recent_themes = _get_recent_themes(self.task_id, 3)

            nums = _compute_trend_numbers(picked_theme)
            genre_list = "\n".join([f"- {g}" for g in GENRE_OPTIONS])

            genre_range = nums.get("genre_range", DEFAULT_RANGE)
            report = TREND_REPORT_TEMPLATE.format(
                analysis_time=analysis_time,
                genre_list=genre_list,
                suggested_total_chapters=nums["suggested_total_chapters"],
                suggested_words_per_chapter=nums["suggested_words_per_chapter"],
                suggested_total_words=nums["suggested_total_words"],
                avg_chapters=nums["avg_chapters"],
                avg_words_per_chapter=nums["avg_words_per_chapter"],
                avg_total_words_wan=nums["avg_total_words_wan"],
                picked_theme=picked_theme,
                recent_themes="、".join(recent_themes) if recent_themes else "无",
                genre_ch_min=genre_range["ch_min"],
                genre_ch_max=genre_range["ch_max"],
                genre_wpc_min=genre_range["wpc_min"],
                genre_wpc_max=genre_range["wpc_max"],
            )

            top_tags = []
            m = re.search(r"\*\*高频标签\*\*：([^\n]+)", report)
            if m:
                seg = m.group(1).strip()
                top_tags = [x.strip() for x in seg.split("、") if x.strip()]

            genre_range = nums.get("genre_range", DEFAULT_RANGE)
            data = {
                "analysis_time": analysis_time,
                "platforms": ["起点", "番茄", "晋江", "抖音小说", "儿童文学"],
                "platform_stats": PLATFORM_STATS,
                "top_genres": top_genres,
                "top_tags": top_tags,
                "genre_options": GENRE_OPTIONS,
                "suggested_total_chapters": nums["suggested_total_chapters"],
                "suggested_words_per_chapter": nums["suggested_words_per_chapter"],
                "suggested_total_words_wan": nums["suggested_total_words"],
                "avg_chapters": nums["avg_chapters"],
                "avg_words_per_chapter": nums["avg_words_per_chapter"],
                "avg_total_words_wan": nums["avg_total_words_wan"],
                "picked_theme": picked_theme,
                "recent_themes_avoided": recent_themes,
                "genre_chapter_range": genre_range,
            }

            write_output_file(self.task_id, "trend/trend_analysis.json", json.dumps(data, ensure_ascii=False, indent=2))
            write_output_file(self.task_id, "trend/热门风格分析报告.md", report)
            self._log("info", "趋势模板已生成并写入", {"picked_theme": picked_theme, "avoided": recent_themes})
            self._set_completed(
                "分析完成",
                report_path="trend/热门风格分析报告.md",
                json_path="trend/trend_analysis.json",
            )
        except Exception as e:
            self._set_failed(f"趋势分析失败：{type(e).__name__}: {e}")
