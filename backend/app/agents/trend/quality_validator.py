# -*- coding: utf-8 -*-
"""
数据质量验证器 - 验证数据质量指标
基于详细设计文档实现
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """验证状态"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class ValidationRule:
    """验证规则"""
    name: str
    description: str
    field: str
    condition: str  # 条件表达式，如 ">0", "in ['A','B','C']", "len() >= 5"
    required: bool = True
    severity: str = "error"  # error, warning, info
    weight: float = 1.0  # 规则权重


@dataclass
class ValidationResult:
    """验证结果"""
    rule_name: str
    status: ValidationStatus
    message: str
    actual_value: Any
    expected_condition: str
    severity: str
    weight: float
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class QualityMetrics:
    """质量指标"""
    completeness: float = 0.0  # 完整率 (0-1)
    timeliness: float = 0.0    # 时效性 (0-1)
    accuracy: float = 0.0      # 准确率 (0-1)
    consistency: float = 0.0   # 一致性 (0-1)
    uniqueness: float = 0.0    # 唯一性 (0-1)
    overall_score: float = 0.0  # 综合评分
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "completeness": self.completeness,
            "timeliness": self.timeliness,
            "accuracy": self.accuracy,
            "consistency": self.consistency,
            "uniqueness": self.uniqueness,
            "overall_score": self.overall_score
        }


class QualityValidator:
    """数据质量验证器"""
    
    def __init__(self, config_path: str = "config/quality_rules.yaml"):
        self.config_path = config_path
        self.rules = self._load_rules()
        self.validation_history = []
        
        # 质量阈值
        self.thresholds = {
            "completeness": 0.95,  # ≥95%
            "timeliness": 0.8,     # 24小时内
            "accuracy": 0.9,       # ≥90%
            "consistency": 0.85,   # ≥85%
            "uniqueness": 0.99,    # ≥99%
            "overall": 0.7         # 综合≥70%
        }
        
        logger.info(f"质量验证器初始化完成，共 {len(self.rules)} 条规则")
    
    def _load_rules(self) -> List[ValidationRule]:
        """加载验证规则"""
        default_rules = self._get_default_rules()
        
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                return default_rules
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            rules = []
            for rule_data in config_data.get("validation_rules", []):
                rule = ValidationRule(**rule_data)
                rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"加载验证规则失败: {e}")
            return default_rules
    
    def _get_default_rules(self) -> List[ValidationRule]:
        """获取默认验证规则"""
        return [
            ValidationRule(
                name="heat_index_range",
                description="热度指数必须在0-100范围内",
                field="heat_index",
                condition="0 <= value <= 100",
                required=True,
                severity="error",
                weight=0.15
            ),
            ValidationRule(
                name="timestamp_format",
                description="时间戳必须符合ISO 8601格式",
                field="timestamp",
                condition="is_iso_format(value)",
                required=True,
                severity="error",
                weight=0.10
            ),
            ValidationRule(
                name="reader_demographics_completeness",
                description="读者画像数据必须完整",
                field="reader_demographics",
                condition="len(value) >= 4",  # 至少4个年龄段
                required=True,
                severity="warning",
                weight=0.10
            ),
            ValidationRule(
                name="genre_distribution_sum",
                description="题材分布总和应在0.9-1.1范围内",
                field="genre_distribution",
                condition="0.9 <= sum(value.values()) <= 1.1",
                required=True,
                severity="error",
                weight=0.15
            ),
            ValidationRule(
                name="platform_presence",
                description="平台信息必须存在",
                field="platform",
                condition="value is not None and len(value) > 0",
                required=True,
                severity="error",
                weight=0.10
            ),
            ValidationRule(
                name="data_timeliness",
                description="数据应在24小时内",
                field="timestamp",
                condition="age_hours(value) <= 24",
                required=True,
                severity="warning",
                weight=0.10
            ),
            ValidationRule(
                name="genre_names_valid",
                description="题材名称必须在标准分类中",
                field="genre_distribution",
                condition="all_genres_valid(value)",
                required=False,
                severity="info",
                weight=0.05
            ),
            ValidationRule(
                name="demographics_sum",
                description="读者画像比例总和应在95-105%范围内",
                field="reader_demographics",
                condition="95 <= sum(value.values()) <= 105",
                required=True,
                severity="warning",
                weight=0.10
            ),
            ValidationRule(
                name="data_uniqueness",
                description="数据应具有唯一性（非重复）",
                field="__all__",
                condition="is_unique(data)",
                required=False,
                severity="info",
                weight=0.05
            ),
            ValidationRule(
                name="data_consistency",
                description="数据内部一致性检查",
                field="__all__",
                condition="is_consistent(data)",
                required=False,
                severity="info",
                weight=0.10
            )
        ]
    
    def validate(self, data: Dict[str, Any], source_name: str = "unknown") -> QualityMetrics:
        """
        验证数据质量
        
        Args:
            data: 要验证的数据
            source_name: 数据源名称
            
        Returns:
            质量指标
        """
        logger.info(f"开始验证数据质量，数据源: {source_name}")
        
        # 执行所有规则验证
        validation_results = self._execute_validation(data)
        
        # 计算质量指标
        metrics = self._calculate_metrics(validation_results, data)
        
        # 记录验证历史
        self._record_validation(source_name, validation_results, metrics)
        
        # 生成质量报告
        self._generate_quality_report(source_name, validation_results, metrics)
        
        logger.info(f"数据质量验证完成，综合评分: {metrics.overall_score:.2f}")
        return metrics
    
    def _execute_validation(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """执行所有规则验证"""
        results = []
        
        for rule in self.rules:
            try:
                result = self._validate_rule(rule, data)
                results.append(result)
            except Exception as e:
                logger.error(f"规则验证失败 {rule.name}: {e}")
                # 创建失败结果
                result = ValidationResult(
                    rule_name=rule.name,
                    status=ValidationStatus.FAIL,
                    message=f"验证异常: {str(e)}",
                    actual_value=None,
                    expected_condition=rule.condition,
                    severity=rule.severity,
                    weight=rule.weight
                )
                results.append(result)
        
        return results
    
    def _validate_rule(self, rule: ValidationRule, data: Dict[str, Any]) -> ValidationResult:
        """验证单个规则"""
        # 获取字段值
        if rule.field == "__all__":
            value = data
        else:
            value = data.get(rule.field)
        
        # 检查必填字段
        if rule.required and value is None:
            return ValidationResult(
                rule_name=rule.name,
                status=ValidationStatus.FAIL,
                message=f"必填字段 '{rule.field}' 缺失",
                actual_value=None,
                expected_condition="not None",
                severity=rule.severity,
                weight=rule.weight
            )
        
        # 执行条件验证
        is_valid, message = self._evaluate_condition(rule.condition, value, data)
        
        # 确定状态
        if is_valid:
            status = ValidationStatus.PASS
            status_message = f"规则 '{rule.name}' 验证通过"
        else:
            if rule.severity == "error":
                status = ValidationStatus.FAIL
            else:
                status = ValidationStatus.WARNING
            status_message = f"规则 '{rule.name}' 验证失败: {message}"
        
        return ValidationResult(
            rule_name=rule.name,
            status=status,
            message=status_message,
            actual_value=value,
            expected_condition=rule.condition,
            severity=rule.severity,
            weight=rule.weight
        )
    
    def _evaluate_condition(self, condition: str, value: Any, data: Dict[str, Any]) -> Tuple[bool, str]:
        """评估条件表达式"""
        try:
            # 定义辅助函数
            def is_iso_format(timestamp_str):
                """检查是否为ISO 8601格式"""
                try:
                    datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    return True
                except:
                    return False
            
            def age_hours(timestamp_str):
                """计算数据年龄（小时）"""
                try:
                    data_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    return (datetime.now() - data_time).total_seconds() / 3600
                except:
                    return 999  # 返回大值表示无效
            
            def all_genres_valid(genre_distribution):
                """检查所有题材名称是否有效"""
                standard_genres = [
                    "都市现实", "玄幻奇幻", "科幻未来", "历史军事",
                    "游戏竞技", "悬疑灵异", "二次元", "其他"
                ]
                if not isinstance(genre_distribution, dict):
                    return False
                for genre in genre_distribution.keys():
                    if genre not in standard_genres:
                        # 检查是否为标准题材的子类
                        is_subgenre = any(genre.startswith(std) for std in standard_genres)
                        if not is_subgenre:
                            return False
                return True
            
            def is_unique(data):
                """检查数据唯一性"""
                # 这里可以添加更复杂的唯一性检查逻辑
                # 目前返回True
                return True
            
            def is_consistent(data):
                """检查数据一致性"""
                # 检查热度指数与读者画像的一致性
                if "heat_index" in data and "reader_demographics" in data:
                    heat = data["heat_index"]
                    demographics = data["reader_demographics"]
                    
                    # 简单的一致性检查：热度高的题材应该有更多的年轻读者
                    if heat > 80 and demographics:
                        young_ratio = sum(
                            demographics.get(str(age), 0) 
                            for age in range(18, 36)  # 18-35岁
                        ) / sum(demographics.values()) if sum(demographics.values()) > 0 else 0
                        
                        if young_ratio < 0.3:  # 年轻读者比例应≥30%
                            return False
                
                return True
            
            # 创建局部命名空间
            namespace = {
                "value": value,
                "data": data,
                "is_iso_format": is_iso_format,
                "age_hours": age_hours,
                "all_genres_valid": all_genres_valid,
                "is_unique": is_unique,
                "is_consistent": is_consistent,
                "len": len,
                "sum": sum,
                "min": min,
                "max": max,
                "isinstance": isinstance,
                "str": str,
                "int": int,
                "float": float,
                "dict": dict,
                "list": list
            }
            
            # 安全地评估条件
            # 注意：这里使用了eval，在生产环境中需要考虑安全性
            # 可以考虑使用更安全的表达式解析库
            result = eval(condition, {"__builtins__": {}}, namespace)
            
            if isinstance(result, bool):
                return result, "条件评估完成"
            else:
                return bool(result), f"条件评估结果: {result}"
                
        except Exception as e:
            return False, f"条件评估失败: {str(e)}"
    
    def _calculate_metrics(self, results: List[ValidationResult], data: Dict[str, Any]) -> QualityMetrics:
        """计算质量指标"""
        metrics = QualityMetrics()
        
        # 计算各维度分数
        completeness_score = self._calculate_completeness_score(results, data)
        timeliness_score = self._calculate_timeliness_score(results, data)
        accuracy_score = self._calculate_accuracy_score(results, data)
        consistency_score = self._calculate_consistency_score(results, data)
        uniqueness_score = self._calculate_uniqueness_score(results, data)
        
        # 设置指标
        metrics.completeness = completeness_score
        metrics.timeliness = timeliness_score
        metrics.accuracy = accuracy_score
        metrics.consistency = consistency_score
        metrics.uniqueness = uniqueness_score
        
        # 计算综合评分
        weights = {
            "completeness": 0.3,
            "timeliness": 0.25,
            "accuracy": 0.25,
            "consistency": 0.1,
            "uniqueness": 0.1
        }
        
        overall_score = (
            completeness_score * weights["completeness"] +
            timeliness_score * weights["timeliness"] +
            accuracy_score * weights["accuracy"] +
            consistency_score * weights["consistency"] +
            uniqueness_score * weights["uniqueness"]
        )
        
        metrics.overall_score = overall_score
        
        return metrics
    
    def _calculate_completeness_score(self, results: List[ValidationResult], data: Dict[str, Any]) -> float:
        """计算完整率分数"""
        # 统计必填字段验证结果
        required_rules = [r for r in results if "required" in r.message or "缺失" in r.message]
        
        if not required_rules:
            return 1.0
        
        passed_count = sum(1 for r in required_rules if r.status == ValidationStatus.PASS)
        total_count = len(required_rules)
        
        return passed_count / total_count if total_count > 0 else 0.0
    
    def _calculate_timeliness_score(self, results: List[ValidationResult], data: Dict[str, Any]) -> float:
        """计算时效性分数"""
        # 检查时间戳
        if "timestamp" not in data:
            return 0.0
        
        try:
            timestamp_str = data["timestamp"]
            data_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            age_hours = (datetime.now() - data_time).total_seconds() / 3600
            
            # 24小时内为满分，超过则线性衰减
            if age_hours <= 24:
                return 1.0
            elif age_hours <= 72:  # 3天内
                return max(0, 1 - (age_hours - 24) / 48)
            else:
                return 0.0
                
        except:
            return 0.0
    
    def _calculate_accuracy_score(self, results: List[ValidationResult], data: Dict[str, Any]) -> float:
        """计算准确率分数"""
        # 统计准确性相关规则的验证结果
        accuracy_rules = [
            r for r in results 
            if "range" in r.rule_name or "format" in r.rule_name or "valid" in r.rule_name
        ]
        
        if not accuracy_rules:
            return 1.0
        
        # 加权平均
        total_weight = sum(r.weight for r in accuracy_rules)
        if total_weight == 0:
            return 0.0
        
        weighted_score = sum(
            (1.0 if r.status == ValidationStatus.PASS else 0.5 if r.status == ValidationStatus.WARNING else 0.0) * r.weight
            for r in accuracy_rules
        )
        
        return weighted_score / total_weight
    
    def _calculate_consistency_score(self, results: List[ValidationResult], data: Dict[str, Any]) -> float:
        """计算一致性分数"""
        # 查找一致性规则的结果
        consistency_rules = [r for r in results if "consistency" in r.rule_name]
        
        if consistency_rules:
            # 使用一致性规则的结果
            passed_count = sum(1 for r in consistency_rules if r.status == ValidationStatus.PASS)
            total_count = len(consistency_rules)
            return passed_count / total_count if total_count > 0 else 1.0
        else:
            # 如果没有专门的一致性规则，使用其他规则推断
            # 检查是否有矛盾的验证结果
            error_rules = [r for r in results if r.status == ValidationStatus.FAIL]
            warning_rules = [r for r in results if r.status == ValidationStatus.WARNING]
            
            total_rules = len(results)
            if total_rules == 0:
                return 1.0
            
            consistency_score = 1.0
            consistency_score -= len(error_rules) / total_rules * 0.5  # 每个错误扣0.5
            consistency_score -= len(warning_rules) / total_rules * 0.2  # 每个警告扣0.2
            
            return max(0.0, consistency_score)
    
    def _calculate_uniqueness_score(self, results: List[ValidationResult], data: Dict[str, Any]) -> float:
        """计算唯一性分数"""
        # 查找唯一性规则的结果
        uniqueness_rules = [r for r in results if "uniqueness" in r.rule_name]
        
        if uniqueness_rules:
            passed_count = sum(1 for r in uniqueness_rules if r.status == ValidationStatus.PASS)
            total_count = len(uniqueness_rules)
            return passed_count / total_count if total_count > 0 else 1.0
        else:
            # 如果没有专门的唯一性规则，假设数据是唯一的
            return 1.0
    
    def _record_validation(self, source_name: str, results: List[ValidationResult], metrics: QualityMetrics):
        """记录验证历史"""
        validation_record = {
            "source_name": source_name,
            "timestamp": datetime.now().isoformat(),
            "results_summary": {
                "total_rules": len(results),
                "passed": sum(1 for r in results if r.status == ValidationStatus.PASS),
                "warnings": sum(1 for r in results if r.status == ValidationStatus.WARNING),
                "failed": sum(1 for r in results if r.status == ValidationStatus.FAIL)
            },
            "metrics": metrics.to_dict(),
            "details": [
                {
                    "rule_name": r.rule_name,
                    "status": r.status.value,
                    "message": r.message,
                    "severity": r.severity
                }
                for r in results
            ]
        }
        
        self.validation_history.append(validation_record)
        
        # 限制历史记录数量
        if len(self.validation_history) > 100:
            self.validation_history = self.validation_history[-100:]
    
    def _generate_quality_report(self, source_name: str, results: List[ValidationResult], metrics: QualityMetrics):
        """生成质量报告"""
        report = {
            "source_name": source_name,
            "validation_time": datetime.now().isoformat(),
            "summary": {
                "overall_score": metrics.overall_score,
                "passed_all_thresholds": all(
                    getattr(metrics, dim) >= self.thresholds[dim]
                    for dim in ["completeness", "timeliness", "accuracy", "consistency", "uniqueness"]
                ),
                "thresholds": self.thresholds
            },
            "metrics": metrics.to_dict(),
            "threshold_comparison": {
                dim: {
                    "score": getattr(metrics, dim),
                    "threshold": self.thresholds[dim],
                    "passed": getattr(metrics, dim) >= self.thresholds[dim]
                }
                for dim in ["completeness", "timeliness", "accuracy", "consistency", "uniqueness", "overall"]
            },
            "rule_results": [
                {
                    "rule_name": r.rule_name,
                    "status": r.status.value,
                    "message": r.message,
                    "severity": r.severity,
                    "weight": r.weight
                }
                for r in results
            ],
            "recommendations": self._generate_recommendations(metrics, results)
        }
        
        # 保存报告
        report_dir = Path("data/reports/quality")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"quality_report_{source_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"质量报告已保存: {report_file}")
        return report
    
    def _generate_recommendations(self, metrics: QualityMetrics, results: List[ValidationResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于质量指标的建议
        if metrics.completeness < self.thresholds["completeness"]:
            recommendations.append("增加数据采集字段以提高完整性")
        
        if metrics.timeliness < self.thresholds["timeliness"]:
            recommendations.append("优化数据更新频率以提高时效性")
        
        if metrics.accuracy < self.thresholds["accuracy"]:
            recommendations.append("加强数据验证和清洗以提高准确性")
        
        if metrics.consistency < self.thresholds["consistency"]:
            recommendations.append("检查数据内部一致性，修复矛盾数据")
        
        if metrics.uniqueness < self.thresholds["uniqueness"]:
            recommendations.append("实施数据去重策略以提高唯一性")
        
        # 基于规则失败的建议
        failed_rules = [r for r in results if r.status == ValidationStatus.FAIL]
        for rule in failed_rules:
            if "heat_index" in rule.rule_name:
                recommendations.append("检查热度指数数据，确保在0-100范围内")
            elif "timestamp" in rule.rule_name:
                recommendations.append("确保时间戳符合ISO 8601格式")
            elif "genre" in rule.rule_name:
                recommendations.append("验证题材名称是否符合标准分类")
            elif "demographics" in rule.rule_name:
                recommendations.append("检查读者画像数据的完整性和合理性")
        
        return recommendations
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """获取验证摘要"""
        if not self.validation_history:
            return {"message": "暂无验证历史"}
        
        latest = self.validation_history[-1]
        total_validations = len(self.validation_history)
        
        # 计算历史平均分
        avg_scores = {
            "completeness": sum(h["metrics"]["completeness"] for h in self.validation_history) / total_validations,
            "timeliness": sum(h["metrics"]["timeliness"] for h in self.validation_history) / total_validations,
            "accuracy": sum(h["metrics"]["accuracy"] for h in self.validation_history) / total_validations,
            "consistency": sum(h["metrics"]["consistency"] for h in self.validation_history) / total_validations,
            "uniqueness": sum(h["metrics"]["uniqueness"] for h in self.validation_history) / total_validations,
            "overall_score": sum(h["metrics"]["overall_score"] for h in self.validation_history) / total_validations
        }
        
        return {
            "total_validations": total_validations,
            "latest_validation": {
                "source": latest["source_name"],
                "timestamp": latest["timestamp"],
                "overall_score": latest["metrics"]["overall_score"]
            },
            "average_scores": avg_scores,
            "threshold_compliance": {
                dim: avg_scores[dim] >= self.thresholds[dim]
                for dim in ["completeness", "timeliness", "accuracy", "consistency", "uniqueness"]
            }
        }
    
    def clear_history(self):
        """清空验证历史"""
        self.validation_history = []
        logger.info("验证历史已清空")


# 导入yaml（在文件末尾避免循环导入）
try:
    import yaml
except ImportError:
    yaml = None
    logger.warning("yaml库未安装，将使用默认规则")