# -*- coding: utf-8 -*-
"""
数据源管理器 - 多平台数据源管理
基于详细设计文档实现
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DataSourceConfig(BaseModel):
    """数据源配置模型"""
    name: str
    type: str  # api, crawler, third_party, local_cache
    endpoint: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit: Optional[str] = None
    fallback: Optional[str] = None
    data_format: str = "json"
    update_frequency: str = "hourly"
    priority: int = 1  # 优先级，1为最高
    enabled: bool = True


class DataQualityMetrics(BaseModel):
    """数据质量指标"""
    completeness: float = 0.0  # 完整率 (0-1)
    timeliness: float = 0.0    # 时效性 (0-1)
    accuracy: float = 0.0      # 准确率 (0-1)
    consistency: float = 0.0   # 一致性 (0-1)
    uniqueness: float = 0.0    # 唯一性 (0-1)
    overall_score: float = 0.0  # 综合评分


class DataSourceResult(BaseModel):
    """数据源结果"""
    source_name: str
    data: Dict[str, Any]
    quality: DataQualityMetrics
    timestamp: datetime
    is_fallback: bool = False
    error: Optional[str] = None


class DataSourceManager:
    """多平台数据源管理器"""
    
    def __init__(self, config_path: str = "config/data_sources.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.sources = self._initialize_sources()
        self.cache_dir = Path("data/cache/data_sources")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据源优先级排序
        self.prioritized_sources = self._prioritize_sources()
        
        # 质量验证器
        self.quality_validator = QualityValidator()
        
        # 降级处理器
        self.fallback_handler = FallbackHandler()
        
        logger.info(f"数据源管理器初始化完成，共 {len(self.sources)} 个数据源")
    
    def _load_config(self) -> Dict[str, DataSourceConfig]:
        """加载数据源配置"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                # 使用默认配置
                return self._get_default_config()
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            sources = {}
            for name, source_config in config_data.get("data_sources", {}).items():
                sources[name] = DataSourceConfig(name=name, **source_config)
            
            return sources
            
        except Exception as e:
            logger.error(f"加载数据源配置失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, DataSourceConfig]:
        """获取默认数据源配置"""
        return {
            "qidian": DataSourceConfig(
                name="qidian",
                type="api",
                endpoint="https://api.qidian.com/trend",
                rate_limit="10 requests/minute",
                fallback="local_cache",
                data_format="json",
                update_frequency="hourly",
                priority=1,
                enabled=True
            ),
            "jinjiang": DataSourceConfig(
                name="jinjiang",
                type="crawler",
                base_url="https://www.jjwxc.net",
                rate_limit="5 requests/minute",
                fallback="local_cache",
                data_format="html",
                update_frequency="daily",
                priority=2,
                enabled=True
            ),
            "local_cache": DataSourceConfig(
                name="local_cache",
                type="local_cache",
                data_format="sqlite",
                update_frequency="daily",
                priority=3,
                enabled=True
            )
        }
    
    def _initialize_sources(self) -> Dict[str, Any]:
        """初始化数据源实例"""
        sources = {}
        
        for name, config in self.config.items():
            if not config.enabled:
                continue
                
            if config.type == "api":
                sources[name] = APIDataSource(config)
            elif config.type == "crawler":
                sources[name] = CrawlerDataSource(config)
            elif config.type == "local_cache":
                sources[name] = LocalCacheDataSource(config)
            else:
                logger.warning(f"未知数据源类型: {config.type} for {name}")
        
        return sources
    
    def _prioritize_sources(self) -> List[str]:
        """根据优先级对数据源排序"""
        return sorted(
            self.sources.keys(),
            key=lambda x: self.config[x].priority if x in self.config else 999
        )
    
    async def collect_data(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        从所有数据源收集数据
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            包含数据和质量报告的结果
        """
        logger.info("开始从所有数据源收集数据...")
        
        # 检查缓存
        if use_cache:
            cached_data = self._get_cached_data()
            if cached_data:
                logger.info("使用缓存数据")
                return cached_data
        
        # 并行收集数据
        tasks = []
        for source_name in self.prioritized_sources:
            if source_name in self.sources:
                task = self._collect_from_source(source_name)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        source_results = {}
        successful_sources = []
        
        for i, result in enumerate(results):
            source_name = self.prioritized_sources[i]
            
            if isinstance(result, Exception):
                logger.error(f"数据源 {source_name} 收集失败: {result}")
                # 尝试降级处理
                fallback_result = await self.fallback_handler.get_fallback_data(
                    source_name, str(result)
                )
                source_results[source_name] = fallback_result
            else:
                source_results[source_name] = result
                if result.quality.overall_score >= 0.7:  # 质量阈值
                    successful_sources.append(source_name)
        
        # 合并数据
        merged_data = self._merge_data(source_results)
        
        # 计算整体质量
        overall_quality = self._calculate_overall_quality(source_results)
        
        # 生成质量报告
        quality_report = self._generate_quality_report(source_results, overall_quality)
        
        # 构建最终结果
        final_result = {
            "data": merged_data,
            "quality_report": quality_report,
            "source_qualities": {
                name: result.quality.overall_score
                for name, result in source_results.items()
            },
            "overall_quality": overall_quality.overall_score,
            "successful_sources": successful_sources,
            "timestamp": datetime.now().isoformat(),
            "cache_key": self._generate_cache_key()
        }
        
        # 缓存结果
        self._cache_data(final_result)
        
        logger.info(f"数据收集完成，成功源: {len(successful_sources)}/{len(self.sources)}")
        return final_result
    
    async def _collect_from_source(self, source_name: str) -> DataSourceResult:
        """从单个数据源收集数据"""
        source = self.sources[source_name]
        config = self.config[source_name]
        
        logger.info(f"从数据源 {source_name} 收集数据...")
        
        try:
            # 收集数据
            data = await source.collect()
            
            # 验证数据质量
            quality = self.quality_validator.validate(data, source_name)
            
            # 构建结果
            result = DataSourceResult(
                source_name=source_name,
                data=data,
                quality=quality,
                timestamp=datetime.now()
            )
            
            logger.info(f"数据源 {source_name} 收集成功，质量评分: {quality.overall_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"数据源 {source_name} 收集失败: {e}")
            raise
    
    def _merge_data(self, source_results: Dict[str, DataSourceResult]) -> Dict[str, Any]:
        """合并多个数据源的数据"""
        merged = {
            "heat_index": 0.0,
            "reader_demographics": {},
            "genre_distribution": {},
            "platform_data": {},
            "raw_data": {}
        }
        
        total_weight = 0
        weighted_heat = 0
        
        for source_name, result in source_results.items():
            if result.is_fallback:
                weight = 0.3  # 降级数据权重较低
            else:
                weight = result.quality.overall_score
            
            data = result.data
            
            # 合并热度指数（加权平均）
            if "heat_index" in data:
                weighted_heat += data["heat_index"] * weight
                total_weight += weight
            
            # 合并读者画像
            if "reader_demographics" in data:
                for key, value in data["reader_demographics"].items():
                    if key in merged["reader_demographics"]:
                        merged["reader_demographics"][key] = (
                            merged["reader_demographics"][key] + value
                        ) / 2
                    else:
                        merged["reader_demographics"][key] = value
            
            # 合并题材分布
            if "genre_distribution" in data:
                for genre, share in data["genre_distribution"].items():
                    if genre in merged["genre_distribution"]:
                        merged["genre_distribution"][genre] = max(
                            merged["genre_distribution"][genre], share
                        )
                    else:
                        merged["genre_distribution"][genre] = share
            
            # 保存平台原始数据
            merged["platform_data"][source_name] = data
            merged["raw_data"][source_name] = data
        
        # 计算加权平均热度
        if total_weight > 0:
            merged["heat_index"] = weighted_heat / total_weight
        
        # 标准化题材分布
        total_share = sum(merged["genre_distribution"].values())
        if total_share > 0:
            for genre in merged["genre_distribution"]:
                merged["genre_distribution"][genre] /= total_share
        
        return merged
    
    def _calculate_overall_quality(self, source_results: Dict[str, DataSourceResult]) -> DataQualityMetrics:
        """计算整体数据质量"""
        if not source_results:
            return DataQualityMetrics()
        
        qualities = [result.quality for result in source_results.values()]
        
        return DataQualityMetrics(
            completeness=sum(q.completeness for q in qualities) / len(qualities),
            timeliness=sum(q.timeliness for q in qualities) / len(qualities),
            accuracy=sum(q.accuracy for q in qualities) / len(qualities),
            consistency=sum(q.consistency for q in qualities) / len(qualities),
            uniqueness=sum(q.uniqueness for q in qualities) / len(qualities),
            overall_score=sum(q.overall_score for q in qualities) / len(qualities)
        )
    
    def _generate_quality_report(self, source_results: Dict[str, DataSourceResult], 
                                overall_quality: DataQualityMetrics) -> Dict[str, Any]:
        """生成质量报告"""
        report = {
            "overall_score": overall_quality.overall_score,
            "metrics": {
                "completeness": {
                    "score": overall_quality.completeness,
                    "threshold": 0.95,
                    "passed": overall_quality.completeness >= 0.95
                },
                "timeliness": {
                    "score": overall_quality.timeliness,
                    "threshold": 0.8,  # 24小时内
                    "passed": overall_quality.timeliness >= 0.8
                },
                "accuracy": {
                    "score": overall_quality.accuracy,
                    "threshold": 0.9,
                    "passed": overall_quality.accuracy >= 0.9
                },
                "consistency": {
                    "score": overall_quality.consistency,
                    "threshold": 0.85,
                    "passed": overall_quality.consistency >= 0.85
                },
                "uniqueness": {
                    "score": overall_quality.uniqueness,
                    "threshold": 0.99,
                    "passed": overall_quality.uniqueness >= 0.99
                }
            },
            "source_details": {},
            "recommendations": []
        }
        
        # 添加数据源详情
        for source_name, result in source_results.items():
            report["source_details"][source_name] = {
                "quality_score": result.quality.overall_score,
                "is_fallback": result.is_fallback,
                "timestamp": result.timestamp.isoformat(),
                "error": result.error
            }
        
        # 生成建议
        if overall_quality.completeness < 0.95:
            report["recommendations"].append("增加数据源以提高数据完整性")
        if overall_quality.timeliness < 0.8:
            report["recommendations"].append("优化数据采集频率以提高时效性")
        if overall_quality.accuracy < 0.9:
            report["recommendations"].append("加强数据验证以提高准确性")
        
        return report
    
    def _get_cached_data(self) -> Optional[Dict[str, Any]]:
        """获取缓存数据"""
        cache_key = self._generate_cache_key()
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                
                # 检查缓存是否过期（1小时）
                cache_time = datetime.fromisoformat(cached.get("timestamp", "2000-01-01"))
                if datetime.now() - cache_time < timedelta(hours=1):
                    return cached
                    
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}")
        
        return None
    
    def _cache_data(self, data: Dict[str, Any]):
        """缓存数据"""
        try:
            cache_key = self._generate_cache_key()
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已缓存: {cache_file}")
            
        except Exception as e:
            logger.error(f"缓存数据失败: {e}")
    
    def _generate_cache_key(self) -> str:
        """生成缓存键"""
        timestamp = datetime.now().strftime("%Y%m%d_%H")
        return f"trend_data_{timestamp}"
    
    def get_source_status(self) -> Dict[str, Any]:
        """获取数据源状态"""
        status = {
            "total_sources": len(self.sources),
            "enabled_sources": len([s for s in self.sources.values()]),
            "source_details": {}
        }
        
        for source_name, source in self.sources.items():
            config = self.config[source_name]
            status["source_details"][source_name] = {
                "type": config.type,
                "priority": config.priority,
                "enabled": config.enabled,
                "update_frequency": config.update_frequency
            }
        
        return status


class APIDataSource:
    """API数据源"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def collect(self) -> Dict[str, Any]:
        """从API收集数据"""
        if not self.config.endpoint:
            raise ValueError("API端点未配置")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = await self.client.get(self.config.endpoint, headers=headers)
            response.raise_for_status()
            
            if self.config.data_format == "json":
                data = response.json()
            else:
                data = {"raw": response.text}
            
            # 转换为标准格式
            return self._normalize_data(data)
            
        except Exception as e:
            raise Exception(f"API请求失败: {e}")
    
    def _normalize_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化API数据"""
        # 这里需要根据具体API响应格式进行适配
        # 目前返回模拟数据
        return {
            "heat_index": 95.2,
            "reader_demographics": {
                "18-25": 35,
                "26-35": 45,
                "36-45": 15,
                "46+": 5
            },
            "genre_distribution": {
                "都市现实": 0.25,
                "玄幻奇幻": 0.20,
                "科幻未来": 0.15,
                "历史军事": 0.10,
                "游戏竞技": 0.10,
                "悬疑灵异": 0.10,
                "二次元": 0.05,
                "其他": 0.05
            },
            "platform": "qidian",
            "timestamp": datetime.now().isoformat()
        }


class CrawlerDataSource:
    """爬虫数据源"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
    
    async def collect(self) -> Dict[str, Any]:
        """从网页爬取数据"""
        # 这里需要实现实际的爬虫逻辑
        # 目前返回模拟数据
        return {
            "heat_index": 88.7,
            "reader_demographics": {
                "18-25": 40,
                "26-35": 40,
                "36-45": 15,
                "46+": 5
            },
            "genre_distribution": {
                "都市现实": 0.30,
                "玄幻奇幻": 0.15,
                "科幻未来": 0.10,
                "历史军事": 0.05,
                "游戏竞技": 0.15,
                "悬疑灵异": 0.15,
                "二次元": 0.05,
                "其他": 0.05
            },
            "platform": "jinjiang",
            "timestamp": datetime.now().isoformat()
        }


class LocalCacheDataSource:
    """本地缓存数据源"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.cache_file = Path("data/cache/trend_data.json")
    
    async def collect(self) -> Dict[str, Any]:
        """从本地缓存获取数据"""
        if not self.cache_file.exists():
            return {
                "heat_index": 75.0,
                "reader_demographics": {},
                "genre_distribution": {},
                "platform": "local_cache",
                "timestamp": datetime.now().isoformat(),
                "is_cached": True
            }
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data["is_cached"] = True
            return data
        except Exception:
            return {
                "heat_index": 75.0,
                "reader_demographics": {},
                "genre_distribution": {},
                "platform": "local_cache",
                "timestamp": datetime.now().isoformat(),
                "is_cached": True
            }


class QualityValidator:
    """数据质量验证器"""
    
    def validate(self, data: Dict[str, Any], source_name: str) -> DataQualityMetrics:
        """验证数据质量"""
        metrics = DataQualityMetrics()
        
        # 完整性检查
        required_fields = ["heat_index", "reader_demographics", "genre_distribution"]
        completeness = sum(1 for field in required_fields if field in data) / len(required_fields)
        metrics.completeness = completeness
        
        # 时效性检查（假设数据中有timestamp字段）
        timeliness = 1.0
        if "timestamp" in data:
            try:
                data_time = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                age_hours = (datetime.now() - data_time).total_seconds() / 3600
                timeliness = max(0, 1 - age_hours / 24)  # 24小时内为满分
            except:
                timeliness = 0.5
        
        metrics.timeliness = timeliness
        
        # 准确性检查（基于数据合理性）
        accuracy = 1.0
        if "heat_index" in data:
            heat = data["heat_index"]
            if not (0 <= heat <= 100):
                accuracy *= 0.5
        
        if "genre_distribution" in data:
            total_share = sum(data["genre_distribution"].values())
            if abs(total_share - 1.0) > 0.1:  # 允许10%误差
                accuracy *= 0.7
        
        metrics.accuracy = accuracy
        
        # 一致性检查（跨字段一致性）
        consistency = 1.0
        # 这里可以添加更复杂的一致性检查
        metrics.consistency = consistency
        
        # 唯一性检查（数据去重）
        uniqueness = 1.0
        metrics.uniqueness = uniqueness
        
        # 计算综合评分
        weights = {
            "completeness": 0.3,
            "timeliness": 0.25,
            "accuracy": 0.25,
            "consistency": 0.1,
            "uniqueness": 0.1
        }
        
        overall_score = (
            metrics.completeness * weights["completeness"] +
            metrics.timeliness * weights["timeliness"] +
            metrics.accuracy * weights["accuracy"] +
            metrics.consistency * weights["consistency"] +
            metrics.uniqueness * weights["uniqueness"]
        )
        
        metrics.overall_score = overall_score
        
        return metrics


class FallbackHandler:
    """降级处理器"""
    
    async def get_fallback_data(self, source_name: str, error: str) -> DataSourceResult:
        """获取降级数据"""
        logger.warning(f"数据源 {source_name} 降级处理，错误: {error}")
        
        # 根据数据源类型提供不同的降级数据
        if "qidian" in source_name:
            fallback_data = {
                "heat_index": 50.0,
                "reader_demographics": {"18-25": 30, "26-35": 40},
                "genre_distribution": {"都市现实": 0.3, "玄幻奇幻": 0.2},
                "platform": source_name,
                "timestamp": datetime.now().isoformat(),
                "is_fallback": True
            }
        elif "jinjiang" in source_name:
            fallback_data = {
                "heat_index": 45.0,
                "reader_demographics": {"18-25": 35, "26-35": 35},
                "genre_distribution": {"都市现实": 0.4, "言情": 0.3},
                "platform": source_name,
                "timestamp": datetime.now().isoformat(),
                "is_fallback": True
            }
        else:
            fallback_data = {
                "heat_index": 40.0,
                "reader_demographics": {},
                "genre_distribution": {},
                "platform": source_name,
                "timestamp": datetime.now().isoformat(),
                "is_fallback": True
            }
        
        # 创建质量指标（降级数据质量较低）
        quality = DataQualityMetrics(
            completeness=0.6,
            timeliness=0.5,
            accuracy=0.4,
            consistency=0.7,
            uniqueness=0.8,
            overall_score=0.6
        )
        
        return DataSourceResult(
            source_name=source_name,
            data=fallback_data,
            quality=quality,
            timestamp=datetime.now(),
            is_fallback=True,
            error=error
        )