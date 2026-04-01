# AI小说生成Agent系统 - 详细设计文档（更新版）

## 更新说明
基于功能性能需求文档的四大改进点，本详细设计文档进行了相应更新：
1. TrendAgent：增强数据源管理和相似度计算
2. PlannerAgent：新增差异化审核和题材类型检测
3. 新增MonitorAgent和AlertAgent详细设计
4. 更新硬件配置和部署设计
5. 增强性能优化和容错机制

## 1. TrendAgent详细设计（增强版）

### 1.1 模块结构更新
```
backend/app/agents/trend/
├── __init__.py
├── main.py                    # 主执行入口
├── data_collector.py          # 数据采集模块（增强）
├── genre_analyzer.py          # 题材分析模块
├── trend_predictor.py         # 趋势预测模块
├── genre_library.py           # 题材库管理
├── cache_manager.py           # 缓存管理
├── output_formatter.py        # 输出格式化
├── data_source_manager.py     # 数据源管理（新增）
├── similarity_calculator.py   # 相似度计算（增强）
├── quality_validator.py       # 数据质量验证（新增）
└── utils/
    ├── http_client.py         # HTTP客户端（支持多平台）
    ├── text_similarity.py     # 文本相似度计算（Sentence-BERT）
    ├── time_utils.py          # 时间处理工具
    ├── config_loader.py       # 配置加载（新增）
    ├── fallback_handler.py    # 降级处理（新增）
    └── data_merger.py         # 数据合并（新增）
```

### 1.2 数据源管理模块详细设计

#### 1.2.1 DataSourceManager类
```python
class DataSourceManager:
    """多平台数据源管理器"""
    
    def __init__(self, config_path="config/data_sources.yaml"):
        self.config = self._load_config(config_path)
        self.sources = self._initialize_sources()
        self.quality_metrics = QualityMetrics()
        self.fallback_handler = FallbackHandler()
        
        # 数据源优先级排序
        self.prioritized_sources = self._prioritize_sources()
    
    def _load_config(self, config_path):
        """加载数据源配置"""
        config = {
            "qidian": {
                "type": "api",
                "endpoint": "https://api.qidian.com/trend",
                "rate_limit": "10 requests/minute",
                "timeout": 30.0,
                "retry_times": 3,
                "fallback": "local_cache",
                "priority": 1,
                "weight": 0.4,  # 在合并中的权重
                "required_fields": ["heat_index", "reader_demographics"],
                "validation_rules": {
                    "heat_index": {"min": 0, "max": 100},
                    "read_count": {"min": 0}
                }
            },
            "jinjiang": {
                "type": "crawler",
                "base_url": "https://www.jjwxc.net",
                "selectors": {
                    "hot_list": ".hot-list li",
                    "genre_tags": ".tag-item",
                    "ranking": ".rank-item",
                    "novel_info": ".novel-info"
                },
                "anti_crawler": {
                    "enabled": True,
                    "strategy": "rotating_proxy",
                    "delay_range": [1.0, 3.0],
                    "user_agents": ["agent1", "agent2", "agent3"]
                },
                "respect_robots_txt": True,
                "priority": 2,
                "weight": 0.3
            },
            "data_aggregator": {
                "type": "third_party",
                "provider": "novel_insights_api",
                "api_key_env": "NOVEL_INSIGHTS_API_KEY",
                "endpoint": "https://api.novel-insights.com/v1/trends",
                "metrics": ["heat_index", "reader_demographics", "trend_analysis", "market_saturation"],
                "cache_ttl": 3600,
                "priority": 3,
                "weight": 0.3
            }
        }
        return config
    
    def _initialize_sources(self):
        """初始化数据源实例"""
        sources = {}
        
        for source_name, source_config in self.config.items():
            if source_config["type"] == "api":
                sources[source_name] = APIDataSource(source_config)
            elif source_config["type"] == "crawler":
                sources[source_name] = CrawlerDataSource(source_config)
            elif source_config["type"] == "third_party":
                sources[source_name] = ThirdPartyDataSource(source_config)
        
        return sources
    
    async def collect_data(self, use_cache=True, force_refresh=False):
        """从多个数据源收集数据"""
        collected_data = {}
        source_qualities = {}
        
        # 并行收集数据
        async with asyncio.TaskGroup() as tg:
            tasks = {}
            for source_name, source in self.sources.items():
                if force_refresh or not use_cache:
                    task = tg.create_task(source.collect())
                else:
                    task = tg.create_task(source.get_cached_data())
                tasks[source_name] = task
        
        # 处理收集结果
        for source_name, task in tasks.items():
            try:
                data = await task
                
                # 验证数据质量
                quality_score = self.quality_metrics.evaluate(data, source_name)
                source_qualities[source_name] = quality_score
                
                # 记录质量指标
                self._record_quality_metrics(source_name, quality_score, data)
                
                # 根据质量调整权重
                adjusted_weight = self._adjust_weight_by_quality(
                    self.config[source_name]["weight"],
                    quality_score
                )
                
                # 合并数据
                collected_data = self._merge_data_with_weight(
                    collected_data, 
                    data, 
                    adjusted_weight
                )
                
            except Exception as e:
                logger.error(f"数据源{source_name}处理失败: {e}")
                # 使用降级数据
                fallback_data = self.fallback_handler.get_fallback_data(source_name)
                collected_data = self._merge_data_with_weight(
                    collected_data,
                    fallback_data,
                    self.config[source_name]["weight"] * 0.5  # 降级数据权重减半
                )
        
        # 计算整体数据质量
        overall_quality = self._calculate_overall_quality(source_qualities)
        
        # 生成数据质量报告
        quality_report = self._generate_quality_report(source_qualities, overall_quality)
        
        return {
            "data": collected_data,
            "quality_report": quality_report,
            "source_qualities": source_qualities,
            "overall_quality": overall_quality,
            "timestamp": datetime.now().isoformat()
        }
    
    def _merge_data_with_weight(self, existing_data, new_data, weight):
        """根据权重合并数据"""
        if not existing_data:
            return new_data
        
        merged = {}
        
        # 合并通用字段
        for key in set(existing_data.keys()) | set(new_data.keys()):
            if key in existing_data and key in new_data:
                # 加权平均
                if isinstance(existing_data[key], (int, float)) and isinstance(new_data[key], (int, float)):
                    existing_weight = 1 - weight
                    merged[key] = existing_data[key] * existing_weight + new_data[key] * weight
                else:
                    # 非数值类型，根据质量选择
                    merged[key] = new_data[key] if weight > 0.5 else existing_data[key]
            elif key in existing_data:
                merged[key] = existing_data[key]
            else:
                merged[key] = new_data[key]
        
        return merged
```

#### 1.2.2 数据质量验证类
```python
class QualityValidator:
    """数据质量验证器"""
    
    def __init__(self):
        self.metrics = {
            "completeness": self._calculate_completeness,
            "timeliness": self._calculate_timeliness,
            "accuracy": self._calculate_accuracy,
            "consistency": self._calculate_consistency,
            "uniqueness": self._calculate_uniqueness
        }
        
        self.thresholds = {
            "completeness": 0.95,  # 95%完整
            "timeliness": 24,      # 24小时内
            "accuracy": 0.90,      # 90%准确
            "consistency": 0.85,   # 85%一致
            "uniqueness": 0.99     # 99%唯一
        }
    
    def validate(self, data, source_name):
        """验证数据质量"""
        validation_results = {}
        
        for metric_name, metric_func in self.metrics.items():
            try:
                score = metric_func(data, source_name)
                validation_results[metric_name] = {
                    "score": score,
                    "passed": score >= self.thresholds[metric_name],
                    "threshold": self.thresholds[metric_name]
                }
            except Exception as e:
                logger.warning(f"质量指标{metric_name}计算失败: {e}")
                validation_results[metric_name] = {
                    "score": 0.0,
                    "passed": False,
                    "error": str(e)
                }
        
        # 计算综合质量分数
        overall_score = self._calculate_overall_score(validation_results)
        
        return {
            "overall_score": overall_score,
            "metrics": validation_results,
            "passed_all": all(r["passed"] for r in validation_results.values() if "passed" in r)
        }
    
    def _calculate_completeness(self, data, source_name):
        """计算数据完整率"""
        required_fields = self._get_required_fields(source_name)
        
        if not required_fields:
            return 1.0
        
        present_fields = 0
        for field in required_fields:
            if field in data and data[field] is not None:
                present_fields += 1
        
        return present_fields / len(required_fields)
    
    def _calculate_timeliness(self, data, source_name):
        """计算数据时效性"""
        if "timestamp" not in data:
            return 0.0
        
        try:
            data_time = datetime.fromisoformat(data["timestamp"])
            current_time = datetime.now()
            time_diff = (current_time - data_time).total_seconds() / 3600  # 小时
            
            # 时效性分数：24小时内为1.0，超过线性下降
            if time_diff <= 24:
                return 1.0
            else:
                return max(0.0, 1.0 - (time_diff - 24) / 48)  # 48小时后为0
        except:
            return 0.0
    
    def _calculate_accuracy(self, data, source_name):
        """计算数据准确率（需要历史数据对比）"""
        # 这里可以使用历史数据的统计特征进行验证
        # 例如：数值字段是否在合理范围内
        accuracy_checks = [
            self._check_numeric_range(data, "heat_index", 0, 100),
            self._check_numeric_range(data, "read_count", 0, None),
            self._check_string_format(data, "timestamp", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        ]
        
        passed_checks = sum(1 for check in accuracy_checks if check)
        return passed_checks / len(accuracy_checks) if accuracy_checks else 1.0
    
    def _check_numeric_range(self, data, field, min_val, max_val):
        """检查数值字段范围"""
        if field not in data:
            return False
        
        value = data[field]
        if not isinstance(value, (int, float)):
            return False
        
        if min_val is not None and value < min_val:
            return False
        
        if max_val is not None and value > max_val:
            return False
        
        return True
```

### 1.3 相似度计算模块增强

#### 1.3.1 Sentence-BERT相似度计算
```python
class SentenceBERTSimilarity:
    """基于Sentence-BERT的文本相似度计算"""
    
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2", device=None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.tokenizer = None
        self.cache = LRUCache(maxsize=10000)  # 缓存1万个结果
        self.load_model()
    
    def load_model(self):
        """加载预训练模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"加载Sentence-BERT模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            
            # 预热模型
            self.model.encode(["预热文本"], show_progress_bar=False)
            logger.info("模型加载完成")
            
        except ImportError:
            logger.error("请安装sentence-transformers: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise
    
    def calculate_similarity(self, text1, text2, use_cache=True):
        """计算两个文本的相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 生成缓存键
        cache_key = self._generate_cache_key(text1, text2)
        
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # 文本预处理
            processed1 = self._preprocess_text(text1)
            processed2 = self._preprocess_text(text2)
            
            # 生成向量
            embeddings = self.model.encode([processed1, processed2], 
                                         convert_to_tensor=True,
                                         show_progress_bar=False)
            
            # 计算余弦相似度
            similarity = util.cos_sim(embeddings[0], embeddings[1]).item()
            
            # 缓存结果
            if use_cache:
                self.cache[cache_key] = similarity
            
            return similarity
            
        except Exception as e:
            logger.error(f"相似度计算失败: {e}")
            # 降级到简单文本相似度
            return self._fallback_similarity(text1, text2)
    
    def _preprocess_text(self, text):
        """文本预处理"""
        if not isinstance(text, str):
            text = str(text)
        
        # 去除多余空格和换行
        text = ' '.join(text.split())
        
        # 截断过长的文本（BERT有长度限制）
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def _generate_cache_key(self, text1, text2):
        """生成缓存键"""
        # 使用哈希避免存储完整文本
        return f"{hash(text1)}:{hash(text2)}"
    
    def _fallback_similarity(self, text1, text2):
        """降级相似度计算（当BERT失败时使用）"""
        # 使用简单的Jaccard相似度
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def find_similar_items(self, target_text, item_list, threshold=0.7, limit=10):
        """在列表中查找相似项"""
        if not item_list:
            return []
        
        similarities = []
        
        for item in item_list:
            if "name" not in item:
                continue
            
            similarity = self.calculate_similarity(target_text, item["name"])
            
            if similarity >= threshold:
                similarities.append({
                    "item": item,
                    "similarity": similarity,
                    "is_new_genre": similarity < 0.7  # 相似度<0.7视为新题材
                })
        
        # 按相似度排序
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 限制返回数量
        return similarities[:limit]
```

### 1.4 数据质量监控

#### 1.4.1 质量指标收集
```python
class QualityMetricsCollector:
    """数据质量指标收集器"""
    
    def __init__(self):
        self.metrics_history = []
        self.alert_thresholds = {
            "completeness": 0.90,  # 低于90%触发告警
            "timeliness": 0.80,    # 低于80%触发告警
            "accuracy": 0.85,      # 低于85%触发告警
            "consistency": 0.80    # 低于80%触发告警
        }
    
    def collect_metrics(self, validation_results, source_name):
        """收集质量指标"""
        metrics_entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source_name,
            "overall_score": validation_results["overall_score"],
            "metrics": validation_results["metrics"],
            "alerts": self._check_alerts(validation_results)
        }
        
        self.metrics_history.append(metrics_entry)
        
        # 保持历史记录大小
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        return metrics_entry
    
    def _check_alerts(self, validation_results):
        """检查是否需要触发告警"""
        alerts = []
        
        for metric_name, metric_info in validation_results["metrics"].items():
            if "score" in metric_info:
                score = metric_info["score"]
                threshold = self.alert_thresholds.get(metric_name, 0.8)
                
                if score < threshold:
                    alerts.append({
                        "metric": metric_name,
                        "score": score,
                        "threshold": threshold,
                        "level": "warning" if score > threshold * 0.8 else "critical",
                        "message": f"{metric_name}质量低于阈值: {score:.2f} < {threshold}"
                    })
        
        return alerts
    
    def generate_quality_report(self, period="daily"):
        """生成质量报告"""
        if not self.metrics_history:
            return {"error": "无质量数据"}
        
        # 按时间段过滤数据
        now = datetime.now()
        if period == "daily":
            start_time = now - timedelta(days=1)
        elif period == "weekly":
            start_time = now - timedelta(weeks=1)
        elif period == "monthly":
            start_time = now - timedelta(days=30)
        else:
            start_time = datetime.min
        
        period_data = [
            m for m in self.metrics_history 
            if datetime.fromisoformat(m["timestamp"]) >= start_time
        ]
        
        if not period_data:
            return {"error": f"该时间段内无数据: {period}"}
        
        # 计算统计信息
        report = {
            "period": period,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "total_entries": len(period_data),
            "sources": set(m["source"] for m in period_data),
            "overall_stats": self._calculate_overall_stats(period_data),
            "source_stats": self._calculate_source_stats(period_data),
            "alert_summary": self._summarize_alerts(period_data),
            "trends": self._analyze_trends(period_data),
            "recommendations": self._generate_recommendations(period_data)
        }
        
        return report
```

## 2. PlannerAgent详细设计（增强版）

### 2.1 差异化审核系统详细设计

#### 2.1.1 差异化审核器完整实现
```python
class DifferentiatedReviewSystem:
    """完整的差异化审核系统"""
    
    def __init__(self, config_dir="config/differentiated"):
        self.config_dir = Path(config_dir)
        self.standards = self._load_all_standards()
        self.genre_detector = GenreTypeDetector()
        self.review_history = []
        self.performance_tracker = ReviewPerformanceTracker()
        
        # 初始化审核模型
        self.review_models = {
            "structure": StructureReviewModel(),
            "character": CharacterReviewModel(),
            "plot": PlotReviewModel(),
            "market": MarketReviewModel(),
            "style": StyleReviewModel(),
            "innovation": InnovationReviewModel()  # 新增创新性审核
        }
    
    def _load_all_standards(self):
        """加载所有审核标准"""
        standards = {}
        
        # 高质量成熟题材标准
        standards["high_quality_genre"] = {
            "name": "高质量成熟题材",
            "description": "市场成熟，读者期待高，要求严格（如都市现实、玄幻奇幻）",
            "total_score_threshold": 85,
            "dimension_requirements": {
                "structure": {"min": 75, "weight": 0.30},
                "character": {"min": 80, "weight": 0.25},
                "plot": {"min": 70, "weight": 0.20},
                "market": {"min": 65, "weight": 0.15},
                "style": {"min": 75, "weight": 0.10}
            },
            "special_rules": [
                {
                    "rule": "不允许出现明显逻辑漏洞",
                    "checker": "logic_consistency_checker",
                    "severity": "critical"
                },
                {
                    "rule": "人物性格必须稳定一致",
                    "checker": "character_consistency_checker", 
                    "severity": "high"
                },
                {
                    "rule": "必须符合主流审美",
                    "checker": "aesthetic_checker",
                    "severity": "medium"
                },
                {
                    "rule": "情感表达要细腻真实",
                    "checker": "emotional_authenticity_checker",
                    "severity": "medium"
                }
            ],
            "weight_adjustments": {
                "structure": 1.2,  # 结构权重增加20%
                "character": 1.3,  # 人物权重增加30%
                "market": 0.9      # 市场权重降低10%
            }
        }
        
        # 实验性创新题材标准
        standards["experimental_genre"] = {
            "name": "实验性创新题材",
            "description": "创新尝试，允许一定风险（如跨界融合、新兴题材）",
            "total_score_threshold": 70,
            "dimension_requirements": {
                "structure": {"min": 65, "weight": 0.20},
                "character": {"min": 70, "weight": 0.20},
                "plot": {"min": 60, "weight": 0.15},
                "market": {"min": 55, "weight": 0.10},
                "innovation": {"min": 65, "weight": 0.35}  # 创新性权重最高
            },
            "special_rules": [
                {
                    "rule": "允许适度创新和冒险",
                    "checker": "innovation_allowance_checker",
                    "severity": "low"
                },
                {
                    "rule": "可以尝试非传统结构",
                    "checker": "structure_flexibility_checker",
                    "severity": "low"
                },
                {
                    "rule": "接受一定程度的读者接受度风险",
                    "checker": "risk_tolerance_checker",
                    "severity": "medium"
                },
                {
                    "rule": "鼓励新颖的设定和世界观",
                    "checker": "worldview_novelty_checker",
                    "severity": "medium"
                }
            ],
            "weight_adjustments": {
                "innovation": 1.5,  # 创新性权重增加50%
                "market": 0.8,      # 市场匹配权重降低20%
                "structure": 0.9    # 结构权重降低10%
            }
        }
        
        # 商业化量产题材标准
        standards["commercial_genre"] = {
            "name": "商业化量产题材",
            "description": "追求产量和效率，质量要求适中（如快餐式网文）",
            "total_score_threshold": 75,
            "dimension_requirements": {
                "structure": {"min": 70, "weight": 0.25},
                "character": {"min": 65, "weight": 0.20},
                "plot": {"min": 70, "weight": 0.30},  # 情节权重最高
                "market": {"min": 75, "weight": 0.20},
                "style": {"min": 60, "weight": 0.05}
            },
            "special_rules": [
                {
                    "rule": "强调情节吸引力和更新速度",
                    "checker": "plot_engagement_checker",
                    "severity": "high"
                },
                {
                    "rule": "允许一定程度的套路化",
                    "checker": "formulaic_tolerance_checker",
                    "severity": "low"
                },
                {
                    "rule": "优先考虑读者留存率",
                    "checker": "reader_retention_checker",
                    "severity": "high"
                },
                {
                    "rule": "节奏要快，爽点要密集",
                    "checker": "pace_density_checker",
                    "severity": "medium"
                }
            ],
            "weight_adjustments": {
                "plot": 1.4,    # 情节权重增加40%
                "market": 1.2,  # 市场权重增加20%
                "style": 0.7    # 风格权重降低30%
            }
        }
        
        # 文学性精品题材标准
        standards["literary_genre"] = {
            "name": "文学性精品题材",
            "description": "追求文学价值，艺术性要求高（如现实主义文学）",
            "total_score_threshold": 80,
            "dimension_requirements": {
                "structure": {"min": 80, "weight": 0.20},
                "character": {"min": 85, "weight": 0.25},
                "plot": {"min": 75, "weight": 0.15},
                "language": {"min": 85, "weight": 0.25},  # 语言权重高
                "depth": {"min": 70, "weight": 0.15}      # 思想深度
            },
            "special_rules": [
                {
                    "rule": "强调文学性和思想深度",
                    "checker": "literary_depth_checker",
                    "severity": "high"
                },
                {
                    "rule": "允许较慢的叙事节奏",
                    "checker": "pace_tolerance_checker",
                    "severity": "low"
                },
                {
                    "rule": "重视语言艺术和修辞",
                    "checker": "language_artistry_checker",
                    "severity": "high"
                },
                {
                    "rule": "人物塑造要有层次感",
                    "checker": "character_layering_checker",
                    "severity": "medium"
                }
            ],
            "weight_adjustments": {
                "language": 1.4,  # 语言权重增加40%
                "depth": 1.3,     # 深度权重增加30%
                "plot": 0.9       # 情节权重降低10%
            }
        }
        
        # 默认标准（当无法确定类型时使用）
        standards["default"] = {
            "name": "默认标准",
            "description": "通用审核标准",
            "total_score_threshold": 75,
            "dimension_requirements": {
                "structure": {"min": 70, "weight": 0.25},
                "character": {"min": 70, "weight": 0.25},
                "plot": {"min": 65, "weight": 0.20},
                "market": {"min": 60, "weight": 0.20},
                "style": {"min": 65, "weight": 0.10}
            },
            "special_rules": [],
            "weight_adjustments": {}
        }
        
        return standards
    
    def review_story_plan(self, plan_data, genre_info, context=None):
        """审核故事策划案"""
        # 1. 检测题材类型
        genre_type = self.genre_detector.detect(genre_info)
        standard = self.standards.get(genre_type, self.standards["default"])
        
        # 2. 执行各维度审核
        dimension_results = {}
        for dimension_name, dimension_config in standard["dimension_requirements"].items():
            if dimension_name in self.review_models:
                model = self.review_models[dimension_name]
                result = model.review(plan_data, context)
                dimension_results[dimension_name] = result
        
        # 3. 检查特殊规则
        rule_violations = self._check_special_rules(plan_data, standard, context)
        
        # 4. 计算维度分数（应用权重调整）
        dimension_scores = self._calculate_dimension_scores(dimension_results, standard)
        
        # 5. 计算总分
        total_score = self._calculate_total_score(dimension_scores)
        
        # 6. 判断是否通过
        passed = self._determine_pass_status(total_score, dimension_scores, standard, rule_violations)
        
        # 7. 生成反馈和建议
        feedback = self._generate_feedback(dimension_results, rule_violations, passed)
        suggestions = self._generate_suggestions(dimension_results, rule_violations, genre_type)
        
        # 8. 记录审核历史
        review_record = self._create_review_record(
            plan_data, genre_type, total_score, dimension_scores, 
            passed, rule_violations, feedback
        )
        self.review_history.append(review_record)
        
        # 9. 更新性能跟踪
        self.performance_tracker.record_review(review_record)
        
        return {
            "passed": passed,
            "genre_type": genre_type,
            "standard_applied": standard["name"],
            "total_score": total_score,
            "dimension_scores": dimension_scores,
            "dimension_details": dimension_results,
            "rule_violations": rule_violations,
            "feedback": feedback,
            "suggestions": suggestions,
            "review_id": review_record["review_id"],
            "requires_revision": not passed,
            "revision_priority": self._calculate_revision_priority(dimension_scores, rule_violations)
        }
    
    def _calculate_dimension_scores(self, dimension_results, standard):
        """计算各维度分数（应用权重调整）"""
        dimension_scores = {}
        
        for dimension_name, result in dimension_results.items():
            base_score = result.get("score", 0)
            
            # 应用权重调整
            weight_adjustment = standard.get("weight_adjustments", {}).get(dimension_name, 1.0)
            adjusted_score = base_score * weight_adjustment
            
            # 确保分数在0-100范围内
            dimension_scores[dimension_name] = min(100, max(0, adjusted_score))
        
        return dimension_scores
    
    def _calculate_total_score(self, dimension_scores):
        """计算总分（加权平均）"""
        if not dimension_scores:
            return 0
        
        # 使用标准中的权重
        total_weight = 0
        weighted_sum = 0
        
        for dimension_name, score in dimension_scores.items():
            # 默认权重为1
            weight = 1.0
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    def _determine_pass_status(self, total_score, dimension_scores, standard, rule_violations):
        """判断是否通过审核"""
        # 1. 检查总分是否达标
        if total_score < standard["total_score_threshold"]:
            return False
        
        # 2. 检查各维度最低分
        for dimension_name, dimension_config in standard["dimension_requirements"].items():
            min_score = dimension_config.get("min", 0)
            actual_score = dimension_scores.get(dimension_name, 0)
            
            if actual_score < min_score:
                return False
        
        # 3. 检查严重规则违规
        critical_violations = [v for v in rule_violations if v.get("severity") == "critical"]
        if critical_violations:
            return False
        
        return True
    
    def _generate_feedback(self, dimension_results, rule_violations, passed):
        """生成审核反馈"""
        feedback = {
            "summary": "审核通过" if passed else "审核未通过",
            "strengths": [],
            "weaknesses": [],
            "rule_violations": rule_violations
        }
        
        # 分析各维度结果
        for dimension_name, result in dimension_results.items():
            dimension_score = result.get("score", 0)
            
            if dimension_score >= 80:
                feedback["strengths"].append({
                    "dimension": dimension_name,
                    "score": dimension_score,
                    "comments": result.get("strengths", [])
                })
            elif dimension_score < 60:
                feedback["weaknesses"].append({
                    "dimension": dimension_name,
                    "score": dimension_score,
                    "issues": result.get("issues", []),
                    "suggestions": result.get("suggestions", [])
                })
        
        return feedback
```

#### 2.1.2 题材类型检测器详细实现
```python
class GenreTypeDetector:
    """题材类型检测器"""
    
    def __init__(self, config_path="config/genre_type_rules.yaml"):
        self.rules = self._load_detection_rules(config_path)
        self.history = []  # 检测历史记录
        self.confidence_threshold = 0.6  # 置信度阈值
    
    def _load_detection_rules(self, config_path):
        """加载检测规则"""
        return {
            "high_quality_genre": {
                "description": "高质量成熟题材",
                "rules": [
                    {"field": "heat_index", "operator": ">", "value": 90, "weight": 0.3},
                    {"field": "reader_maturity", "operator": ">", "value": 0.7, "weight": 0.25},
                    {"field": "market_stability", "operator": ">", "value": 0.8, "weight": 0.25},
                    {"field": "critical_acclaim", "operator": ">", "value": 0.6, "weight": 0.2}
                ],
                "required_fields": ["heat_index", "reader_maturity"]
            },
            "experimental_genre": {
                "description": "实验性创新题材",
                "rules": [
                    {"field": "growth_rate", "operator": ">", "value": 0.2, "weight": 0.4},
                    {"field": "market_share", "operator": "<", "value": 0.1, "weight": 0.3},
                    {"field": "innovation_score", "operator": ">", "value": 0.6, "weight": 0.3}
                ],
                "required_fields": ["growth_rate", "innovation_score"]
            },
            "commercial_genre": {
                "description": "商业化量产题材",
                "rules": [
                    {"field": "production_rate", "operator": ">", "value": 0