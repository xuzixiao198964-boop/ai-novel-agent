# -*- coding: utf-8 -*-
"""备用趋势计算函数，当主trend模块导入失败时使用"""

def _compute_trend_numbers_fallback():
    """备用趋势计算函数"""
    return {
        "suggested_total_chapters": 200,
        "avg_chapters_per_novel": 150,
        "avg_words_per_chapter": 2500,
        "total_words": 375000
    }
