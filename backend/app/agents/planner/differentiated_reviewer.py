# -*- coding: utf-8 -*-
"""
差异化审核器 - 根据题材类型应用不同的审核标准
基于详细设计文档实现
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class GenreType(Enum):
    """题材类型"""
    HIGH_QUALITY = "high_quality_genre"      # 高质量成熟题材
    EXPERIMENTAL = "experimental_genre"      # 实验性创新题材
    COMMERCIAL = "commercial_genre"         # 商业化量产题材
    LITERARY = "literary_genre"             # 文学性精品题材


class ReviewDimension(Enum):
    """审核维度"""
    STRUCTURE = "structure"      # 结构
    CHARACTER = "character"      # 人物
    PLOT = "plot"                # 情节
    MARKET = "market"            # 市场匹配
    STYLE = "style"              # 风格
    INNOVATION = "innovation"    # 创新性
    LANGUAGE = "language"        # 语言
    DEPTH = "depth"              # 思想深度


@dataclass
class DimensionScore:
    """维度评分"""
    dimension: ReviewDimension
    score: float  # 0-100分
    strengths: List[str]
    issues: List[str]
    suggestions: List[str]
    weight: float = 1.0


@dataclass
class ReviewResult:
    """审核结果"""
    plan_id: str
    genre_type: GenreType
    total_score: float
    dimension_scores: Dict[ReviewDimension, DimensionScore]
    passed: bool
    requires_revision: bool
    rule_violations: List[Dict[str, Any]]
    feedback: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DifferentiatedReviewSystem:
    """差异化审核系统"""
    
    def __init__(self, config_dir: str = "config/differentiated"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载审核标准配置
        self.standards = self._load_standards()
        
        # 题材类型检测器
        self.genre_detector = GenreTypeDetector()
        
        # 审核规则引擎
        self.rule_engine = ReviewRuleEngine()
        
        logger.info("差异化审核系统初始化完成")
    
    def _load_standards(self) -> Dict[GenreType, Dict[str, Any]]:
        """加载审核标准配置"""
        standards = {}
        
        for genre_type in GenreType:
            config_file = self.config_dir / f"{genre_type.value}.json"
            
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        standards[genre_type] = json.load(f)
                except Exception as e:
                    logger.error(f"加载标准配置失败 {genre_type}: {e}")
                    standards[genre_type] = self._get_default_standard(genre_type)
            else:
                standards[genre_type] = self._get_default_standard(genre_type)
                # 保存默认配置
                self._save_standard(genre_type, standards[genre_type])
        
        return standards
    
    def _get_default_standard(self, genre_type: GenreType) -> Dict[str, Any]:
        """获取默认审核标准"""
        if genre_type == GenreType.HIGH_QUALITY:
            return {
                "description": "市场成熟，读者期待高，要求严格",
                "total_score_threshold": 85,
                "dimension_requirements": {
                    "structure": 75,
                    "character": 80,
                    "plot": 70,
                    "market": 65,
                    "style": 75
                },
                "dimension_weights": {
                    "structure": 0.25,
                    "character": 0.25,
                    "plot": 0.20,
                    "market": 0.15,
                    "style": 0.15
                },
                "special_rules": [
                    {
                        "name": "no_logic_holes",
                        "description": "不允许出现明显逻辑漏洞",
                        "severity": "critical"
                    },
                    {
                        "name": "character_consistency",
                        "description": "人物性格必须稳定一致",
                        "severity": "high"
                    },
                    {
                        "name": "mainstream_aesthetics",
                        "description": "必须符合主流审美",
                        "severity": "medium"
                    },
                    {
                        "name": "emotional_expression",
                        "description": "情感表达要细腻真实",
                        "severity": "medium"
                    }
                ]
            }
        
        elif genre_type == GenreType.EXPERIMENTAL:
            return {
                "description": "创新尝试，允许一定风险",
                "total_score_threshold": 70,
                "dimension_requirements": {
                    "structure": 65,
                    "character": 70,
                    "plot": 60,
                    "market": 55,
                    "innovation": 65
                },
                "dimension_weights": {
                    "structure": 0.20,
                    "character": 0.20,
                    "plot": 0.15,
                    "market": 0.15,
                    "innovation": 0.30  # 创新性权重高
                },
                "special_rules": [
                    {
                        "name": "allow_innovation",
                        "description": "允许适度创新和冒险",
                        "severity": "low"
                    },
                    {
                        "name": "non_traditional_structure",
                        "description": "可以尝试非传统结构",
                        "severity": "low"
                    },
                    {
                        "name": "accept_reader_risk",
                        "description": "接受一定程度的读者接受度风险",
                        "severity": "medium"
                    },
                    {
                        "name": "encourage_novel_settings",
                        "description": "鼓励新颖的设定和世界观",
                        "severity": "low"
                    }
                ]
            }
        
        elif genre_type == GenreType.COMMERCIAL:
            return {
                "description": "追求产量和效率，质量要求适中",
                "total_score_threshold": 75,
                "dimension_requirements": {
                    "structure": 70,
                    "character": 65,
                    "plot": 70,
                    "market": 75,
                    "style": 60
                },
                "dimension_weights": {
                    "structure": 0.20,
                    "character": 0.15,
                    "plot": 0.25,  # 情节权重高
                    "market": 0.30,  # 市场匹配权重高
                    "style": 0.10
                },
                "special_rules": [
                    {
                        "name": "plot_attractiveness",
                        "description": "强调情节吸引力和更新速度",
                        "severity": "high"
                    },
                    {
                        "name": "allow_formulaic",
                        "description": "允许一定程度的套路化",
                        "severity": "low"
                    },
                    {
                        "name": "reader_retention",
                        "description": "优先考虑读者留存率",
                        "severity": "high"
                    },
                    {
                        "name": "fast_pacing",
                        "description": "节奏要快，爽点要密集",
                        "severity": "medium"
                    }
                ]
            }
        
        elif genre_type == GenreType.LITERARY:
            return {
                "description": "追求文学价值，艺术性要求高",
                "total_score_threshold": 80,
                "dimension_requirements": {
                    "structure": 80,
                    "character": 85,
                    "plot": 75,
                    "language": 85,
                    "depth": 70
                },
                "dimension_weights": {
                    "structure": 0.20,
                    "character": 0.25,
                    "plot": 0.15,
                    "language": 0.25,  # 语言权重高
                    "depth": 0.15  # 思想深度权重
                },
                "special_rules": [
                    {
                        "name": "literary_value",
                        "description": "强调文学性和思想深度",
                        "severity": "high"
                    },
                    {
                        "name": "allow_slow_pacing",
                        "description": "允许较慢的叙事节奏",
                        "severity": "low"
                    },
                    {
                        "name": "language_art",
                        "description": "重视语言艺术和修辞",
                        "severity": "high"
                    },
                    {
                        "name": "character_depth",
                        "description": "人物塑造要有层次感",
                        "severity": "high"
                    }
                ]
            }
        
        else:
            # 默认标准
            return {
                "description": "通用标准",
                "total_score_threshold": 75,
                "dimension_requirements": {
                    "structure": 70,
                    "character": 70,
                    "plot": 70,
                    "market": 70,
                    "style": 70
                },
                "dimension_weights": {
                    "structure": 0.20,
                    "character": 0.20,
                    "plot": 0.20,
                    "market": 0.20,
                    "style": 0.20
                },
                "special_rules": []
            }
    
    def _save_standard(self, genre_type: GenreType, standard: Dict[str, Any]):
        """保存审核标准"""
        config_file = self.config_dir / f"{genre_type.value}.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(standard, f, ensure_ascii=False, indent=2)
            logger.info(f"审核标准已保存: {config_file}")
        except Exception as e:
            logger.error(f"保存审核标准失败: {e}")
    
    def review_story_plan(self, plan_data: Dict[str, Any], genre_info: Dict[str, Any]) -> ReviewResult:
        """
        审核故事策划
        
        Args:
            plan_data: 故事策划数据
            genre_info: 题材信息
            
        Returns:
            审核结果
        """
        logger.info(f"开始审核故事策划，题材: {genre_info.get('name', '未知')}")
        
        # 确定题材类型
        genre_type = self.genre_detector.detect(genre_info)
        logger.info(f"检测到题材类型: {genre_type.value}")
        
        # 获取对应的审核标准
        standard = self.standards[genre_type]
        
        # 计算各维度分数
        dimension_scores = self._calculate_dimension_scores(plan_data, standard)
        
        # 计算总分（加权平均）
        total_score = self._calculate_total_score(dimension_scores, standard)
        
        # 检查特殊规则
        rule_violations = self._check_special_rules(plan_data, standard)
        
        # 确定是否通过
        passed, requires_revision = self._determine_result(
            total_score, dimension_scores, rule_violations, standard
        )
        
        # 生成反馈
        feedback = self._generate_feedback(
            plan_data, dimension_scores, total_score, rule_violations, standard
        )
        
        # 创建审核结果
        result = ReviewResult(
            plan_id=plan_data.get("id", "unknown"),
            genre_type=genre_type,
            total_score=total_score,
            dimension_scores=dimension_scores,
            passed=passed,
            requires_revision=requires_revision,
            rule_violations=rule_violations,
            feedback=feedback
        )
        
        # 保存审核记录
        self._save_review_record(result)
        
        logger.info(f"审核完成，总分: {total_score:.1f}, 通过: {passed}")
        return result
    
    def _calculate_dimension_scores(self, plan_data: Dict[str, Any], 
                                  standard: Dict[str, Any]) -> Dict[ReviewDimension, DimensionScore]:
        """计算各维度分数"""
        dimension_scores = {}
        
        # 获取需要评估的维度
        dimensions_to_evaluate = list(standard["dimension_requirements"].keys())
        
        for dim_name in dimensions_to_evaluate:
            try:
                dimension = ReviewDimension(dim_name)
                
                # 调用对应的评估函数
                score_data = self._evaluate_dimension(dimension, plan_data)
                
                # 创建维度评分对象
                dim_score = DimensionScore(
                    dimension=dimension,
                    score=score_data["score"],
                    strengths=score_data.get("strengths", []),
                    issues=score_data.get("issues", []),
                    suggestions=score_data.get("suggestions", []),
                    weight=standard["dimension_weights"].get(dim_name, 1.0)
                )
                
                dimension_scores[dimension] = dim_score
                
            except Exception as e:
                logger.error(f"评估维度 {dim_name} 失败: {e}")
                # 创建默认评分
                dimension = ReviewDimension(dim_name) if hasattr(ReviewDimension, dim_name) else ReviewDimension.STRUCTURE
                dimension_scores[dimension] = DimensionScore(
                    dimension=dimension,
                    score=50.0,  # 中等分数
                    strengths=[],
                    issues=[f"评估失败: {str(e)}"],
                    suggestions=["请检查数据完整性"],
                    weight=standard["dimension_weights"].get(dim_name, 1.0)
                )
        
        return dimension_scores
    
    def _evaluate_dimension(self, dimension: ReviewDimension, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个维度"""
        # 这里应该调用具体的评估逻辑
        # 目前使用模拟评估
        
        if dimension == ReviewDimension.STRUCTURE:
            return self._evaluate_structure(plan_data)
        elif dimension == ReviewDimension.CHARACTER:
            return self._evaluate_character(plan_data)
        elif dimension == ReviewDimension.PLOT:
            return self._evaluate_plot(plan_data)
        elif dimension == ReviewDimension.MARKET:
            return self._evaluate_market(plan_data)
        elif dimension == ReviewDimension.STYLE:
            return self._evaluate_style(plan_data)
        elif dimension == ReviewDimension.INNOVATION:
            return self._evaluate_innovation(plan_data)
        elif dimension == ReviewDimension.LANGUAGE:
            return self._evaluate_language(plan_data)
        elif dimension == ReviewDimension.DEPTH:
            return self._evaluate_depth(plan_data)
        else:
            return {
                "score": 70.0,
                "strengths": ["维度评估正常"],
                "issues": [],
                "suggestions": []
            }
    
    def _evaluate_structure(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估结构维度"""
        structure = plan_data.get("structure", {})
        
        score = 75.0  # 基础分数
        
        strengths = []
        issues = []
        suggestions = []
        
        # 检查三幕式结构
        if all(act in structure for act in ["act1", "act2", "act3"]):
            strengths.append("三幕式结构完整")
            score += 10
        else:
            issues.append("三幕式结构不完整")
            suggestions.append("完善开端、发展、高潮三部分结构")
            score -= 15
        
        # 检查情节推进
        if structure.get("plot_progression", ""):
            strengths.append("情节推进逻辑清晰")
            score += 5
        else:
            issues.append("情节推进逻辑不明确")
            suggestions.append("明确情节发展脉络")
            score -= 10
        
        # 检查悬念设置
        if structure.get("suspense_count", 0) >= 3:
            strengths.append("悬念设置充足")
            score += 5
        else:
            issues.append("悬念设置不足")
            suggestions.append("增加悬念和转折点")
            score -= 5
        
        # 确保分数在合理范围内
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "strengths": strengths,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _evaluate_character(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估人物维度"""
        characters = plan_data.get("characters", [])
        
        score = 70.0  # 基础分数
        
        strengths = []
        issues = []
        suggestions = []
        
        # 检查主要人物
        main_characters = [c for c in characters if c.get("is_main", False)]
        if len(main_characters) >= 1:
            strengths.append("主要人物设定明确")
            score += 10
        else:
            issues.append("缺乏明确的主要人物")
            suggestions.append("设定清晰的主角")
            score -= 20
        
        # 检查人物性格
        consistent_chars = sum(1 for c in characters if c.get("personality", ""))
        if consistent_chars >= len(characters) * 0.8:  # 80%的人物有性格设定
            strengths.append("人物性格设定完整")
            score += 8
        else:
            issues.append("部分人物性格设定缺失")
            suggestions.append("完善所有主要人物的性格设定")
            score -= 10
        
        # 检查成长弧线
        growing_chars = sum(1 for c in characters if c.get("growth_arc", ""))
        if growing_chars >= len(main_characters) * 0.5:  # 50%的主要人物有成长弧线
            strengths.append("人物成长弧线清晰")
            score += 7
        else:
            issues.append("人物成长弧线不足")
            suggestions.append("为主角设计明确的成长路径")
            score -= 8
        
        # 确保分数在合理范围内
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "strengths": strengths,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _evaluate_plot(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估情节维度"""
        plot = plan_data.get("plot", {})
        
        score = 70.0  # 基础分数
        
        strengths = []
        issues = []
        suggestions = []
        
        # 检查核心冲突
        if plot.get("main_conflict", ""):
            strengths.append("核心冲突明确")
            score += 10
        else:
            issues.append("缺乏明确的核心冲突")
            suggestions.append("设定清晰的故事核心矛盾")
            score -= 15
        
        # 检查关键事件
        key_events = plot.get("key_events", [])
        if len(key_events) >= 5:
            strengths.append("关键事件设置充足")
            score += 8
        elif len(key_events) >= 3:
            strengths.append("关键事件设置基本充足")
            score += 5
        else:
            issues.append("关键事件设置不足")
            suggestions.append("增加关键情节转折点")
            score -= 10
        
        # 检查情感曲线
        if plot.get("emotional_curve", ""):
            strengths.append("情感曲线设计合理")
            score += 7
        else:
            issues.append("情感曲线设计不足")
            suggestions.append("设计完整的情感起伏曲线")
            score -= 8
        
        # 确保分数在合理范围内
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "strengths": strengths,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _evaluate_market(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估市场匹配维度"""
        market_info = plan_data.get("market_analysis", {})
        
        score = 65.0  # 基础分数
        
        strengths = []
        issues = []
        suggestions = []
        
        # 检查目标读者
        if market_info.get("target_readers", ""):
            strengths.append("目标读者明确")
            score += 10
        else:
            issues.append("目标读者不明确")
            suggestions.append("明确目标读者群体")
            score -= 12
        
        # 检查竞争分析
        if market_info.get("competition_analysis", ""):
            strengths.append("竞争分析完整")
            score += 8
        else:
            issues.append("缺乏竞争分析")
            suggestions.append("分析同类作品的市场表现")
            score -= 10
        
        # 检查创新点
        if market_info.get("unique_selling_points", []):
            strengths.append("独特卖点明确")
            score += 7
        else:
            issues.append("缺乏独特卖点")
            suggestions.append("明确作品的差异化优势")
            score -= 8
        
        # 确保分数在合理范围内
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "strengths": strengths,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _evaluate_style(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估风格维度"""
        style_info = plan_data.get("style_parameters", {})
        
        score = 70.0  # 基础分数
        
        strengths = []
        issues = []
        suggestions = []
        
        # 检查语言风格
        if style_info.get("language_style", ""):
            strengths.append("语言风格明确")
            score += 10
        else:
            issues.append("语言风格不明确")
            suggestions.append("明确作品的语言风格")
            score -= 10
        
        # 检查叙事节奏
        if style_info.get("narrative_pace", ""):
            strengths.append("叙事节奏设定合理")
            score += 8
        else:
            issues.append("叙事节奏不明确")
            suggestions.append("设定合适的叙事节奏")
            score -= 8
        
        # 检查情感基调
        if style_info.get("emotional_tone", ""):
            strengths.append("情感基调明确")
            score += 7
        else:
            issues.append("情感基调不明确")
            suggestions.append("明确作品的情感基调")
            score -= 7
        
        # 确保分数在合理范围内
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "strengths": strengths,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _evaluate_innovation(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估创新性维度"""
        innovation_info = plan_data.get("innovation_elements", {})
        
        score = 60.0  # 基础分数
        
        strengths = []
        issues = []
        suggestions = []
        
        # 检查世界观创新
        if innovation_info.get("worldview_innovation", ""):
            strengths.append("世界观有创新")
            score += 15
        else:
            issues.append("世界观创新不足")
            suggestions.append("尝试独特的世界观设定")
            score -= 5
        
        # 检查情节创新
        if innovation_info.get("plot_innovation", ""):
            strengths.append("情节设计有创新")
            score += 12
        else:
            issues.append("情节设计创新不足")
            suggestions.append("尝试非传统的情节结构")
            score -= 5
        
        # 检查人物创新
        if innovation_info.get("character_innovation", ""):
            strengths.append("人物设定有创新")
            score += 10
        else:
            issues.append("人物设定创新不足")
            suggestions.append("设计独特的人物形象")
            score -= 5
        
        # 确保分数在合理范围内
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "strengths": strengths,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _evaluate_language(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估语言维度"""
        language_info = plan_data.get("language_quality", {})
        
        score = 75.0  # 基础分数
        
        strengths = []
        issues = []
        suggestions = []
        
        # 检查语言流畅度
        if language_info.get("fluency_score", 0) >= 7:
            strengths.append("语言流畅度良好")
            score += 10
        else:
            issues.append("语言流畅度有待提高")
            suggestions.append("优化语言表达，提高流畅度")
            score -= 10
        
        # 检查修辞运用
        if language_info.get("rhetoric_count", 0) >= 3:
            strengths.append("修辞运用丰富")
            score += 8
        else:
            issues.append("修辞运用不足")
            suggestions.append("适当运用修辞手法")
            score -= 8
        
        # 检查语言风格一致性
        if language_info.get("style_consistency", True):
            strengths.append("语言风格一致")
            score += 7
        else:
            issues.append("语言风格不一致")
            suggestions.append("保持语言风格的一致性")
            score -= 7
        
        # 确保分数在合理范围内
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "strengths": strengths,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _evaluate_depth(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估思想深度维度"""
        depth_info = plan_data.get("thematic_depth", {})
        
        score = 65.0  # 基础分数
        
        strengths = []
        issues = []
        suggestions = []
        
        # 检查主题深度
        if depth_info.get("theme_depth_score", 0) >= 7:
            strengths.append("主题有深度")
            score += 15
        else:
            issues.append("主题深度不足")
            suggestions.append("深化作品主题思想")
            score -= 10
        
        # 检查价值观表达
        if depth_info.get("values_expression", ""):
            strengths.append("价值观表达清晰")
            score += 10
        else:
            issues.append("价值观表达不明确")
            suggestions.append("明确作品要表达的价值观")
            score -= 8
        
        # 检查社会意义
        if depth_info.get("social_significance", ""):
            strengths.append("具有一定社会意义")
            score += 8
        else:
            issues.append("社会意义不足")
            suggestions.append("思考作品的社会价值")
            score -= 7
        
        # 确保分数在合理范围内
        score = max(0, min(100, score))
        
        return {
            "score": score,
            "strengths": strengths,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _calculate_total_score(self, dimension_scores: Dict[ReviewDimension, DimensionScore],
                             standard: Dict[str, Any]) -> float:
        """计算总分（加权平均）"""
        if not dimension_scores:
            return 0.0
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for dimension, score_data in dimension_scores.items():
            weight = score_data.weight
            total_weighted_score += score_data.score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return total_weighted_score / total_weight
    
    def _check_special_rules(self, plan_data: Dict[str, Any], 
                           standard: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查特殊规则"""
        violations = []
        
        for rule in standard.get("special_rules", []):
            rule_name = rule.get("name", "")
            severity = rule.get("severity", "medium")
            
            # 这里应该调用具体的规则检查逻辑
            # 目前使用模拟检查
            is_violated, violation_details = self._check_single_rule(rule_name, plan_data)
            
            if is_violated:
                violations.append({
                    "rule_name": rule_name,
                    "description": rule.get("description", ""),
                    "severity": severity,
                    "details": violation_details
                })
        
        return violations
    
    def _check_single_rule(self, rule_name: str, plan_data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查单个规则"""
        # 这里应该实现具体的规则检查逻辑
        # 目前使用模拟检查
        
        if "no_logic_holes" in rule_name:
            # 检查逻辑漏洞
            plot = plan_data.get("plot", {})
            if plot.get("logic_issues", []):
                return True, "发现逻辑漏洞"
            else:
                return False, ""
        
        elif "character_consistency" in rule_name:
            # 检查人物一致性
            characters = plan_data.get("characters", [])
            inconsistent_chars = sum(1 for c in characters if c.get("inconsistent", False))
            if inconsistent_chars > 0:
                return True, f"{inconsistent_chars}个人物存在不一致"
            else:
                return False, ""
        
        elif "plot_attractiveness" in rule_name:
            # 检查情节吸引力
            plot = plan_data.get("plot", {})
            if plot.get("attractiveness_score", 0) < 6:
                return True, "情节吸引力不足"
            else:
                return False, ""
        
        elif "literary_value" in rule_name:
            # 检查文学价值
            depth_info = plan_data.get("thematic_depth", {})
            if depth_info.get("literary_value_score", 0) < 7:
                return True, "文学价值有待提高"
            else:
                return False, ""
        
        # 默认通过
        return False, ""
    
    def _determine_result(self, total_score: float, 
                         dimension_scores: Dict[ReviewDimension, DimensionScore],
                         rule_violations: List[Dict[str, Any]],
                         standard: Dict[str, Any]) -> Tuple[bool, bool]:
        """确定审核结果"""
        # 检查总分是否达标
        threshold = standard.get("total_score_threshold", 75)
        score_passed = total_score >= threshold
        
        # 检查各维度是否达标
        dimension_requirements = standard.get("dimension_requirements", {})
        dimension_passed = True
        
        for dim_name, min_score in dimension_requirements.items():
            try:
                dimension = ReviewDimension(dim_name)
                if dimension in dimension_scores:
                    if dimension_scores[dimension].score < min_score:
                        dimension_passed = False
                        break
            except:
                continue
        
        # 检查是否有严重规则违规
        critical_violations = [v for v in rule_violations if v.get("severity") == "critical"]
        has_critical_violations = len(critical_violations) > 0
        
        # 确定是否通过
        passed = score_passed and dimension_passed and not has_critical_violations
        
        # 确定是否需要修订
        requires_revision = not passed or len(rule_violations) > 0
        
        return passed, requires_revision
    
    def _generate_feedback(self, plan_data: Dict[str, Any],
                          dimension_scores: Dict[ReviewDimension, DimensionScore],
                          total_score: float,
                          rule_violations: List[Dict[str, Any]],
                          standard: Dict[str, Any]) -> Dict[str, Any]:
        """生成反馈"""
        feedback = {
            "summary": f"审核总分: {total_score:.1f}/{standard.get('total_score_threshold', 75)}",
            "strengths": [],
            "weaknesses": [],
            "rule_violations": rule_violations,
            "suggestions": [],
            "dimension_details": {}
        }
        
        # 收集强项和弱项
        for dimension, score_data in dimension_scores.items():
            dim_feedback = {
                "score": score_data.score,
                "strengths": score_data.strengths,
                "issues": score_data.issues,
                "suggestions": score_data.suggestions,
                "requirement": standard["dimension_requirements"].get(dimension.value, 70)
            }
            
            feedback["dimension_details"][dimension.value] = dim_feedback
            
            # 添加到强项或弱项
            if score_data.score >= 80:
                feedback["strengths"].append({
                    "dimension": dimension.value,
                    "score": score_data.score,
                    "description": f"{dimension.value}表现优秀"
                })
            elif score_data.score < 60:
                feedback["weaknesses"].append({
                    "dimension": dimension.value,
                    "score": score_data.score,
                    "description": f"{dimension.value}需要改进",
                    "suggestions": score_data.suggestions[:2]  # 取前2条建议
                })
        
        # 生成总体建议
        if total_score < standard.get("total_score_threshold", 75):
            feedback["suggestions"].append(f"总分未达到要求，需要提高{standard.get('total_score_threshold', 75) - total_score:.1f}分")
        
        if rule_violations:
            critical_count = sum(1 for v in rule_violations if v.get("severity") == "critical")
            if critical_count > 0:
                feedback["suggestions"].append(f"有{critical_count}条严重规则违规需要修复")
        
        return feedback
    
    def _save_review_record(self, result: ReviewResult):
        """保存审核记录"""
        records_dir = Path("data/reviews/differentiated")
        records_dir.mkdir(parents=True, exist_ok=True)
        
        record_file = records_dir / f"review_{result.plan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        record_data = {
            "plan_id": result.plan_id,
            "genre_type": result.genre_type.value,
            "total_score": result.total_score,
            "passed": result.passed,
            "requires_revision": result.requires_revision,
            "timestamp": result.timestamp.isoformat(),
            "dimension_scores": {
                dim.value: {
                    "score": score_data.score,
                    "weight": score_data.weight
                }
                for dim, score_data in result.dimension_scores.items()
            },
            "rule_violations": result.rule_violations,
            "feedback_summary": result.feedback.get("summary", "")
        }
        
        try:
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(record_data, f, ensure_ascii=False, indent=2)
            logger.info(f"审核记录已保存: {record_file}")
        except Exception as e:
            logger.error(f"保存审核记录失败: {e}")


class GenreTypeDetector:
    """题材类型检测器"""
    
    def detect(self, genre_info: Dict[str, Any]) -> GenreType:
        """
        检测题材类型
        
        Args:
            genre_info: 题材信息
            
        Returns:
            题材类型
        """
        # 提取特征
        heat_index = genre_info.get("heat_index", 0)
        growth_rate = genre_info.get("growth_rate", 0)
        market_share = genre_info.get("market_share", 0)
        reader_maturity = genre_info.get("reader_maturity", 0)
        market_stability = genre_info.get("market_stability", 0)
        innovation_score = genre_info.get("innovation_score", 0)
        production_rate = genre_info.get("production_rate", 0)
        reader_retention = genre_info.get("reader_retention", 0)
        monetization = genre_info.get("monetization", 0)
        critical_acclaim = genre_info.get("critical_acclaim", 0)
        award_count = genre_info.get("award_count", 0)
        depth_score = genre_info.get("depth_score", 0)
        
        # 应用检测规则
        
        # 1. 高质量成熟题材检测
        if (heat_index > 90 and 
            reader_maturity > 0.7 and 
            market_stability > 0.8):
            return GenreType.HIGH_QUALITY
        
        # 2. 实验性创新题材检测
        if (growth_rate > 0.2 and 
            market_share < 0.1 and 
            innovation_score > 0.6):
            return GenreType.EXPERIMENTAL
        
        # 3. 商业化量产题材检测
        if (production_rate > 0.5 and 
            reader_retention > 0.6 and 
            monetization > 0.7):
            return GenreType.COMMERCIAL
        
        # 4. 文学性精品题材检测
        if (critical_acclaim > 0.6 and 
            award_count > 0 and 
            depth_score > 0.7):
            return GenreType.LITERARY
        
        # 5. 基于热度指数的默认检测
        if heat_index > 80:
            return GenreType.HIGH_QUALITY
        elif heat_index > 60:
            return GenreType.COMMERCIAL
        elif innovation_score > 0.5:
            return GenreType.EXPERIMENTAL
        else:
            return GenreType.COMMERCIAL  # 默认商业化题材
    
    def get_detection_details(self, genre_info: Dict[str, Any]) -> Dict[str, Any]:
        """获取检测详情"""
        genre_type = self.detect(genre_info)
        
        return {
            "detected_type": genre_type.value,
            "detection_rules_applied": self._get_applied_rules(genre_info, genre_type),
            "feature_scores": {
                "heat_index": genre_info.get("heat_index", 0),
                "growth_rate": genre_info.get("growth_rate", 0),
                "market_share": genre_info.get("market_share", 0),
                "reader_maturity": genre_info.get("reader_maturity", 0),
                "market_stability": genre_info.get("market_stability", 0),
                "innovation_score": genre_info.get("innovation_score", 0),
                "production_rate": genre_info.get("production_rate", 0),
                "reader_retention": genre_info.get("reader_retention", 0),
                "monetization": genre_info.get("monetization", 0),
                "critical_acclaim": genre_info.get("critical_acclaim", 0),
                "award_count": genre_info.get("award_count", 0),
                "depth_score": genre_info.get("depth_score", 0)
            },
            "confidence": self._calculate_confidence(genre_info, genre_type)
        }
    
    def _get_applied_rules(self, genre_info: Dict[str, Any], genre_type: GenreType) -> List[str]:
        """获取应用的检测规则"""
        rules = []
        
        if genre_type == GenreType.HIGH_QUALITY:
            if genre_info.get("heat_index", 0) > 90:
                rules.append("heat_index > 90")
            if genre_info.get("reader_maturity", 0) > 0.7:
                rules.append("reader_maturity > 0.7")
            if genre_info.get("market_stability", 0) > 0.8:
                rules.append("market_stability > 0.8")
        
        elif genre_type == GenreType.EXPERIMENTAL:
            if genre_info.get("growth_rate", 0) > 0.2:
                rules.append("growth_rate > 0.2")
            if genre_info.get("market_share", 0) < 0.1:
                rules.append("market_share < 0.1")
            if genre_info.get("innovation_score", 0) > 0.6:
                rules.append("innovation_score > 0.6")
        
        elif genre_type == GenreType.COMMERCIAL:
            if genre_info.get("production_rate", 0) > 0.5:
                rules.append("production_rate > 0.5")
            if genre_info.get("reader_retention", 0) > 0.6:
                rules.append("reader_retention > 0.6")
            if genre_info.get("monetization", 0) > 0.7:
                rules.append("monetization > 0.7")
        
        elif genre_type == GenreType.LITERARY:
            if genre_info.get("critical_acclaim", 0) > 0.6:
                rules.append("critical_acclaim > 0.6")
            if genre_info.get("award_count", 0) > 0:
                rules.append("award_count > 0")
            if genre_info.get("depth_score", 0) > 0.7:
                rules.append("depth_score > 0.7")
        
        return rules
    
    def _calculate_confidence(self, genre_info: Dict[str, Any], genre_type: GenreType) -> float:
        """计算检测置信度"""
        confidence = 0.0
        total_weight = 0
        
        if genre_type == GenreType.HIGH_QUALITY:
            weights = {"heat_index": 0.4, "reader_maturity": 0.3, "market_stability": 0.3}
            for feature, weight in weights.items():
                value = genre_info.get(feature, 0)
                if feature == "heat_index":
                    confidence += min(value / 100, 1.0) * weight
                else:
                    confidence += value * weight
                total_weight += weight
        
        elif genre_type == GenreType.EXPERIMENTAL:
            weights = {"growth_rate": 0.4, "innovation_score": 0.4, "market_share": 0.2}
            for feature, weight in weights.items():
                value = genre_info.get(feature, 0)
                if feature == "market_share":
                    # 市场占有率越小，实验性越强
                    confidence += (1 - min(value, 1.0)) * weight
                else:
                    confidence += value * weight
                total_weight += weight
        
        elif genre_type == GenreType.COMMERCIAL:
            weights = {"production_rate": 0.4, "monetization": 0.4, "reader_retention": 0.2}
            for feature, weight in weights.items():
                value = genre_info.get(feature, 0)
                confidence += value * weight
                total_weight += weight
        
        elif genre_type == GenreType.LITERARY:
            weights = {"critical_acclaim": 0.4, "depth_score": 0.4, "award_count": 0.2}
            for feature, weight in weights.items():
                value = genre_info.get(feature, 0)
                if feature == "award_count":
                    confidence += min(value / 5, 1.0) * weight  # 假设最多5个奖项
                else:
                    confidence += value * weight
                total_weight += weight
        
        if total_weight > 0:
            confidence = confidence / total_weight
        
        return min(max(confidence, 0.0), 1.0)


class ReviewRuleEngine:
    """审核规则引擎"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> Dict[str, Any]:
        """初始化规则"""
        return {
            "logic_consistency": {
                "description": "逻辑一致性检查",
                "severity": "critical",
                "check_function": self._check_logic_consistency
            },
            "character_development": {
                "description": "人物发展合理性检查",
                "severity": "high",
                "check_function": self._check_character_development
            },
            "plot_coherence": {
                "description": "情节连贯性检查",
                "severity": "high",
                "check_function": self._check_plot_coherence
            },
            "market_feasibility": {
                "description": "市场可行性检查",
                "severity": "medium",
                "check_function": self._check_market_feasibility
            },
            "style_consistency": {
                "description": "风格一致性检查",
                "severity": "medium",
                "check_function": self._check_style_consistency
            }
        }
    
    def check_all_rules(self, plan_data: Dict[str, Any], genre_type: GenreType) -> List[Dict[str, Any]]:
        """检查所有规则"""
        violations = []
        
        for rule_name, rule_config in self.rules.items():
            check_func = rule_config["check_function"]
            severity = rule_config["severity"]
            
            try:
                is_violated, details = check_func(plan_data, genre_type)
                if is_violated:
                    violations.append({
                        "rule_name": rule_name,
                        "description": rule_config["description"],
                        "severity": severity,
                        "details": details
                    })
            except Exception as e:
                logger.error(f"规则检查失败 {rule_name}: {e}")
        
        return violations
    
    def _check_logic_consistency(self, plan_data: Dict[str, Any], genre_type: GenreType) -> Tuple[bool, str]:
        """检查逻辑一致性"""
        # 简化检查：确保关键设定没有矛盾
        settings = plan_data.get("settings", {})
        plot = plan_data.get("plot", {})
        
        issues = []
        
        # 检查世界观一致性
        if settings.get("worldview", "") and plot.get("events", []):
            # 这里可以添加更复杂的逻辑检查
            pass
        
        if issues:
            return True, "; ".join(issues)
        else:
            return False, ""
    
    def _check_character_development(self, plan_data: Dict[str, Any], genre_type: GenreType) -> Tuple[bool, str]:
        """检查人物发展合理性"""
        characters = plan_data.get("characters", [])
        
        issues = []
        
        for char in characters:
            # 检查人物成长弧线
            if char.get("is_main", False) and not char.get("growth_arc", ""):
                issues.append(f"主角 '{char.get('name', '未知')}' 缺乏成长弧线")
            
            # 检查人物动机
            if not char.get("motivation", ""):
                issues.append(f"人物 '{char.get('name', '未知')}' 缺乏明确动机")
        
        if issues:
            return True, "; ".join(issues[:3])  # 只返回前3个问题
        else:
            return False, ""
    
    def _check_plot_coherence(self, plan_data: Dict[str, Any], genre_type: GenreType) -> Tuple[bool, str]:
        """检查情节连贯性"""
        plot = plan_data.get("plot", {})
        events = plot.get("key_events", [])
        
        if len(events) < 3:
            return True, "关键事件数量不足（至少需要3个）"
        
        # 检查事件之间的逻辑关系
        for i in range(len(events) - 1):
            current_event = events[i]
            next_event = events[i + 1]
            
            # 简化检查：确保事件有逻辑关联
            if not current_event.get("leads_to", "") and i < len(events) - 1:
                return True, f"事件{i+1}缺乏明确的后续发展"
        
        return False, ""
    
    def _check_market_feasibility(self, plan_data: Dict[str, Any], genre_type: GenreType) -> Tuple[bool, str]:
        """检查市场可行性"""
        market_info = plan_data.get("market_analysis", {})
        
        # 不同题材类型的市场要求不同
        if genre_type == GenreType.COMMERCIAL:
            # 商业化题材要求明确的市场定位
            if not market_info.get("target_readers", ""):
                return True, "商业化题材需要明确的目标读者"
            if not market_info.get("unique_selling_points", []):
                return True, "商业化题材需要明确的独特卖点"
        
        elif genre_type == GenreType.EXPERIMENTAL:
            # 实验性题材允许较高的市场风险
            pass  # 放宽要求
        
        elif genre_type == GenreType.LITERARY:
            # 文学性题材更注重艺术价值
            if not market_info.get("artistic_value", ""):
                return True, "文学性题材需要明确的艺术价值定位"
        
        return False, ""
    
    def _check_style_consistency(self, plan_data: Dict[str, Any], genre_type: GenreType) -> Tuple[bool, str]:
        """检查风格一致性"""
        style_info = plan_data.get("style_parameters", {})
        
        required_fields = ["language_style", "narrative_pace", "emotional_tone"]
        missing_fields = [field for field in required_fields if field not in style_info]
        
        if missing_fields:
            return True, f"缺失风格参数: {', '.join(missing_fields)}"
        
        return False, ""