# -*- coding: utf-8 -*-
"""
简单的审核配置 - 仅用于修复导入错误
"""

class IssueSeverity:
    """问题严重程度枚举"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"

class AuditStrategy:
    """简单的审核策略"""
    def __init__(self):
        self.max_retries = 6  # 最大重试次数
        self.batch_size = 3   # 批量大小
        self.score_thresholds = {
            "strict": 80,
            "normal": 70,
            "lenient": 60,
            "min_accept": 55
        }
    
    def should_continue(self, audit_data, retry_count, chapter_scores):
        """
        简单的判断逻辑：如果没有严重问题就继续
        这只是为了修复导入错误，实际逻辑在pipeline.py中
        """
        # 这里返回True让流程继续，实际逻辑在pipeline.py中
        return True, "简单配置：继续前进"

# 全局实例
audit_config = AuditStrategy()