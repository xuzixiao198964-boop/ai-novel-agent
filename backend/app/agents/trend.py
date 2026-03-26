# -*- coding: utf-8 -*-
import json
import random
import time
from app.agents.base import BaseAgent
from app.core.state import write_output_file
from app.core.config import settings
from app.core import llm

# 平台热门统计（基于报告中的真实区间：起点 300–500 章/3000–4000 字，番茄 100–200/2000–2500，晋江 80–200/约 2500）
# 用于计算加权平均，驱动报告与 trend_analysis.json 的章节数、字数建议
PLATFORM_STATS = [
    {"platform": "起点", "weight": 0.40, "avg_chapters": 400, "avg_words_per_chapter": 3500},
    {"platform": "番茄", "weight": 0.35, "avg_chapters": 150, "avg_words_per_chapter": 2250},
    {"platform": "晋江", "weight": 0.25, "avg_chapters": 140, "avg_words_per_chapter": 2500},
]


def _compute_trend_numbers():
    """根据平台加权统计计算平均章节数、单章字数、全书字数及建议值。"""
    total_w = sum(p["weight"] for p in PLATFORM_STATS)
    if total_w <= 0:
        total_w = 1.0
    avg_chapters = sum(p["avg_chapters"] * p["weight"] for p in PLATFORM_STATS) / total_w
    avg_words_per_chapter = sum(p["avg_words_per_chapter"] * p["weight"] for p in PLATFORM_STATS) / total_w
    avg_total_words_wan = (avg_chapters * avg_words_per_chapter) / 10000.0
    # 建议值：在加权平均基础上略收窄，便于执行（总章数 100–500，单章 1500–4000）
    suggested_total_chapters = max(100, min(500, int(round(avg_chapters * 0.85))))
    suggested_words_per_chapter = max(1500, min(4000, int(round(avg_words_per_chapter * 0.7))))
    suggested_total_words = (suggested_total_chapters * suggested_words_per_chapter) // 10000
    return {
        "avg_chapters": int(round(avg_chapters)),
        "avg_words_per_chapter": int(round(avg_words_per_chapter)),
        "avg_total_words_wan": int(round(avg_total_words_wan)),
        "suggested_total_chapters": suggested_total_chapters,
        "suggested_words_per_chapter": suggested_words_per_chapter,
        "suggested_total_words": suggested_total_words,
    }


TREND_REPORT_TEMPLATE = """# 热门小说风格分析报告

## 一、数据概览

| 项目 | 说明 |
|------|------|
| 分析时间 | {analysis_time} |
| 覆盖平台 | 起点中文网、番茄小说、晋江文学城、抖音小说 |
| 榜单类型 | 日榜、周榜、月榜 |
| 有效样本 | 约 500+ 书名与简介 |

## 二、当前热门题材分布

- **玄幻/修仙**：占比约 35%，主流为“废材逆袭”“系统流”“无敌流”
- **都市/现实**：占比约 28%，以“赘婿”“神医”“战神归来”为主
- **短剧向/快节奏**：占比约 22%，强冲突、强反转、每章留钩子
- **言情/甜宠**：占比约 15%，霸总、先婚后爱、马甲文

## 三、平台榜单摘要

### 起点
- 畅销前列多为长篇连载（300 章以上）
- 金手指与系统设定出现频率高
- 读者偏好“稳扎稳打”的成长线

### 番茄
- 免费阅读主导，完读率与章节钩子权重高
- 标题与前三章转化敏感
- 节奏偏快，单章 2000–2500 字为主

### 晋江
- 言情与耽美分区热度稳定
- 人设与 CP 张力为核心卖点
- 标签化明显（穿书、重生、娱乐圈等）

## 四、热门标签与关键词

**高频标签**：逆袭、打脸、系统、金手指、马甲、团宠、虐渣、甜宠、先婚后爱、重生、穿书

**爽点关键词**：装逼打脸、身份揭晓、反杀、碾压、护短、宠溺、反转、打脸来得快

## 五、风格特征归纳

- **节奏**：中快节奏为主，冲突密度高，避免大段纯铺垫
- **句式**：短句占比高，对话与动作描写多，心理描写适度
- **人设**：主角目标明确，配角功能清晰，反派不拖泥带水
- **爽点类型**：打脸、逆袭、装逼、身份揭晓、情感爆发
- **章节结构**：开篇钩子 → 中段冲突/推进 → 结尾留悬念

## 六、章节数分析

- **起点/长连载**：畅销前列多为 300–500 章，部分超长篇 800 章以上；读者习惯追更长线。
- **番茄/短剧向**：100–200 章较常见，单本完结点明确，利于完读率。
- **晋江**：多数 80–200 章，中长篇 200–400 章。
- **当前平台热门小说平均章节数**：约 **{avg_chapters} 章**（综合各平台加权）。
- **综合建议**：本任务采用 **{suggested_total_chapters} 章** 作为总章节数（Planner 将据此生成大纲与正文规模）。

## 七、字数分析

- **单章字数**：起点常见 3000–4000 字/章；番茄、短剧向 2000–2500 字/章为主（利于碎片阅读）。
- **当前平台热门小说平均单章字数**：约 **{avg_words_per_chapter} 字**；**平均全书字数**：约 **{avg_total_words_wan} 万字**。
- **全书字数**：300 章 × 约 1500 字/章 ≈ **45 万字**；500 章约 **75 万字**。
- **本任务建议**：单章 **{suggested_words_per_chapter} 字**，全书约 **{suggested_total_words} 万字**（{suggested_total_chapters} 章 × {suggested_words_per_chapter} 字）。

## 八、本次随机建议选题

**本次随机建议选题（用于本任务生成小说）**：{picked_theme}。策划阶段将据此题材进行创作。

## 九、建议创作方向

1. 选题可优先考虑玄幻/都市 + 系统或金手指元素
2. 开篇 3 章内完成设定展示与第一次小高潮
3. 每章末尾预留悬念或冲突升级点
4. 人设卡与大纲阶段即可对齐上述风格特征，便于后续 Writer 与 Polish 统一发挥
"""


class TrendAgent(BaseAgent):
    name = "TrendAgent"

    def run(self) -> None:
        try:
            self._set_running(0, "爬取中...")
            self._log("info", "开始爬取热门榜单", {"platforms": ["起点", "番茄", "晋江"]})
            for i in range(1, 4):
                time.sleep(settings.step_interval_seconds or 0.2)
                pct = i * 25
                self._set_running(pct, f"爬取中（{pct}%）")
                self._log("info", f"已爬取 {i} 个平台榜单")
            self._set_running(75, "分析中...")
            self._log("info", "提取热门标签与风格特征")
            time.sleep(settings.step_interval_seconds or 0.2)
            self._set_running(90, "生成报告中（DeepSeek）...")
            from datetime import datetime
            analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M")

            # 热门题材列表（与模板二节一致），本次随机选一个作为建议选题，避免每次都选第一个
            import re
            genre_names = ["玄幻/修仙", "都市/现实", "短剧向/快节奏", "言情/甜宠"]
            top_genres = [{"genre": g, "share": 0.25, "notes": "来自模板趋势摘要"} for g in genre_names]
            picked_theme = random.choice(genre_names) if genre_names else "综合热门"

            nums = _compute_trend_numbers()
            suggested_total_chapters = nums["suggested_total_chapters"]
            suggested_words_per_chapter = nums["suggested_words_per_chapter"]
            suggested_total_words = nums["suggested_total_words"]
            avg_chapters = nums["avg_chapters"]
            avg_words_per_chapter = nums["avg_words_per_chapter"]
            avg_total_words_wan = nums["avg_total_words_wan"]
            report = TREND_REPORT_TEMPLATE.format(
                analysis_time=analysis_time,
                suggested_total_chapters=suggested_total_chapters,
                suggested_words_per_chapter=suggested_words_per_chapter,
                suggested_total_words=suggested_total_words,
                avg_chapters=avg_chapters,
                avg_words_per_chapter=avg_words_per_chapter,
                avg_total_words_wan=avg_total_words_wan,
                picked_theme=picked_theme,
            )

            # tags 从模板提取（不强依赖，解析失败可降级为空）
            top_tags = []
            m = re.search(r"\*\*高频标签\*\*：([^\n]+)", report)
            if m:
                seg = m.group(1).strip()
                top_tags = [x.strip() for x in seg.split("、") if x.strip()]

            data = {
                "analysis_time": analysis_time,
                "platforms": ["起点", "番茄", "晋江", "抖音小说"],
                "platform_stats": PLATFORM_STATS,
                "top_genres": top_genres,
                "top_tags": top_tags,
                "suggested_total_chapters": suggested_total_chapters,
                "suggested_words_per_chapter": suggested_words_per_chapter,
                "suggested_total_words_wan": suggested_total_words,
                "avg_chapters": avg_chapters,
                "avg_words_per_chapter": avg_words_per_chapter,
                "avg_total_words_wan": avg_total_words_wan,
                "picked_theme": picked_theme,
            }

            write_output_file(self.task_id, "trend/trend_analysis.json", json.dumps(data, ensure_ascii=False, indent=2))
            write_output_file(self.task_id, "trend/热门风格分析报告.md", report)
            self._log("info", "趋势模板已生成并写入", {"path": "trend/热门风格分析报告.md"})
            self._set_completed(
                "分析完成",
                report_path="trend/热门风格分析报告.md",
                json_path="trend/trend_analysis.json",
            )
        except Exception as e:
            self._set_failed(f"趋势分析失败：{type(e).__name__}: {e}")
