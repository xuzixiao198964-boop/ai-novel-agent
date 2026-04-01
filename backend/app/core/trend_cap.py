# -*- coding: utf-8 -*-
"""从热门趋势分析 JSON 读取建议总章数，供测试模式递增上限与正式模式规模参考。"""
import json
from pathlib import Path

from app.core.config import settings
from app.core.state import _task_dir


def get_trend_suggested_chapter_cap(task_id: str | None = None) -> int:
    """
    优先读任务 output/trend/trend_analysis.json，其次系统 data/trend/trend_analysis.json，
    否则用 TrendAgent 内置默认统计。
    """
    paths: list[Path] = []
    if task_id:
        paths.append(_task_dir(task_id) / "output" / "trend" / "trend_analysis.json")
    paths.append(settings.data_dir / "trend" / "trend_analysis.json")

    n = 0
    for p in paths:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            n = int(data.get("suggested_total_chapters") or 0)
            if n > 0:
                break
        except Exception:
            continue

    if n <= 0:
        try:
            from app.agents.trend_agent import _compute_trend_numbers
            n = int(_compute_trend_numbers().get("suggested_total_chapters") or 200)
        except ImportError:
            try:
                from app.core.trend_fallback import _compute_trend_numbers_fallback
                n = int(_compute_trend_numbers_fallback().get("suggested_total_chapters") or 200)
            except ImportError:
                n = 200

    return max(30, n)
