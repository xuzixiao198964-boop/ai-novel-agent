# AI小说生成Agent系统 - 测试文档

## 文档概述

本文档基于需求文档、概要设计文档和详细设计文档，定义 AI 小说生成 Agent 系统的完整测试策略。包括单元测试（精细到接口级别）、集成测试、性能测试（含 **104 裸机对齐档**）、**系统测试要点**（与 `docs/TESTING.md` 呼应）及 **systemd 裸机** 部署相关验证思路（非 Docker）。

## 0. 测试环境约束说明

### 服务器硬件约束
本项目运行在资源受限的裸机服务器上：

| 资源 | 规格 | 测试影响 |
|------|------|----------|
| CPU | 2核 | 并发测试最多2个并行任务 |
| 内存 | 1GB（可用~476MB） | 禁止大内存测试，需监控OOM |
| 磁盘 | 20GB（仅剩~1GB） | 测试数据必须及时清理 |
| 部署 | 裸机 systemd（非Docker） | 直接在系统环境运行 |
| 数据库 | PostgreSQL 16（唯一持久化存储） | 无Redis |
| 缓存 | 进程内缓存 cachetools（无Redis） | 缓存测试用内存mock |
| 任务队列 | PostgreSQL任务表（无RabbitMQ） | 无MQ相关测试 |

### 测试约束
1. **并发限制**：由于内存限制，并发测试最多2个并行任务
2. **磁盘清理**：测试前后需检查磁盘空间，测试数据应及时清理
3. **内存监控**：测试过程中需监控内存使用，防止OOM
4. **数据库连接**：测试连接池不超过5个连接（生产max_connections=20）
5. **无Redis测试**：所有缓存相关测试使用PostgreSQL缓存表或进程内cachetools mock
6. **无Docker测试**：集成测试直接在裸机环境运行，使用systemd管理服务
7. **无RabbitMQ测试**：消息队列相关测试使用PostgreSQL task_queue表

### 0.1 单元测试替身与数据策略（对齐架构）

编写与执行单元测试时，**不得依赖** Redis、RabbitMQ、Docker、MinIO、独立 MQ 等组件，替身与数据来源约定如下：

| 能力 | 生产实现 | 单元测试替身 |
|------|----------|--------------|
| 会话/热点缓存 | `cachetools.TTLCache` 或 PostgreSQL `cache_entries` | `unittest.mock` 或内存 `TTLCache(maxsize=10)` |
| 支付回调幂等 | `idempotent_keys` 表 `INSERT … ON CONFLICT DO NOTHING` | 测试库真实表或 `sqlite` + 同 schema |
| 分布式锁/并发订阅 | `pg_advisory_lock` 或行级锁 | `pytest` fixture 串行化或 mock `lock.acquire` |
| 异步任务 | `task_queue` 表 + Worker 轮询 | 直接调用处理函数，或 mock `enqueue` |
| 限流 | SlowAPI + 进程内计数器 | mock 时间窗口或调高超限阈值 |
| 文件/媒体 | `/opt/ai-novel-agent/data/` | `tmp_path` / `pytest` 临时目录 |
| 向量/相似检索 | `pg_trgm` | 测试库启用扩展或 mock `similarity()` |

**执行原则**：商业化模块（§2.5–§2.12）的用例一律在 **临时目录 + 测试数据库（或事务回滚）** 中运行；不得在 104 生产盘写入大文件。

### 0.2 测试环境分级

| 级别 | 用途 | 资源假设 | 并发/内存断言 |
|------|------|----------|----------------|
| **A：本地/CI** | 单元测试、大部分集成测试 | 开发者机或 GitHub Runner（充裕） | 可按模块放宽，但仍不启动 Redis |
| **B：104 对齐（系统测试）** | 验收、冒烟、关键 E2E | 2 核 / 1GB / 20GB 磁盘 | 并发 ≤2；单进程 RSS 峰值 ≤300MB（主服务） |
| **C：性能回归（可选）** | 基准对比 | 建议在 ≥4GB 内存的专用机执行 | 文档中 104 档指标与「扩展档」分开写明 |

---

## 1. 测试策略与范围

### 1.1 测试目标
1. **功能正确性**：验证7个Agent的核心功能按需求实现
2. **接口完整性**：确保所有模块接口定义清晰、调用正确
3. **性能达标**：验证3章批次机制的性能指标
4. **健壮可靠**：测试错误处理和恢复机制
5. **部署可用**：验证生产环境部署和运行

### 1.2 测试范围矩阵
| 测试类型 | 覆盖范围 | 测试重点 | 验收标准 |
|---------|---------|---------|---------|
| 单元测试 | 所有模块接口 | 接口契约、边界条件、异常处理 | 代码覆盖率≥85% |
| 集成测试 | Agent间协作、DB 任务表 | 数据流、状态转换、错误传播 | 端到端流程100%通过（Mock LLM 时可 CI） |
| 性能测试 | 关键路径 | 响应时间、资源使用、**104 档**并发≤2、内存上限 | A 档可放宽；B 档须满足 §6.2 `production_104` |
| 系统测试 | 裸机验收 | systemd、健康检查、磁盘/内存门禁、TC-C 类用例 | 发版前在目标机或等价环境通过 |
| 部署测试 | 生产环境 | **systemd** 单元、配置、日志轮转、备份 | 服务 `active`、回滚脚本可用（非 Docker 一键） |

### 1.3 测试环境
```yaml
测试环境:
  开发环境:
    - 位置: 本地开发机
    - 用途: 单元测试、接口测试
    - 数据: 模拟数据、测试数据库
  
  集成环境:
    - 位置: 测试服务器或 CI Runner
    - 用途: 集成测试、带 PostgreSQL 的流水线测试
    - 数据: 独立测试库；任务队列为表驱动，无 RabbitMQ
  
  生产/验收环境(104对齐):
    - 位置: 104.244.90.202（裸机 systemd）
    - 用途: 系统测试、冒烟、关键 E2E（参见 docs/TESTING.md TC-C*）
    - 约束: 发任务前检查磁盘剩余>500MB；并发业务任务≤2
    - 监控: journalctl + /health，无 Prometheus 栈
  
  生产环境:
    - 位置: 104.244.90.202:9000（主 API）
    - 用途: 部署验证、抽样回归
    - 数据: 生产数据备份；测试须避开高峰或只读账号
```

## 2. 单元测试设计（接口级别）

### 2.1 TrendAgent单元测试

#### 2.1.1 DataCollector接口测试
```python
# tests/unit/test_trend_data_collector.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.agents.trend.data_collector import DataCollector, BasePlatformCollector

class TestDataCollectorInterface:
    """DataCollector接口级别测试"""
    
    @pytest.fixture
    def data_collector(self):
        return DataCollector(config={
            "cache_ttl": 3600,
            "platforms": ["qidian", "jinjiang"]
        })
    
    @pytest.mark.asyncio
    async def test_collect_daily_data_interface(self, data_collector):
        """测试collect_daily_data接口契约"""
        # 模拟平台收集器
        mock_collector = AsyncMock(spec=BasePlatformCollector)
        mock_collector.collect.return_value = [
            {"title": "测试小说", "genre": "都市现实", "read_count": 1000}
        ]
        
        data_collector.platforms = {"test": mock_collector}
        
        # 调用接口
        result = await data_collector.collect_daily_data()
        
        # 验证接口契约
        assert isinstance(result, dict)
        assert "test" in result
        assert isinstance(result["test"], list)
        assert len(result["test"]) == 1
        
        # 验证数据格式
        novel = result["test"][0]
        assert "title" in novel
        assert "genre" in novel
        assert "read_count" in novel
        
        # 验证方法调用
        mock_collector.collect.assert_called_once_with(
            categories=["hot", "new", "rising"],
            limit_per_category=50
        )
    
    @pytest.mark.asyncio
    async def test_collect_daily_data_error_handling(self, data_collector):
        """测试错误处理接口"""

## 2.1.2 数据源管理接口测试（新增）
```python
# tests/unit/test_trend_data_source_manager.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from app.agents.trend.data_source_manager import DataSourceManager, QualityValidator

class TestDataSourceManagerInterface:
    """数据源管理器接口测试"""
    
    @pytest.fixture
    def data_source_manager(self):
        return DataSourceManager(config_path="test_config/data_sources.yaml")
    
    @pytest.mark.asyncio
    async def test_collect_data_interface(self, data_source_manager):
        """测试多数据源收集接口"""
        # 模拟数据源
        mock_source_qidian = AsyncMock()
        mock_source_qidian.collect.return_value = {
            "heat_index": 95.2,
            "reader_demographics": {"18-25": 35, "26-35": 45}
        }
        
        mock_source_jinjiang = AsyncMock()
        mock_source_jinjiang.collect.return_value = {
            "heat_index": 88.7,
            "reader_demographics": {"18-25": 40, "26-35": 40}
        }
        
        data_source_manager.sources = {
            "qidian": mock_source_qidian,
            "jinjiang": mock_source_jinjiang
        }
        
        # 调用接口
        result = await data_source_manager.collect_data(use_cache=False)
        
        # 验证接口契约
        assert isinstance(result, dict)
        required_fields = ["data", "quality_report", "source_qualities", "overall_quality", "timestamp"]
        for field in required_fields:
            assert field in result
        
        # 验证数据合并
        assert "heat_index" in result["data"]
        assert "reader_demographics" in result["data"]
        
        # 验证质量报告
        assert isinstance(result["quality_report"], dict)
        assert "overall_score" in result["quality_report"]
        
        # 验证源质量记录
        assert "qidian" in result["source_qualities"]
        assert "jinjiang" in result["source_qualities"]
    
    @pytest.mark.asyncio
    async def test_data_quality_validation_interface(self):
        """测试数据质量验证接口"""
        validator = QualityValidator()
        
        test_data = {
            "heat_index": 95.2,
            "read_count": 10000,
            "timestamp": datetime.now().isoformat(),
            "platform": "qidian"
        }
        
        # 调用接口
        validation_result = validator.validate(test_data, "qidian")
        
        # 验证接口契约
        assert isinstance(validation_result, dict)
        assert "overall_score" in validation_result
        assert "metrics" in validation_result
        assert "passed_all" in validation_result
        
        # 验证质量指标
        expected_metrics = ["completeness", "timeliness", "accuracy", "consistency", "uniqueness"]
        for metric in expected_metrics:
            assert metric in validation_result["metrics"]
            
            metric_info = validation_result["metrics"][metric]
            assert "score" in metric_info
            assert "passed" in metric_info
            assert "threshold" in metric_info
        
        # 验证分数范围
        assert 0 <= validation_result["overall_score"] <= 1
        
        # 验证阈值检查
        for metric_name, metric_info in validation_result["metrics"].items():
            if "score" in metric_info and "threshold" in metric_info:
                score = metric_info["score"]
                threshold = metric_info["threshold"]
                passed = metric_info["passed"]
                
                if score >= threshold:
                    assert passed == True
                else:
                    assert passed == False
    
    def test_similarity_calculation_interface(self):
        """测试相似度计算接口"""
        from app.agents.trend.similarity_calculator import SentenceBERTSimilarity
        
        # 使用模拟或简化版本进行测试
        calculator = SentenceBERTSimilarity(model_name="test_model")
        
        test_cases = [
            {
                "text1": "都市现实",
                "text2": "都市言情",
                "expected_high": True  # 应该相似度高
            },
            {
                "text1": "科幻未来",
                "text2": "历史军事", 
                "expected_low": True   # 应该相似度低
            },
            {
                "text1": "",
                "text2": "测试题材",
                "expected_zero": True  # 空文本应该返回0
            }
        ]
        
        for test_case in test_cases:
            similarity = calculator.calculate_similarity(
                test_case["text1"], 
                test_case["text2"],
                use_cache=False
            )
            
            # 验证接口契约
            assert isinstance(similarity, float)
            assert 0 <= similarity <= 1
            
            # 验证预期行为
            if test_case.get("expected_high"):
                assert similarity > 0.7
            elif test_case.get("expected_low"):
                assert similarity < 0.3
            elif test_case.get("expected_zero"):
                assert similarity == 0.0
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism_interface(self, data_source_manager):
        """测试降级机制接口"""
        # 模拟数据源失败
        mock_source = AsyncMock()
        mock_source.collect.side_effect = Exception("API调用失败")
        
        data_source_manager.sources = {"test_source": mock_source}
        
        # 模拟降级处理器
        with patch.object(data_source_manager.fallback_handler, 'get_fallback_data') as mock_fallback:
            mock_fallback.return_value = {
                "heat_index": 50.0,
                "is_fallback": True
            }
            
            # 调用接口
            result = await data_source_manager.collect_data(use_cache=False)
            
            # 验证降级数据被使用
            assert result["data"]["is_fallback"] == True
            assert result["data"]["heat_index"] == 50.0
            
            # 验证质量分数较低（因为是降级数据）
            assert result["source_qualities"]["test_source"] < 0.7
```

## 2.2 PlannerAgent单元测试（增强版）

### 2.2.1 差异化审核器接口测试（新增）
```python
# tests/unit/test_planner_differentiated_reviewer.py
import pytest
from unittest.mock import Mock, patch

from app.agents.planner.differentiated_reviewer import DifferentiatedReviewSystem, GenreTypeDetector

class TestDifferentiatedReviewSystemInterface:
    """差异化审核系统接口测试"""
    
    @pytest.fixture
    def review_system(self):
        return DifferentiatedReviewSystem(config_dir="test_config/differentiated")
    
    @pytest.fixture
    def test_plan_data(self):
        """创建测试策划数据"""
        return {
            "title": "测试小说",
            "structure": {
                "act1": "开端",
                "act2": "发展", 
                "act3": "高潮"
            },
            "characters": [
                {"name": "主角", "personality": "勇敢", "growth_arc": "从平凡到英雄"}
            ],
            "plot": {
                "main_conflict": "权力斗争",
                "key_events": ["相遇", "冲突", "解决"]
            }
        }
    
    def test_determine_genre_type_interface(self, review_system):
        """测试题材类型检测接口"""
        test_cases = [
            {
                "genre_info": {
                    "heat_index": 95.5,
                    "reader_maturity": 0.8,
                    "market_stability": 0.85
                },
                "expected_type": "high_quality_genre"
            },
            {
                "genre_info": {
                    "growth_rate": 0.25,
                    "market_share": 0.05,
                    "innovation_score": 0.7
                },
                "expected_type": "experimental_genre"
            },
            {
                "genre_info": {
                    "production_rate": 0.6,
                    "reader_retention": 0.7,
                    "monetization": 0.75
                },
                "expected_type": "commercial_genre"
            },
            {
                "genre_info": {
                    "critical_acclaim": 0.7,
                    "award_count": 2,
                    "depth_score": 0.8
                },
                "expected_type": "literary_genre"
            }
        ]
        
        for test_case in test_cases:
            # 模拟检测器
            with patch.object(review_system.genre_detector, 'detect') as mock_detect:
                mock_detect.return_value = test_case["expected_type"]
                
                # 调用审核
                result = review_system.review_story_plan(
                    plan_data={},
                    genre_info=test_case["genre_info"]
                )
                
                # 验证接口契约
                assert "genre_type" in result
                assert result["genre_type"] == test_case["expected_type"]
                assert "standard_applied" in result
    
    def test_apply_differentiated_standards_interface(self, review_system, test_plan_data):
        """测试差异化标准应用接口"""
        # 测试不同题材类型的审核标准差异
        
        test_scenarios = [
            {
                "genre_type": "high_quality_genre",
                "expected_threshold": 85,
                "expected_strict_dimensions": ["structure", "character"]
            },
            {
                "genre_type": "experimental_genre", 
                "expected_threshold": 70,
                "expected_innovation_weight": "high"
            },
            {
                "genre_type": "commercial_genre",
                "expected_threshold": 75,
                "expected_market_weight": "high"
            },
            {
                "genre_type": "literary_genre",
                "expected_threshold": 80,
                "expected_language_weight": "high"
            }
        ]
        
        for scenario in test_scenarios:
            # 模拟审核模型
            mock_results = {
                "structure": {"score": 80},
                "character": {"score": 85},
                "plot": {"score": 75},
                "market": {"score": 70},
                "style": {"score": 80},
                "innovation": {"score": 65}
            }
            
            with patch.object(review_system, '_calculate_dimension_scores') as mock_calc:
                with patch.object(review_system.genre_detector, 'detect') as mock_detect:
                    
                    mock_detect.return_value = scenario["genre_type"]
                    mock_calc.return_value = mock_results
                    
                    # 调用审核
                    result = review_system.review_story_plan(
                        plan_data=test_plan_data,
                        genre_info={"name": "测试题材"}
                    )
                    
                    # 验证差异化标准应用
                    assert result["total_score"] >= scenario["expected_threshold"]
                    
                    # 验证权重调整
                    if "expected_strict_dimensions" in scenario:
                        for dimension in scenario["expected_strict_dimensions"]:
                            assert dimension in result["dimension_scores"]
                            # 高质量题材的结构和人物分数应该较高
                            if scenario["genre_type"] == "high_quality_genre":
                                assert result["dimension_scores"][dimension] >= 75
    
    def test_special_rules_checking_interface(self, review_system, test_plan_data):
        """测试特殊规则检查接口"""
        # 测试不同题材类型的特殊规则
        
        test_cases = [
            {
                "genre_type": "high_quality_genre",
                "violation_scenario": {
                    "has_logic_hole": True,
                    "character_inconsistent": True
                },
                "expected_fail": True
            },
            {
                "genre_type": "experimental_genre",
                "violation_scenario": {
                    "too_innovative": False,  # 实验性题材允许创新
                    "market_risk": True       # 允许市场风险
                },
                "expected_fail": False  # 应该通过
            },
            {
                "genre_type": "commercial_genre", 
                "violation_scenario": {
                    "plot_too_slow": True,    # 商业化题材节奏不能慢
                    "formulaic": False        # 允许套路化
                },
                "expected_fail": True
            }
        ]
        
        for test_case in test_cases:
            # 模拟规则检查
            with patch.object(review_system, '_check_special_rules') as mock_check:
                with patch.object(review_system.genre_detector, 'detect') as mock_detect:
                    
                    mock_detect.return_value = test_case["genre_type"]
                    
                    if test_case["expected_fail"]:
                        # 模拟规则违规
                        mock_check.return_value = [
                            {
                                "rule": "测试规则",
                                "severity": "critical",
                                "description": "严重违规"
                            }
                        ]
                    else:
                        # 模拟无违规
                        mock_check.return_value = []
                    
                    # 调用审核
                    result = review_system.review_story_plan(
                        plan_data=test_plan_data,
                        genre_info={"name": "测试题材"}
                    )
                    
                    # 验证规则检查结果
                    if test_case["expected_fail"]:
                        assert result["passed"] == False
                        assert len(result["rule_violations"]) > 0
                        assert result["requires_revision"] == True
                    else:
                        # 如果没有严重违规，应该通过
                        assert result["passed"] == True or result["requires_revision"] == False
    
    def test_feedback_generation_interface(self, review_system, test_plan_data):
        """测试反馈生成接口"""
        # 模拟审核结果
        mock_dimension_results = {
            "structure": {
                "score": 85,
                "strengths": ["结构完整", "三幕式清晰"],
                "issues": [],
                "suggestions": []
            },
            "character": {
                "score": 60,  # 分数较低
                "strengths": ["主角鲜明"],
                "issues": ["配角单薄", "成长弧线不清晰"],
                "suggestions": ["加强配角塑造", "明确成长阶段"]
            },
            "plot": {
                "score": 75,
                "strengths": ["情节吸引人"],
                "issues": ["节奏稍快"],
                "suggestions": ["增加过渡段落"]
            }
        }
        
        with patch.object(review_system, '_calculate_dimension_scores') as mock_calc:
            with patch.object(review_system.genre_detector, 'detect') as mock_detect:
                
                mock_detect.return_value = "high_quality_genre"
                mock_calc.return_value = {k: v["score"] for k, v in mock_dimension_results.items()}
                
                # 调用审核
                result = review_system.review_story_plan(
                    plan_data=test_plan_data,
                    genre_info={"name": "都市现实"}
                )
                
                # 验证反馈接口契约
                assert "feedback" in result
                feedback = result["feedback"]
                
                required_fields = ["summary", "strengths", "weaknesses", "rule_violations"]
                for field in required_fields:
                    assert field in feedback
                
                # 验证反馈内容
                assert isinstance(feedback["strengths"], list)
                assert isinstance(feedback["weaknesses"], list)
                
                # 验证强弱项识别
                assert len(feedback["strengths"]) > 0  # 应该有强项
                assert len(feedback["weaknesses"]) > 0  # 应该有弱项
                
                # 验证具体反馈
                for strength in feedback["strengths"]:
                    assert "dimension" in strength
                    assert "score" in strength
                    assert strength["score"] >= 80  # 强项分数应该高
                
                for weakness in feedback["weaknesses"]:
                    assert "dimension" in weakness
                    assert "score" in weakness
                    assert weakness["score"] < 70  # 弱项分数应该低
                    assert "suggestions" in weakness
                    assert len(weakness["suggestions"]) > 0  # 应该有改进建议
```

### 2.2.2 监控告警系统接口测试（新增）
```python
# tests/unit/test_monitoring_alert_system.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.agents.monitor.metrics_collector import MetricsCollector
from app.agents.alert.rule_engine import AlertRuleEngine
from app.agents.alert.auto_recovery_manager import AutoRecoveryManager

class TestMonitoringAlertSystemInterface:
    """监控告警系统接口测试"""
    
    @pytest.fixture
    def metrics_collector(self):
        return MetricsCollector()
    
    @pytest.fixture
    def alert_rule_engine(self):
        return AlertRuleEngine(config_path="test_config/alert_rules.yaml")
    
    @pytest.fixture
    def sample_metrics(self):
        """创建测试指标数据"""
        return {
            "performance": {
                "batch_generation_time": 550,  # 9.17分钟（超过8分钟警告阈值）
                "memory_usage": 620,           # MB（超过
        # 模拟平台抛出异常
        mock_collector = AsyncMock(spec=BasePlatformCollector)
        mock_collector.collect.side_effect = Exception("网络错误")
        
        data_collector.platforms = {"error_platform": mock_collector}
        
        # 应该处理异常并返回降级数据
        result = await data_collector.collect_daily_data()
        
        assert "error_platform" in result
        # 验证返回了降级数据
        assert len(result["error_platform"]) > 0
    
    def test_cache_interface(self, data_collector):
        """测试缓存接口"""
        # 测试缓存设置
        cache_key = "test_key"
        cache_value = {"data": "test"}
        
        data_collector.cache.set(cache_key, cache_value)
        
        # 测试缓存获取
        retrieved = data_collector.cache.get(cache_key)
        assert retrieved == cache_value
        
        # 测试缓存过期
        with patch('time.time', return_value=time.time() + 4000):  # 超过TTL
            expired = data_collector.cache.get(cache_key)
            assert expired is None

class TestBasePlatformCollectorInterface:
    """BasePlatformCollector抽象接口测试"""
    
    def test_abstract_methods(self):
        """测试抽象接口定义"""
        # 验证抽象方法存在
        abstract_methods = BasePlatformCollector.__abstractmethods__
        
        expected_methods = {"collect", "parse_html", "extract_novel_info"}
        assert abstract_methods == expected_methods
        
        # 验证不能实例化抽象类
        with pytest.raises(TypeError):
            BasePlatformCollector()
    
    def test_concrete_implementation(self):
        """测试具体实现类接口"""
        from app.agents.trend.platforms.qidian import QidianCollector
        
        collector = QidianCollector()
        
        # 验证实现了所有抽象方法
        assert hasattr(collector, "collect")
        assert hasattr(collector, "parse_html")
        assert hasattr(collector, "extract_novel_info")
        
        # 验证具体属性
        assert hasattr(collector, "base_url")
        assert hasattr(collector, "headers")
        assert collector.base_url == "https://www.qidian.com"

class TestQidianCollectorInterface:
    """QidianCollector具体接口测试"""
    
    @pytest.fixture
    def qidian_collector(self):
        from app.agents.trend.platforms.qidian import QidianCollector
        return QidianCollector()
    
    @pytest.mark.asyncio
    async def test_collect_interface(self, qidian_collector):
        """测试collect方法接口"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '<html>测试内容</html>'
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 调用接口
            result = await qidian_collector.collect(
                categories=["hot"],
                limit_per_category=10
            )
            
            # 验证接口契约
            assert isinstance(result, list)
            assert len(result) <= 10  # 不超过限制
            
            # 验证HTTP调用
            mock_client_instance.get.assert_called()
    
    def test_parse_html_interface(self, qidian_collector):
        """测试parse_html方法接口"""
        test_html = """
        <div class="book-mid-info">
            <h4><a href="/book/101">测试小说</a></h4>
            <p class="author">作者：测试作者</p>
            <p class="intro">简介内容</p>
        </div>
        """
        
        result = qidian_collector.parse_html(test_html)
        
        # 验证接口契约
        assert isinstance(result, list)
        if result:  # 如果有解析结果
            novel_element = result[0]
            assert hasattr(novel_element, "find")  # 应该是BeautifulSoup元素
    
    def test_extract_novel_info_interface(self, qidian_collector):
        """测试extract_novel_info方法接口"""
        # 创建模拟元素
        mock_element = Mock()
        mock_element.find.return_value = Mock(text="测试小说")
        
        result = qidian_collector.extract_novel_info(mock_element)
        
        # 验证接口契约
        assert isinstance(result, dict)
        required_fields = ["title", "author", "genre", "url"]
        for field in required_fields:
            assert field in result
```

#### 2.1.2 GenreLibrary接口测试
```python
# tests/unit/test_trend_genre_library.py
import pytest
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

from app.agents.trend.genre_library import GenreLibrary

class TestGenreLibraryInterface:
    """GenreLibrary数据库接口测试"""
    
    @pytest.fixture
    def genre_library(self, tmp_path):
        """创建测试数据库"""
        db_path = tmp_path / "test_genre_library.db"
        library = GenreLibrary(db_path=str(db_path))
        library.initialize()
        return library
    
    def test_initialize_interface(self, genre_library):
        """测试初始化接口"""
        # 验证数据库文件创建
        assert Path(genre_library.db_path).exists()
        
        # 验证表结构
        conn = sqlite3.connect(genre_library.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {"genres", "genre_heat", "genre_similarity", "genre_vectors"}
        assert expected_tables.issubset(tables)
        
        conn.close()
    
    def test_add_daily_heat_data_interface(self, genre_library):
        """测试添加热度数据接口"""
        test_data = {
            "qidian": [
                {
                    "genre": "都市现实",
                    "read_count": 1000,
                    "discuss_count": 200,
                    "collect_count": 150,
                    "share_count": 50,
                    "reader_age": {"18-25": 35, "26-35": 45},
                    "reader_gender": {"male": 40, "female": 60}
                }
            ]
        }
        
        # 调用接口
        genre_library.add_daily_heat_data(test_data)
        
        # 验证数据插入
        conn = sqlite3.connect(genre_library.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM genre_heat")
        count = cursor.fetchone()[0]
        assert count == 1
        
        cursor.execute("SELECT heat_index FROM genre_heat")
        heat_index = cursor.fetchone()[0]
        assert heat_index > 0  # 应该计算了热度
        
        conn.close()
    
    def test_get_hot_genres_interface(self, genre_library):
        """测试获取热门题材接口"""
        # 先添加测试数据
        test_data = {
            "qidian": [
                {"genre": "都市现实", "read_count": 1000},
                {"genre": "玄幻奇幻", "read_count": 800}
            ]
        }
        genre_library.add_daily_heat_data(test_data)
        
        # 调用接口
        hot_genres = genre_library.get_hot_genres(days=7, limit=5)
        
        # 验证接口契约
        assert isinstance(hot_genres, list)
        assert len(hot_genres) <= 5
        
        if hot_genres:
            genre = hot_genres[0]
            required_fields = ["id", "name", "heat_index", "data_coverage"]
            for field in required_fields:
                assert field in genre
    
    def test_calculate_similarity_interface(self, genre_library):
        """测试计算相似度接口"""
        # 添加测试题材
        conn = sqlite3.connect(genre_library.db_path)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO genres (name, category) VALUES (?, ?)", 
                      ("都市现实", "都市"))
        cursor.execute("INSERT INTO genres (name, category) VALUES (?, ?)", 
                      ("都市言情", "都市"))
        conn.commit()
        conn.close()
        
        # 调用接口
        genre_library.calculate_similarity()
        
        # 验证相似度计算
        conn = sqlite3.connect(genre_library.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM genre_similarity")
        count = cursor.fetchone()[0]
        assert count > 0
        
        cursor.execute("SELECT similarity_score FROM genre_similarity")
        similarity = cursor.fetchone()[0]
        assert 0 <= similarity <= 1
        
        conn.close()
    
    def test_apply_heat_decay_interface(self, genre_library):
        """测试热度衰减接口"""
        # 添加测试数据
        conn = sqlite3.connect(genre_library.db_path)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO genres (name) VALUES (?)", ("测试题材",))
        genre_id = cursor.lastrowid
        
        # 添加7天前的热度数据
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO genre_heat 
            (genre_id, date, platform, heat_index)
            VALUES (?, ?, ?, ?)
        """, (genre_id, seven_days_ago, "qidian", 100.0))
        
        conn.commit()
        conn.close()
        
        # 调用接口
        genre_library.apply_heat_decay()
        
        # 验证热度衰减
        conn = sqlite3.connect(genre_library.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT heat_index FROM genre_heat WHERE genre_id = ?", (genre_id,))
        decayed_heat = cursor.fetchone()[0]
        
        # 7天衰减后应该小于100
        assert decayed_heat < 100.0
        # 验证指数衰减公式
        expected = 100.0 * (2.71828 ** (-0.05 * 7))
        assert abs(decayed_heat - expected) < 0.1
        
        conn.close()
```

#### 2.1.3 TrendPredictor接口测试
```python
# tests/unit/test_trend_predictor.py
import pytest
import numpy as np
from datetime import datetime, timedelta

from app.agents.trend.trend_predictor import TrendPredictor

class TestTrendPredictorInterface:
    """TrendPredictor预测接口测试"""
    
    @pytest.fixture
    def trend_predictor(self):
        return TrendPredictor()
    
    def test_analyze_trends_interface(self, trend_predictor):
        """测试趋势分析接口"""
        # 创建测试数据
        heat_data = {
            1: [
                {"date": "2026-03-01", "heat_index": 50.0},
                {"date": "2026-03-02", "heat_index": 55.0},
                {"date": "2026-03-03", "heat_index": 60.0},
                {"date": "2026-03-04", "heat_index": 65.0},
                {"date": "2026-03-05", "heat_index": 70.0},
                {"date": "2026-03-06", "heat_index": 75.0},
                {"date": "2026-03-07", "heat_index": 80.0},
            ]
        }
        
        # 调用接口
        trends = trend_predictor.analyze_trends(heat_data, window_sizes=[7])
        
        # 验证接口契约
        assert isinstance(trends, dict)
        assert "7_day" in trends
        
        trend_info = trends["7_day"]
        required_fields = ["moving_average", "growth_rate", "direction", "stability"]
        for field in required_fields:
            assert field in trend_info
        
        # 验证数据类型
        assert isinstance(trend_info["growth_rate"], float)
        assert trend_info["direction"] in ["rising", "falling", "stable"]
        assert 0 <= trend_info["stability"] <= 1
    
    def test_predict_future_trend_interface(self, trend_predictor):
        """测试未来趋势预测接口"""
        # 创建历史数据
        historical_data = [
            {"date": "2026-03-01", "heat_index": 50.0},
            {"date": "2026-03-02", "heat_index": 55.0},
            {"date": "2026-03-03", "heat_index": 60.0},
            {"date": "2026-03-04", "heat_index": 65.0},
            {"date": "2026-03-05", "heat_index": 70.0},
            {"date": "2026-03-06", "heat_index": 75.0},
            {"date": "2026-03-07", "heat_index": 80.0},
        ]
        
        # 调用接口
        predictions = trend_predictor.predict_future_trend(
            historical_data, days_ahead=3
        )
        
        # 验证接口契约
        assert isinstance(predictions, dict)
        required_fields = ["predictions", "r_squared", "trend_slope"]
        for field in required_fields:
            assert field in predictions
        
        # 验证预测结果
        assert len(predictions["predictions"]) == 3
        for pred in predictions["predictions"]:
            assert "date" in pred
            assert "predicted_heat" in pred
            assert "confidence_low" in pred
            assert "confidence_high" in pred
        
        # 验证统计指标
        assert 0 <= predictions["r_squared"] <= 1
        assert isinstance(predictions["trend_slope"], float)
    
    def test_identify_emerging_genres_interface(self, trend_predictor):
        """测试识别新兴题材接口"""
        # 创建快速增长数据
        heat_data = {
            1: [
                {"date": "2026-03-01", "heat_index": 10.0},
                {"date": "2026-03-02", "heat_index": 15.0},
                {"date": "2026-03-03", "heat_index": 22.0},
                {"date": "2026-03-04", "heat_index": 30.0},
                {"date": "2026-03-05", "heat_index": 40.0},
                {"date": "2026-03-06", "heat_index": 52.0},
                {"date": "2026-03-07", "heat_index": 65.0},
            ]
        }
        
        # 调用接口
        emerging = trend_predictor.identify_emerging_genres(
            heat_data, min_growth_rate=0.2
        )
        
        # 验证接口契约
        assert isinstance(emerging, list)
        
        if emerging:
            genre_info = emerging[0]
            required_fields = [
                "genre_id", "growth_rate", "acceleration", 
                "stability", "current_heat", "potential_score"
            ]
            for field in required_fields:
                assert field in genre_info
            
            # 验证增长率
            assert genre_info["growth_rate"] >= 0.2
            
            # 验证潜力分数
            assert 0 <= genre_info["potential_score"] <= 1
    
    def test_calculate_heat_index_interface(self, trend_predictor):
        """测试热度计算接口"""
        novel_data = {
            "read_count": 1000,
            "discuss_count": 200,
            "collect_count": 150,
            "share_count": 50
        }
        
        # 调用内部方法（测试计算公式）
        heat_index = trend_predictor._calculate_heat_index(novel_data)
        
        # 验证计算公式
        expected = 0.4*1000 + 0.3*200 + 0.2*150 + 0.1*50
        assert heat_index == expected
        
        # 测试边界条件
        empty_data = {}
        zero_heat = trend_predictor._calculate_heat_index(empty_data)
        assert zero_heat == 0.0
```

### 2.2 PlannerAgent单元测试

#### 2.2.1 ThreeChapterCycleController接口测试
```python
# tests/unit/test_planner_cycle_controller.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.agents.planner.three_chapter_cycle import ThreeChapterCycleController

class TestThreeChapterCycleControllerInterface:
    """3章周期控制器接口测试"""
    
    @pytest.fixture
    def cycle_controller(self):
        return ThreeChapterCycleController(config={
            "batch_size": 3,
            "max_retries": 3,
            "review_threshold": 80
        })
    
    @pytest.mark.asyncio
    async def test_execute_planning_interface(self, cycle_controller):
        """测试执行策划接口"""
        # 模拟依赖数据
        trend_data = {
            "hot_genres": [{"name": "都市现实", "heat_index": 95.2}],
            "chapter_recommendation": {"min": 12, "recommended": 18, "max": 30}
        }
        
        style_data = {
            "style_parameters": {"language_complexity": 7.2}
        }
        
        # 模拟内部方法
        with patch.object(cycle_controller, '_select_genres') as mock_select:
            with patch.object(cycle_controller, '_generate_story_spine') as mock_spine:
                with patch.object(cycle_controller, '_generate_batch_outlines') as mock_batch:
                    with patch.object(cycle_controller, '_deep_review_batch') as mock_review:
                        
                        # 设置模拟返回值
                        mock_select.return_value = [{"name": "都市现实"}]
                        mock_spine.return_value = {"title": "测试故事", "chapters": 6}
                        mock_batch.return_value = [
                            {"chapter": 1, "title": "第1章"},
                            {"chapter": 2, "title": "第2章"},
                            {"chapter": 3, "title": "第3章"}
                        ]
                        mock_review.return_value = {
                            "pass": True,
                            "total_score": 85,
                            "dimension_scores": {"structure": 90, "character": 85}
                        }
                        
                        # 调用接口
                        result = await cycle_controller.execute_planning(
                            total_chapters=6,
                            trend_data=trend_data,
                            style_data=style_data
                        )
        
        # 验证接口契约
        assert isinstance(result, dict)
        required_fields = [
            "story_spine", "chapter_outlines", 
            "fixed_settings", "review_history", "total_chapters"
        ]
        for field in required_fields:
            assert field in result
        
        # 验证结果数据
        assert result["total_chapters"] == 6
        assert len(result["chapter_outlines"]) == 6  # 6章大纲
        assert isinstance(result["review_history"], list)
    
    @pytest.mark.asyncio
    async def test_deep_review_batch_interface(self, cycle_controller):
        """测试深度审核批次接口"""
        # 创建测试批次数据
        batch_outlines = [
            {
                "chapter": 1,
                "title": "第1章",
                "summary": "开端",
                "key_events": ["主角出场", "冲突引入"],
                "characters": ["主角", "配角"],
                "word_target": 3000
            },
            {
                "chapter": 2,
                "title": "第2章",
                "summary": "发展",
                "key_events": ["情节推进", "悬念设置"],
                "characters": ["主角", "反派"],
                "word_target": 3200
            },
            {
                "chapter": 3,
                "title": "第3章",
                "summary": "转折",
                "key_events": ["冲突升级", "人物成长"],
                "characters": ["主角", "配角", "反派"],
                "word_target": 3500
            }
        ]
        
        # 模拟LLM调用
        with patch('app.core.llm.chat_json') as mock_llm:
            mock_llm.return_value = {
                "structure": {"score": 90, "feedback": "结构完整"},
                "character": {"score": 85, "feedback": "人物鲜明"},
                "plot": {"score": 80, "feedback": "情节合理"},
                "market": {"score": 75, "feedback": "市场匹配"},
                "style": {"score": 88, "feedback": "风格一致"},
                "feedback": "整体质量良好",
                "issues": []
            }
            
            # 调用接口
            result = await cycle_controller._deep_review_batch(
                batch_outlines, is_first_batch=True
            )
        
        # 验证接口契约
        assert isinstance(result, dict)
        required_fields = [
            "pass", "total_score", "dimension_scores",
            "llm_feedback", "specific_issues"
        ]
        for field in required_fields:
            assert field in result
        
        # 验证数据类型
        assert isinstance(result["pass"], bool)
        assert isinstance(result["total_score"], (int, float))
        assert isinstance(result["dimension_scores"], dict)
        assert isinstance(result["specific_issues"], list)
        
        # 验证分数计算
        assert 0 <= result["total_score"] <= 100
        for score in result["dimension_scores"].values():
            assert 0 <= score <= 100
    
    def test_calculate_review_scores_interface(self, cycle_controller):
        """测试审核分数计算接口"""
        # 模拟LLM响应
        llm_response = {
            "structure": {"score": 90, "feedback": "结构完整"},
            "character": {"score": 85, "feedback": "人物鲜明"},
            "plot": {"score": 80, "feedback": "情节合理"},
            "market": {"score": 75, "feedback": "市场匹配"},
            "style": {"score": 88, "feedback": "风格一致"}
        }
        
        # 调用接口
        scores = cycle_controller._calculate_review_scores(
            llm_response, is_first_batch=True
        )
        
        # 验证接口契约
        assert isinstance(scores, dict)
        expected_dimensions = ["structure", "character", "plot", "market", "style"]
        for dimension in expected_dimensions:
            assert dimension in scores
            assert 0 <= scores[dimension] <= 100
        
        # 验证首次审核权重调整
        # 首次审核结构和人物权重更高
        assert scores["structure"] >= 90 * 0.35  # 权重0.35
        assert scores["character"] >= 85 * 0.30  # 权重0.30
    
    def test_extract_fixed_settings_interface(self, cycle_controller):
        """测试提取固化设定接口"""
        batch_outlines = [
            {
                "chapter": 1,
                "title": "第1章",
                "characters": [
                    {"name": "主角", "traits": ["勇敢", "聪明"]},
                    {"name": "配角", "traits": ["忠诚", "幽默"]}
                ],
                "world_building": {
                    "time": "现代",
                    "place": "都市",
                    "rules": ["现实世界", "轻微奇幻元素"]
                },
                "core_conflict": "主角与反派的权力斗争"
            }
        ]
        
        # 调用接口
        fixed_settings = cycle_controller._extract_fixed_settings(batch_outlines)
        
        # 验证接口契约
        assert isinstance(fixed_settings, dict)
        expected_sections = [
            "characters", "world_building", "core_conflict",
            "tone", "writing_style", "chapter_length"
        ]
        
        for section in expected_sections:
            assert section in fixed_settings
        
        # 验证具体内容
        assert "主角" in [c["name"] for c in fixed_settings["characters"]]
        assert fixed_settings["world_building"]["time"] == "现代"
        assert len(fixed_settings["core_conflict"]) > 0
```

#### 2.2.2 GenreSelector接口测试
```python
# tests/unit/test_planner_genre_selector.py
import pytest
import numpy as np
from unittest.mock import Mock

from app.agents.planner.genre_selector import GenreSelector

class TestGenreSelectorInterface:
    """题材选择器接口测试"""
    
    @pytest.fixture
    def genre_selector(self):
        # 创建模拟题材库
        mock_library = Mock()
        mock_library.get_hot_genres.return_value = [
            {"id": 1, "name": "都市现实", "heat_index": 95.2, "rank": 1},
            {"id": 2, "name": "玄幻奇幻", "heat_index": 88.7, "rank": 2},
            {"id": 3, "name": "科幻未来", "heat_index": 82.3, "rank": 3},
            {"id": 4, "name": "历史军事", "heat_index": 78.5, "rank": 4},
            {"id": 5, "name": "游戏竞技", "heat_index": 75.1, "rank": 5}
        ]
        
        selector = GenreSelector(mock_library)
        selector.recent_creations = [
            {"genre": "都市现实", "time": datetime.now()},
            {"genre": "玄幻奇幻", "time": datetime.now()}
        ]
        
        return selector
    
    def test_select_genres_interface(self, genre_selector):
        """测试选择题材接口"""
        trend_data = {
            "rising_genres": ["科幻未来"],
            "declining_genres": ["历史军事"]
        }
        
        # 调用接口
        selected = genre_selector.select_genres(
            trend_data=trend_data,
            count=3,
            avoid_recent=True
        )
        
        # 验证接口契约
        assert isinstance(selected, list)
        assert len(selected) == 3
        
        # 验证选择逻辑
        selected_names = [g["name"] for g in selected]
        
        # 应该避免最近创作过的题材
        assert "都市现实" not in selected_names  # 最近创作过
        assert "玄幻奇幻" not in selected_names  # 最近创作过
        
        # 新兴题材应该有更高概率被选中
        if "科幻未来" in selected_names:
            # 验证这是合理的
            pass
    
    def test_calculate_selection_probability_interface(self, genre_selector):
        """测试计算选择概率接口"""
        test_genre = {
            "name": "科幻未来",
            "heat_index": 82.3,
            "rank": 3,
            "daily_growth": 0.25,  # 25%增长率，是新兴题材
            "days_since_update": 1
        }
        
        trend_data = {
            "rising_genres": ["科幻未来"],
            "declining_genres": []
        }
        
        # 调用接口
        probability = genre_selector._calculate_selection_probability(
            test_genre, trend_data, avoid_recent=True
        )
        
        # 验证接口契约
        assert isinstance(probability, float)
        assert probability > 0.01  # 最小概率
        
        # 验证计算因素
        # 新兴题材应该有创新系数加成
        # 最近没创作过应该有回避系数加成
    
    def test_calculate_heat_weight_interface(self, genre_selector):
        """测试计算热度权重接口"""
        test_genre = {
            "heat_index": 100.0,
            "days_since_update": 7,
            "name": "测试题材"
        }
        
        trend_data = {
            "rising_genres": ["测试题材"],
            "declining_genres": []
        }
        
        # 调用接口
        heat_weight = genre_selector._calculate_heat_weight(test_genre, trend_data)
        
        # 验证接口契约
        assert isinstance(heat_weight, float)
        assert 0 <= heat_weight <= 1
        
        # 验证热度衰减
        # 7天衰减后应该小于原始热度
        assert heat_weight < 1.0
        
        # 验证趋势调整
        # 上升趋势应该有加成
    
    def test_calculate_innovation_coefficient_interface(self, genre_selector):
        """测试计算创新系数接口"""
        test_cases = [
            {"rank": 1, "daily_growth": 0.1, "expected": 0.7},  # 热门题材
            {"rank": 15, "daily_growth": 0.25, "expected": 1.5},  # 新兴题材
            {"rank": 20, "daily_growth": 0.1, "expected": 1.0},  # 稳定题材
            {"rank": 40, "daily_growth": 0.05, "expected": 0.5},  # 冷门题材
        ]
        
        for test_case in test_cases:
            test_genre = {
                "rank": test_case["rank"],
                "daily_growth": test_case["daily_growth"]
            }
            
            coefficient = genre_selector._calculate_innovation_coefficient(test_genre)
            
            assert coefficient == test_case["expected"]
    
    def test_calculate_avoidance_coefficient_interface(self, genre_selector):
        """测试计算回避系数接口"""
        from datetime import datetime, timedelta
        
        test_cases = [
            {
                "genre_name": "都市现实",
                "days_passed": 3,  # 3天内创作过
                "expected": 0.3
            },
            {
                "genre_name": "玄幻奇幻",
                "days_passed": 15,  # 15天前创作过
                "expected": 0.7
            },
            {
                "genre_name": "科幻未来",
                "days_passed": 35,  # 35天前创作过
                "expected": 1.2
            },
            {
                "genre_name": "全新题材",
                "days_passed": None,  # 从未创作过
                "expected": 1.5
            }
        ]
        
        # 设置创作记录
        now = datetime.now()
        genre_selector.recent_creations = [
            {"genre": "都市现实", "time": now - timedelta(days=3)},
            {"genre": "玄幻奇幻", "time": now - timedelta(days=15)},
            {"genre": "科幻未来", "time": now - timedelta(days=35)}
        ]
        
        for test_case in test_cases:
            test_genre = {"name": test_case["genre_name"]}
            
            coefficient = genre_selector._calculate_avoidance_coefficient(
                test_genre, avoid_recent=True
            )
            
            assert coefficient == test_case["expected"]
```

### 2.3 WriterAgent单元测试

#### 2.3.1 BatchWritingController接口测试
```python
# tests/unit/test_writer_batch_controller.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from app.agents.writer.batch_writing_controller import BatchWritingController

class TestBatchWritingControllerInterface:
    """批次写作控制器接口测试"""
    
    @pytest.fixture
    def batch_controller(self):
        return BatchWritingController(
            batch_size=3,
            max_workers=3
        )
    
    @pytest.mark.asyncio
    async def test_write_batch_interface(self, batch_controller):
        """测试写作文本批次接口"""
        # 创建测试数据
        outlines = [
            {"chapter": 1, "title": "第1章", "summary": "开端"},
            {"chapter": 2, "title": "第2章", "summary": "发展"},
            {"chapter": 3, "title": "第3章", "summary": "转折"}
        ]
        
        previous_chapters = [
            {"chapter_number": 0, "content": "前言内容"}
        ]
        
        # 模拟内部方法
        with patch.object(batch_controller, '_generate_chapters_parallel') as mock_generate:
            with patch.object(batch_controller.consistency_checker, 'check_batch_consistency') as mock_check:
                with patch.object(batch_controller.quality_evaluator, 'evaluate_batch') as mock_evaluate:
                    
                    # 设置模拟返回值
                    mock_generate.return_value = [
                        {"chapter_number": 1, "content": "第1章内容"},
                        {"chapter_number": 2, "content": "第2章内容"},
                        {"chapter_number": 3, "content": "第3章内容"}
                    ]
                    
                    mock_check.return_value = {
                        "passed": True,
                        "pass_rate": 0.95,
                        "issues": [],
                        "total_checks": 15,
                        "passed_checks": 15
                    }
                    
                    mock_evaluate.return_value = {
                        "avg_score": 8.5,
                        "scores": [8.0, 8.5, 9.0],
                        "dimensions": {
                            "coherence": 8.7,
                            "character": 8.3,
                            "style": 8.6
                        }
                    }
                    
                    # 调用接口
                    result = await batch_controller.write_batch(
                        start_chapter=1,
                        outlines=outlines,
                        previous_chapters=previous_chapters
                    )
        
        # 验证接口契约
        assert isinstance(result, dict)
        required_fields = ["chapters", "batch_info"]
        for field in required_fields:
            assert field in result
        
        # 验证章节数据
        assert len(result["chapters"]) == 3
        for i, chapter in enumerate(result["chapters"], 1):
            assert chapter["chapter_number"] == i
            assert "content" in chapter
        
        # 验证批次信息
        batch_info = result["batch_info"]
        assert batch_info["start_chapter"] == 1
        assert batch_info["end_chapter"] == 3
        assert "generated_at" in batch_info
    
    @pytest.mark.asyncio
    async def test_generate_chapters_parallel_interface(self, batch_controller):
        """测试并行生成章节接口"""
        outlines = [
            {"chapter": 1, "title": "第1章"},
            {"chapter": 2, "title": "第2章"},
            {"chapter": 3, "title": "第3章"}
        ]
        
        # 模拟单章生成
        with patch.object(batch_controller, '_generate_single_chapter') as mock_generate:
            mock_generate.return_value = "测试章节内容"
            
            # 调用接口
            chapters = await batch_controller._generate_chapters_parallel(1, outlines)
        
        # 验证接口契约
        assert isinstance(chapters, list)
        assert len(chapters) == 3
        
        # 验证章节顺序
        for i, chapter in enumerate(chapters, 1):
            assert chapter["chapter_number"] == i
            assert chapter["content"] == "测试章节内容"
            assert chapter["outline"] == outlines[i-1]
            assert "generation_time" in chapter
    
    @pytest.mark.asyncio
    async def test_generate_chapters_timeout_handling(self, batch_controller):
        """测试生成超时处理接口"""
        outlines = [
            {"chapter": 1, "title": "第1章"},
            {"chapter": 2, "title": "第2章"},
            {"chapter": 3, "title": "第3章"}
        ]
        
        # 模拟超时
        call_count = 0
        def mock_generate_with_timeout(params):
            nonlocal call_count
            call_count += 1
            
            if call_count == 2:  # 第2章超时
                raise TimeoutError("生成超时")
            
            return f"第{params['chapter_number']}章内容"
        
        with patch.object(batch_controller, '_generate_single_chapter', side_effect=mock_generate_with_timeout):
            with patch.object(batch_controller, '_generate_fallback_content') as mock_fallback:
                mock_fallback.return_value = "降级内容"
                
                # 调用接口
                chapters = await batch_controller._generate_chapters_parallel(1, outlines)
        
        # 验证接口契约
        assert len(chapters) == 3
        
        # 验证超时处理
        for chapter in chapters:
            if chapter["chapter_number"] == 2:
                assert chapter["is_fallback"] == True
                assert chapter["content"] == "降级内容"
            else:
                assert "is_fallback" not in chapter
    
    def test_prepare_generation_params_interface(self, batch_controller):
        """测试准备生成参数接口"""
        # 模拟上下文
        with patch.object(batch_controller.context_manager, 'get_context_for_chapter') as mock_context:
            with patch.object(batch_controller.context_manager, 'get_style_parameters') as mock_style:
                with patch.object(batch_controller.context_manager, 'get_character_states') as mock_characters:
                    with patch.object(batch_controller.context_manager, 'get_plot_progress') as mock_plot:
                        
                        # 设置模拟返回值
                        mock_context.return_value = {"recent_chapters": []}
                        mock_style.return_value = {"language_complexity": 7.2}
                        mock_characters.return_value = {"主角": {"state": "正常"}}
                        mock_plot.return_value = {"main_plot": {"progress": 0.1}}
                        
                        # 调用接口
                        params = batch_controller._prepare_generation_params(
                            chapter_num=2,
                            outline={"title": "第2章", "summary": "发展"},
                            context={"previous": "第1章内容"}
                        )
        
        # 验证接口契约
        assert isinstance(params, dict)
        required_fields = [
            "chapter_number", "outline", "context",
            "style_parameters", "character_states", "plot_progress",
            "writing_guidelines"
        ]
        for field in required_fields:
            assert field in params
        
        # 验证具体值
        assert params["chapter_number"] == 2
        assert params["outline"]["title"] == "第2章"
        assert params["style_parameters"]["language_complexity"] == 7.2
```

#### 2.3.2 ContextManager接口测试
```python
# tests/unit/test_writer_context_manager.py
import pytest
from datetime import datetime

from app.agents.writer.context_manager import ContextManager

class TestContextManagerInterface:
    """上下文管理器接口测试"""
    
    @pytest.fixture
    def context_manager(self):
        return ContextManager(context_window_size=3)
    
    def test_update_context_interface(self, context_manager):
        """测试更新上下文接口"""
        # 创建测试章节
        new_chapters = [
            {
                "chapter_number": 1,
                "content": "第1章内容。主角张三出场。",
                "outline": {"title": "第1章", "summary": "开端"}
            },
            {
                "chapter_number": 2,
                "content": "第2章内容。张三遇到李四。",
                "outline": {"title": "第2章", "summary": "发展"}
            }
        ]
        
        # 调用接口
        context_manager.update_context(new_chapters)
        
        # 验证接口契约
        assert len(context_manager.recent_chapters) == 2
        assert context_manager.recent_chapters[0]["chapter_number"] == 1
        assert context_manager.recent_chapters[1]["chapter_number"] == 2
        
        # 验证人物状态更新
        assert "张三" in context_manager.character_states
        assert "李四" in context_manager.character_states
    
    def test_get_context_for_chapter_interface(self, context_manager):
        """测试获取章节上下文接口"""
        # 先设置一些上下文
        context_manager.recent_chapters = [
            {"chapter_number": 1, "content": "第1章"},
            {"chapter_number": 2, "content": "第2章"},
            {"chapter_number": 3, "content": "第3章"}
        ]
        
        context_manager.character_states = {
            "张三": {"traits": ["勇敢"], "relationships": {"李四": "朋友"}}
        }
        
        context_manager.plot_progress = {
            "main_conflict": {"progress": [{"chapter": 1, "development": "引入"}]}
        }
        
        context_manager.world_building = {"time": "现代", "place": "都市"}
        context_manager.style_parameters = {"language_complexity": 7.2}
        
        # 调用接口
        context = context_manager.get_context_for_chapter(chapter_num=4)
        
        # 验证接口契约
        assert isinstance(context, dict)
        required_fields = [
            "recent_chapters", "character_states", "plot_progress",
            "world_building", "style_parameters", "chapter_position"
        ]
        for field in required_fields:
            assert field in context
        
        # 验证具体内容
        assert len(context["recent_chapters"]) == 3  # 窗口大小
        assert "张三" in context["character_states"]
        assert context["world_building"]["time"] == "现代"
        assert context["chapter_position"] == "middle"  # 第4章在中间位置
    
    def test_update_character_states_interface(self, context_manager):
        """测试更新人物状态接口"""
        test_chapter = {
            "chapter_number": 1,
            "content": """
            张三是一个勇敢的年轻人，他站在窗前望着远方。
            "我一定要成功！"张三坚定地说。
            李四走进房间，拍了拍张三的肩膀："我相信你。"
            """
        }
        
        # 调用内部方法
        context_manager._update_character_states(test_chapter)
        
        # 验证接口契约
        assert "张三" in context_manager.character_states
        assert "李四" in context_manager.character_states
        
        # 验证人物信息
        zhang_san = context_manager.character_states["张三"]
        assert zhang_san["first_appearance"] == 1
        assert "勇敢" in zhang_san["traits"].values()
        assert len(zhang_san["development"]) == 1
        
        # 验证关系
        assert "李四" in zhang_san["relationships"]
        assert zhang_san["relationships"]["李四"] == "朋友"
    
    def test_update_plot_progress_interface(self, context_manager):
        """测试更新情节进展接口"""
        test_chapters = [
            {
                "chapter_number": 1,
                "content": "神秘事件发生，主角开始调查。"
            },
            {
                "chapter_number": 2,
                "content": "调查取得进展，发现关键线索。线索指向了嫌疑人。"
            }
        ]
        
        # 调用内部方法
        context_manager._update_plot_progress(test_chapters)
        
        # 验证接口契约
        assert len(context_manager.plot_progress) > 0
        
        # 验证情节元素
        for plot_id, plot_info in context_manager.plot_progress.items():
            assert "type" in plot_info
            assert "introduced_in" in plot_info
            assert "progress" in plot_info
            assert "status" in plot_info
            
            # 验证进展记录
            assert len(plot_info["progress"]) == 2
            for progress in plot_info["progress"]:
                assert "chapter" in progress
                assert "development" in progress
                assert "significance" in progress
```

### 2.4 AuditorAgent单元测试

#### 2.4.1 MetricsCalculator接口测试
```python
# tests/unit/test_auditor_metrics_calculator.py
import pytest

from app.agents.auditor.metrics_calculator import MetricsCalculator

class TestMetricsCalculatorInterface:
    """指标计算器接口测试"""
    
    @pytest.fixture
    def metrics_calculator(self):
        return MetricsCalculator()
    
    def test_calculate_precision_interface(self, metrics_calculator):
        """测试计算准确率接口"""
        test_cases = [
            {
                "identified": [1, 2, 3, 4],
                "actual": [1, 2, 3, 5, 6],
                "expected": 0.75  # 3/4
            },
            {
                "identified": [],
                "actual": [1, 2, 3],
                "expected": 1.0  # 没有识别问题，视为准确
            },
            {
                "identified": [1, 2],
                "actual": [],
                "expected": 0.0  # 识别了问题但实际没有问题
            }
        ]
        
        for test_case in test_cases:
            precision = metrics_calculator.calculate_precision(
                test_case["identified"],
                test_case["actual"]
            )
            
            assert precision == pytest.approx(test_case["expected"], rel=1e-3)
    
    def test_calculate_recall_interface(self, metrics_calculator):
        """测试计算召回率接口"""
        test_cases = [
            {
                "identified": [1, 2, 3],
                "actual": [1, 2, 3, 4, 5],
                "expected": 0.6  # 3/5
            },
            {
                "identified": [],
                "actual": [],
                "expected": 1.0  # 没有实际问题，视为全召回
            },
            {
                "identified": [1, 2, 3],
                "actual": [1, 2, 3],
                "expected": 1.0  # 全部召回
            }
        ]
        
        for test_case in test_cases:
            recall = metrics_calculator.calculate_recall(
                test_case["identified"],
                test_case["actual"]
            )
            
            assert recall == pytest.approx(test_case["expected"], rel=1e-3)
    
    def test_calculate_f1_interface(self, metrics_calculator):
        """测试计算F1分数接口"""
        test_cases = [
            {"precision": 0.8, "recall": 0.6, "expected": 0.6857},
            {"precision": 1.0, "recall": 1.0, "expected": 1.0},
            {"precision": 0.0, "recall": 0.0, "expected": 0.0},
            {"precision": 0.5, "recall": 0.5, "expected": 0.5}
        ]
        
        for test_case in test_cases:
            f1 = metrics_calculator.calculate_f1(
                test_case["precision"],
                test_case["recall"]
            )
            
            assert f1 == pytest.approx(test_case["expected"], rel=1e-3)
    
    def test_calculate_dimension_metrics_interface(self, metrics_calculator):
        """测试计算维度指标接口"""
        audit_results = {
            "identified_issues": [
                {"id": 1, "dimension": "plot", "description": "情节漏洞"},
                {"id": 2, "dimension": "character", "description": "人物矛盾"},
                {"id": 3, "dimension": "plot", "description": "逻辑错误"}
            ]
        }
        
        ground_truth = {
            "actual_issues": [
                {"id": 1, "dimension": "plot", "description": "情节漏洞"},
                {"id": 2, "dimension": "character", "description": "人物矛盾"},
                {"id": 4, "dimension": "plot", "description": "时间线错误"}
            ]
        }
        
        # 调用接口
        metrics = metrics_calculator.calculate_dimension_metrics(
            audit_results, "plot", ground_truth
        )
        
        # 验证接口契约
        assert isinstance(metrics, dict)
        required_fields = ["precision", "recall", "f1_score", "issue_count"]
        for field in required_fields:
            assert field in metrics
        
        # 验证计算正确性
        # 情节维度：识别了2个问题(1,3)，实际有2个问题(1,4)
        # 正确识别：问题1
        # 准确率：1/2 = 0.5
        # 召回率：1/2 = 0.5
        # F1：2*(0.5*0.5)/(0.5+0.5) = 0.5
        
        assert metrics["precision"] == 0.5
        assert metrics["recall"] == 0.5
        assert metrics["f1_score"] == 0.5
        assert metrics["issue_count"] == 2
    
    def test_calculate_overall_score_interface(self, metrics_calculator):
        """测试计算综合评分接口"""
        test_metrics = {
            "precision": 0.9,
            "recall": 0.85,
            "f1_score": 0.875,
            "plot": {"f1_score": 0.88, "issue_count": 5},
            "character": {"f1_score": 0.82, "issue_count": 3},
            "logic": {"f1_score": 0.90, "issue_count": 2},
            "style": {"f1_score": 0.78, "issue_count": 1},
            "language": {"f1_score": 0.95, "issue_count": 4}
        }
        
        # 调用接口
        overall_score = metrics_calculator.calculate_overall_score(test_metrics)
        
        # 验证接口契约
        assert isinstance(overall_score, float)
        assert 0 <= overall_score <= 100
        
        # 验证计算逻辑
        # 权重计算：
        # precision: 0.9 * 0.25 = 0.225
        # recall: 0.85 * 0.25 = 0.2125
        # f1: 0.875 * 0.20 = 0.175
        # plot: 0.88 * 0.10 = 0.088
        # character: 0.82 * 0.10 = 0.082
        # logic: 0.90 * 0.05 = 0.045
        # style: 0.78 * 0.03 = 0.0234
        # language: 0.95 * 0.02 = 0.019
        # 总和: 0.8699 * 100 = 86.99
        
        expected_score = 86.99
        assert overall_score == pytest.approx(expected_score, rel=1e-2)
    
    def test_calculate_confidence_level_interface(self, metrics_calculator):
        """测试计算置信度等级接口"""
        test_cases = [
            {
                "metrics": {"overall_score": 92, "precision": 0.96, "recall": 0.91},
                "expected": "high"
            },
            {
                "metrics": {"overall_score": 85, "precision": 0.88, "recall": 0.82},
                "expected": "medium"
            },
            {
                "metrics": {"overall_score": 65, "precision": 0.70, "recall": 0.65},
                "expected": "low"
            },
            {
                "metrics": {"overall_score": 95, "precision": 0.94, "recall": 0.89},
                "expected": "high"  # 总体分高但召回略低
            }
        ]
        
        for test_case in test_cases:
            confidence = metrics_calculator.calculate_confidence_level(test_case["metrics"])
            assert confidence == test_case["expected"]
```

#### 2.4.2 ConfidenceCalculator接口测试
```python
# tests/unit/test_auditor_confidence_calculator.py
import pytest

from app.agents.auditor.confidence_calculator import ConfidenceCalculator

class TestConfidenceCalculatorInterface:
    """置信度计算器接口测试"""
    
    @pytest.fixture
    def confidence_calculator(self):
        return ConfidenceCalculator()
    
    def test_calculate_confidence_interface(self, confidence_calculator):
        """测试计算置信度接口"""
        test_issue = {
            "id": "test_issue_1",
            "type": "plot_hole",
            "severity": "high",
            "evidence": [
                {
                    "type": "direct_text",
                    "text": "在第5章提到主角不会游泳，但在第8章却游过了河",
                    "relevance": 0.9
                },
                {
                    "type": "pattern",
                    "strength": 0.8,
                    "occurrences": 2
                }
            ]
        }
        
        test_context = {
            "chapter_count": 10,
            "previous_issues": [],
            "audit_history": {"accuracy": 0.92}
        }
        
        # 调用接口
        result = confidence_calculator.calculate_confidence(test_issue, test_context)
        
        # 验证接口契约
        assert isinstance(result, dict)
        required_fields = [
            "confidence_score", "confidence_level", 
            "factor_scores", "issue_id", "calculated_at"
        ]
        for field in required_fields:
            assert field in result
        
        # 验证数据类型
        assert 0 <= result["confidence_score"] <= 1
        assert result["confidence_level"] in ["high", "medium", "low", "very_low"]
        assert isinstance(result["factor_scores"], dict)
        assert result["issue_id"] == "test_issue_1"
    
    def test_calculate_evidence_score_interface(self, confidence_calculator):
        """测试计算证据强度接口"""
        test_cases = [
            {
                "evidence": [],
                "expected_low": True  # 无证据应该得低分
            },
            {
                "evidence": [
                    {"type": "direct_text", "text": "长文本证据", "relevance": 0.9}
                ],
                "expected_high": True  # 强证据应该得高分
            },
            {
                "evidence": [
                    {"type": "pattern", "strength": 0.6, "occurrences": 3}
                ],
                "expected_medium": True  # 中等证据
            }
        ]
        
        for test_case in test_cases:
            issue = {"evidence": test_case["evidence"]}
            score = confidence_calculator._calculate_evidence_score(issue)
            
            assert 0 <= score <= 1
            
            if test_case.get("expected_low"):
                assert score < 0.5
            elif test_case.get("expected_high"):
                assert score > 0.7
            elif test_case.get("expected_medium"):
                assert 0.4 <= score <= 0.7
    
    def test_evaluate_single_evidence_interface(self, confidence_calculator):
        """测试评估单个证据接口"""
        test_cases = [
            {
                "evidence": {
                    "type": "direct_text",
                    "text": "这是一个很长的文本证据，包含详细描述和具体引用",
                    "relevance": 0.9
                },
                "expected_high": True
            },
            {
                "evidence": {
                    "type": "pattern",
                    "strength": 0.8,
                    "occurrences": 3
                },
                "expected_high": True  # 强模式，多次出现
            },
            {
                "evidence": {
                    "type": "contradiction",
                    "source_a": {"reliability": 0.9},
                    "source_b": {"reliability": 0.8},
                    "clarity": 0.7
                },
                "expected_medium": True  # 中等置信度
            }
        ]
        
        for test_case in test_cases:
            score = confidence_calculator._evaluate_single_evidence(test_case["evidence"])
            
            assert 0 <= score <= 1
            
            if test_case.get("expected_high"):
                assert score > 0.7
            elif test_case.get("expected_medium"):
                assert 0.5 <= score <= 0.8
    
    def test_calculate_severity_score_interface(self, confidence_calculator):
        """测试计算问题严重性分数接口"""
        severity_map = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "minor": 0.2
        }
        
        for severity, expected_score in severity_map.items():
            issue = {"severity": severity}
            score = confidence_calculator._calculate_severity_score(issue)
            
            assert score == expected_score
        
        # 测试默认值
        issue_no_severity = {}
        default_score = confidence_calculator._calculate_severity_score(issue_no_severity)
        assert default_score == 0.6  # 默认中等
    
    def test_determine_confidence_level_interface(self, confidence_calculator):
        """测试确定置信度等级接口"""
        test_cases = [
            (0.95, "high"),
            (0.85, "medium"),
            (0.65, "low"),
            (0.30, "very_low"),
            (0.72, "medium"),  # 边界值
            (0.50, "low")     # 边界值
        ]
        
        for score, expected_level in test_cases:
            level = confidence_calculator._determine_confidence_level(score)
            assert level == expected_level
```

> **§2.5–§2.12 说明**：以下商业化相关单元测试均按 **§0.1** 替身策略编写——幂等与队列表用 PostgreSQL（或测试等价物），**禁止**在用例中 `import redis`、连接 RabbitMQ 或假设 Docker 网络别名。

### 2.5 套餐订阅服务单元测试

#### 2.5.1 test_create_subscription - 创建订阅
```python
# tests/unit/test_subscription_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.services.subscription import SubscriptionService, PlanType, SubscriptionStatus


class TestCreateSubscription:
    """创建订阅接口测试"""

    @pytest.fixture
    def subscription_service(self, db_session):
        return SubscriptionService(db=db_session)

    @pytest.fixture
    def mock_user(self):
        return {"user_id": "user_001", "phone": "13800138000"}

    @pytest.mark.asyncio
    async def test_create_subscription_basic(self, subscription_service, mock_user):
        """测试基础套餐订阅创建"""
        # Setup: 用户无历史订阅
        # Input
        result = await subscription_service.create_subscription(
            user_id=mock_user["user_id"],
            plan_type=PlanType.BASIC,
            duration_months=1
        )
        # Expected Output
        assert result["status"] == SubscriptionStatus.ACTIVE
        assert result["plan_type"] == PlanType.BASIC
        assert result["user_id"] == mock_user["user_id"]
        assert result["start_time"] <= datetime.utcnow()
        assert result["end_time"] > datetime.utcnow()
        assert "subscription_id" in result
        # Teardown: db_session自动回滚

    @pytest.mark.asyncio
    async def test_create_subscription_duplicate_rejected(self, subscription_service, mock_user):
        """测试重复订阅被拒绝"""
        await subscription_service.create_subscription(
            user_id=mock_user["user_id"],
            plan_type=PlanType.BASIC,
            duration_months=1
        )
        with pytest.raises(ValueError, match="已有活跃订阅"):
            await subscription_service.create_subscription(
                user_id=mock_user["user_id"],
                plan_type=PlanType.BASIC,
                duration_months=1
            )

    @pytest.mark.asyncio
    async def test_create_subscription_all_plan_types(self, subscription_service, mock_user):
        """测试所有套餐类型均可创建"""
        for plan in [PlanType.FREE, PlanType.BASIC, PlanType.PRO, PlanType.ENTERPRISE]:
            result = await subscription_service.create_subscription(
                user_id=f"user_{plan.value}",
                plan_type=plan,
                duration_months=1
            )
            assert result["plan_type"] == plan
```

#### 2.5.2 test_upgrade_subscription - 升级套餐
```python
class TestUpgradeSubscription:
    """升级套餐接口测试"""

    @pytest.fixture
    def subscription_service(self, db_session):
        return SubscriptionService(db=db_session)

    @pytest.fixture
    async def active_basic_sub(self, subscription_service):
        """Setup: 创建一个基础套餐活跃订阅"""
        return await subscription_service.create_subscription(
            user_id="user_upgrade_001",
            plan_type=PlanType.BASIC,
            duration_months=1
        )

    @pytest.mark.asyncio
    async def test_upgrade_basic_to_pro(self, subscription_service, active_basic_sub):
        """测试从基础套餐升级到专业套餐"""
        # Input
        result = await subscription_service.upgrade_subscription(
            subscription_id=active_basic_sub["subscription_id"],
            target_plan=PlanType.PRO
        )
        # Expected Output
        assert result["plan_type"] == PlanType.PRO
        assert result["status"] == SubscriptionStatus.ACTIVE
        assert result["upgrade_from"] == PlanType.BASIC
        assert result["price_diff"] > 0  # 补差价

    @pytest.mark.asyncio
    async def test_upgrade_to_same_plan_rejected(self, subscription_service, active_basic_sub):
        """测试升级到相同套餐被拒绝"""
        with pytest.raises(ValueError, match="不能升级到相同套餐"):
            await subscription_service.upgrade_subscription(
                subscription_id=active_basic_sub["subscription_id"],
                target_plan=PlanType.BASIC
            )

    @pytest.mark.asyncio
    async def test_upgrade_prorates_remaining(self, subscription_service, active_basic_sub):
        """测试升级时按比例折算剩余时长"""
        result = await subscription_service.upgrade_subscription(
            subscription_id=active_basic_sub["subscription_id"],
            target_plan=PlanType.PRO
        )
        assert "prorated_credit" in result
        assert result["prorated_credit"] >= 0
```

#### 2.5.3 test_downgrade_subscription - 降级套餐
```python
class TestDowngradeSubscription:
    """降级套餐接口测试"""

    @pytest.fixture
    async def active_pro_sub(self, subscription_service):
        return await subscription_service.create_subscription(
            user_id="user_downgrade_001",
            plan_type=PlanType.PRO,
            duration_months=1
        )

    @pytest.mark.asyncio
    async def test_downgrade_pro_to_basic(self, subscription_service, active_pro_sub):
        """测试从专业套餐降级到基础套餐（下个周期生效）"""
        # Input
        result = await subscription_service.downgrade_subscription(
            subscription_id=active_pro_sub["subscription_id"],
            target_plan=PlanType.BASIC
        )
        # Expected Output: 降级在当前周期结束后生效
        assert result["current_plan"] == PlanType.PRO
        assert result["pending_plan"] == PlanType.BASIC
        assert result["effective_date"] >= active_pro_sub["end_time"]

    @pytest.mark.asyncio
    async def test_downgrade_to_higher_plan_rejected(self, subscription_service, active_pro_sub):
        """测试降级到更高套餐被拒绝"""
        with pytest.raises(ValueError, match="目标套餐等级不低于当前"):
            await subscription_service.downgrade_subscription(
                subscription_id=active_pro_sub["subscription_id"],
                target_plan=PlanType.ENTERPRISE
            )
```

#### 2.5.4 test_check_entitlement - 权益检查
```python
class TestCheckEntitlement:
    """权益检查接口测试"""

    @pytest.mark.asyncio
    async def test_basic_plan_entitlements(self, subscription_service):
        """测试基础套餐权益"""
        sub = await subscription_service.create_subscription(
            user_id="user_ent_001", plan_type=PlanType.BASIC, duration_months=1
        )
        # Input
        entitlements = await subscription_service.check_entitlement(sub["subscription_id"])
        # Expected Output
        assert entitlements["novel_quota_per_month"] > 0
        assert entitlements["video_quota_per_month"] > 0
        assert entitlements["max_chapters"] > 0
        assert entitlements["priority"] == "normal"

    @pytest.mark.asyncio
    async def test_pro_plan_higher_entitlements(self, subscription_service):
        """测试专业套餐权益高于基础套餐"""
        basic_sub = await subscription_service.create_subscription(
            user_id="user_ent_002", plan_type=PlanType.BASIC, duration_months=1
        )
        pro_sub = await subscription_service.create_subscription(
            user_id="user_ent_003", plan_type=PlanType.PRO, duration_months=1
        )
        basic_ent = await subscription_service.check_entitlement(basic_sub["subscription_id"])
        pro_ent = await subscription_service.check_entitlement(pro_sub["subscription_id"])
        assert pro_ent["novel_quota_per_month"] > basic_ent["novel_quota_per_month"]
        assert pro_ent["video_quota_per_month"] > basic_ent["video_quota_per_month"]

    @pytest.mark.asyncio
    async def test_expired_subscription_no_entitlement(self, subscription_service):
        """测试过期订阅无权益"""
        with pytest.raises(PermissionError, match="订阅已过期"):
            await subscription_service.check_entitlement("expired_sub_id")
```

#### 2.5.5 test_quota_deduction - 配额扣减
```python
class TestQuotaDeduction:
    """配额扣减接口测试"""

    @pytest.mark.asyncio
    async def test_deduct_novel_quota(self, subscription_service):
        """测试扣减小说生成配额"""
        sub = await subscription_service.create_subscription(
            user_id="user_quota_001", plan_type=PlanType.PRO, duration_months=1
        )
        ent_before = await subscription_service.check_entitlement(sub["subscription_id"])
        # Input: 扣减1次小说配额
        result = await subscription_service.deduct_quota(
            subscription_id=sub["subscription_id"],
            resource_type="novel",
            amount=1
        )
        # Expected Output
        assert result["remaining"] == ent_before["novel_quota_per_month"] - 1
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_deduct_quota_insufficient(self, subscription_service):
        """测试配额不足时扣减失败"""
        sub = await subscription_service.create_subscription(
            user_id="user_quota_002", plan_type=PlanType.FREE, duration_months=1
        )
        with pytest.raises(ValueError, match="配额不足"):
            await subscription_service.deduct_quota(
                subscription_id=sub["subscription_id"],
                resource_type="novel",
                amount=9999
            )
```

#### 2.5.6 test_subscription_expiry - 订阅过期处理
```python
class TestSubscriptionExpiry:
    """订阅过期处理接口测试"""

    @pytest.mark.asyncio
    async def test_expire_subscription(self, subscription_service):
        """测试订阅到期自动过期"""
        # Setup: 创建一个即将过期的订阅
        sub = await subscription_service.create_subscription(
            user_id="user_exp_001", plan_type=PlanType.BASIC, duration_months=1
        )
        # 模拟时间到期
        with patch("app.services.subscription.datetime") as mock_dt:
            mock_dt.utcnow.return_value = sub["end_time"] + timedelta(hours=1)
            result = await subscription_service.process_expiry(sub["subscription_id"])
        # Expected Output
        assert result["status"] == SubscriptionStatus.EXPIRED
        assert result["grace_period_end"] is not None  # 宽限期

    @pytest.mark.asyncio
    async def test_grace_period_access(self, subscription_service):
        """测试宽限期内仍可有限访问"""
        sub = await subscription_service.create_subscription(
            user_id="user_exp_002", plan_type=PlanType.PRO, duration_months=1
        )
        with patch("app.services.subscription.datetime") as mock_dt:
            mock_dt.utcnow.return_value = sub["end_time"] + timedelta(hours=12)
            result = await subscription_service.check_access(sub["subscription_id"])
        assert result["can_read"] is True
        assert result["can_create"] is False
```

#### 2.5.7 test_auto_renew - 自动续费
```python
class TestAutoRenew:
    """自动续费接口测试"""

    @pytest.mark.asyncio
    async def test_auto_renew_success(self, subscription_service):
        """测试自动续费成功"""
        sub = await subscription_service.create_subscription(
            user_id="user_renew_001", plan_type=PlanType.BASIC, duration_months=1
        )
        await subscription_service.enable_auto_renew(sub["subscription_id"])
        # 模拟到期触发续费
        with patch.object(subscription_service, "_charge_payment", return_value=True):
            result = await subscription_service.process_auto_renew(sub["subscription_id"])
        assert result["status"] == SubscriptionStatus.ACTIVE
        assert result["renewed"] is True
        assert result["new_end_time"] > sub["end_time"]

    @pytest.mark.asyncio
    async def test_auto_renew_payment_failed(self, subscription_service):
        """测试自动续费支付失败"""
        sub = await subscription_service.create_subscription(
            user_id="user_renew_002", plan_type=PlanType.BASIC, duration_months=1
        )
        await subscription_service.enable_auto_renew(sub["subscription_id"])
        with patch.object(subscription_service, "_charge_payment", return_value=False):
            result = await subscription_service.process_auto_renew(sub["subscription_id"])
        assert result["renewed"] is False
        assert result["retry_count"] == 1
        assert result["next_retry"] is not None

    @pytest.mark.asyncio
    async def test_disable_auto_renew(self, subscription_service):
        """测试关闭自动续费"""
        sub = await subscription_service.create_subscription(
            user_id="user_renew_003", plan_type=PlanType.BASIC, duration_months=1
        )
        await subscription_service.enable_auto_renew(sub["subscription_id"])
        result = await subscription_service.disable_auto_renew(sub["subscription_id"])
        assert result["auto_renew"] is False
```

### 2.6 支付服务单元测试

#### 2.6.1 test_create_order - 创建支付订单
```python
# tests/unit/test_payment_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from app.services.payment import PaymentService, PaymentChannel, OrderStatus


class TestCreateOrder:
    """创建支付订单接口测试"""

    @pytest.fixture
    def payment_service(self, db_session):
        return PaymentService(db=db_session)

    @pytest.mark.asyncio
    async def test_create_alipay_order(self, payment_service):
        """测试创建支付宝订单"""
        # Input
        result = await payment_service.create_order(
            user_id="user_pay_001",
            amount=Decimal("29.90"),
            channel=PaymentChannel.ALIPAY,
            product_type="subscription",
            product_id="plan_basic_monthly"
        )
        # Expected Output
        assert result["order_id"] is not None
        assert result["status"] == OrderStatus.PENDING
        assert result["amount"] == Decimal("29.90")
        assert result["channel"] == PaymentChannel.ALIPAY
        assert "pay_url" in result or "pay_params" in result

    @pytest.mark.asyncio
    async def test_create_order_zero_amount_rejected(self, payment_service):
        """测试零金额订单被拒绝"""
        with pytest.raises(ValueError, match="金额必须大于0"):
            await payment_service.create_order(
                user_id="user_pay_002",
                amount=Decimal("0"),
                channel=PaymentChannel.ALIPAY,
                product_type="subscription",
                product_id="plan_basic_monthly"
            )

    @pytest.mark.asyncio
    async def test_create_order_generates_unique_id(self, payment_service):
        """测试每个订单生成唯一ID"""
        order1 = await payment_service.create_order(
            user_id="user_pay_003", amount=Decimal("29.90"),
            channel=PaymentChannel.WECHAT, product_type="subscription",
            product_id="plan_basic_monthly"
        )
        order2 = await payment_service.create_order(
            user_id="user_pay_003", amount=Decimal("29.90"),
            channel=PaymentChannel.WECHAT, product_type="recharge",
            product_id="recharge_100"
        )
        assert order1["order_id"] != order2["order_id"]
```

#### 2.6.2 test_alipay_webhook - 支付宝回调验签
```python
class TestAlipayWebhook:
    """支付宝回调验签接口测试"""

    @pytest.fixture
    def payment_service(self, db_session):
        svc = PaymentService(db=db_session)
        svc.alipay_public_key = "test_alipay_public_key"
        return svc

    @pytest.mark.asyncio
    async def test_alipay_webhook_valid_signature(self, payment_service):
        """测试合法支付宝回调验签通过"""
        # Setup: 先创建订单
        order = await payment_service.create_order(
            user_id="user_ali_001", amount=Decimal("29.90"),
            channel=PaymentChannel.ALIPAY, product_type="subscription",
            product_id="plan_basic_monthly"
        )
        # Input: 模拟支付宝回调参数
        callback_data = {
            "out_trade_no": order["order_id"],
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "29.90",
            "sign": "mock_valid_signature",
            "sign_type": "RSA2"
        }
        with patch.object(payment_service, "_verify_alipay_sign", return_value=True):
            result = await payment_service.handle_alipay_webhook(callback_data)
        # Expected Output
        assert result["success"] is True
        assert result["order_status"] == OrderStatus.PAID

    @pytest.mark.asyncio
    async def test_alipay_webhook_invalid_signature(self, payment_service):
        """测试非法签名拒绝"""
        callback_data = {
            "out_trade_no": "fake_order",
            "trade_status": "TRADE_SUCCESS",
            "sign": "invalid_signature"
        }
        with patch.object(payment_service, "_verify_alipay_sign", return_value=False):
            with pytest.raises(SecurityError, match="签名验证失败"):
                await payment_service.handle_alipay_webhook(callback_data)
```

#### 2.6.3 test_wechat_webhook - 微信支付回调验签
```python
class TestWechatWebhook:
    """微信支付回调验签接口测试"""

    @pytest.mark.asyncio
    async def test_wechat_webhook_valid(self, payment_service):
        """测试合法微信支付回调"""
        order = await payment_service.create_order(
            user_id="user_wx_001", amount=Decimal("29.90"),
            channel=PaymentChannel.WECHAT, product_type="subscription",
            product_id="plan_basic_monthly"
        )
        callback_xml = f"""
        <xml>
            <out_trade_no>{order["order_id"]}</out_trade_no>
            <result_code>SUCCESS</result_code>
            <total_fee>2990</total_fee>
        </xml>
        """
        with patch.object(payment_service, "_verify_wechat_sign", return_value=True):
            result = await payment_service.handle_wechat_webhook(callback_xml)
        assert result["success"] is True
        assert result["order_status"] == OrderStatus.PAID

    @pytest.mark.asyncio
    async def test_wechat_webhook_amount_mismatch(self, payment_service):
        """测试金额不匹配拒绝"""
        order = await payment_service.create_order(
            user_id="user_wx_002", amount=Decimal("29.90"),
            channel=PaymentChannel.WECHAT, product_type="subscription",
            product_id="plan_basic_monthly"
        )
        callback_xml = f"""
        <xml>
            <out_trade_no>{order["order_id"]}</out_trade_no>
            <result_code>SUCCESS</result_code>
            <total_fee>100</total_fee>
        </xml>
        """
        with patch.object(payment_service, "_verify_wechat_sign", return_value=True):
            with pytest.raises(ValueError, match="金额不匹配"):
                await payment_service.handle_wechat_webhook(callback_xml)
```

#### 2.6.4 test_douyin_webhook - 抖音支付回调验签
```python
class TestDouyinWebhook:
    """抖音支付回调验签接口测试"""

    @pytest.mark.asyncio
    async def test_douyin_webhook_valid(self, payment_service):
        """测试合法抖音支付回调"""
        order = await payment_service.create_order(
            user_id="user_dy_001", amount=Decimal("29.90"),
            channel=PaymentChannel.DOUYIN, product_type="subscription",
            product_id="plan_basic_monthly"
        )
        callback_data = {
            "cp_orderno": order["order_id"],
            "status": "SUCCESS",
            "total_amount": 2990,
            "sign": "mock_valid_sign"
        }
        with patch.object(payment_service, "_verify_douyin_sign", return_value=True):
            result = await payment_service.handle_douyin_webhook(callback_data)
        assert result["success"] is True
        assert result["order_status"] == OrderStatus.PAID

    @pytest.mark.asyncio
    async def test_douyin_webhook_replay_rejected(self, payment_service):
        """测试重放攻击被拒绝（时间戳过期）"""
        callback_data = {
            "cp_orderno": "order_old",
            "status": "SUCCESS",
            "timestamp": 1000000,  # 过期时间戳
            "sign": "mock_sign"
        }
        with pytest.raises(SecurityError, match="回调已过期"):
            await payment_service.handle_douyin_webhook(callback_data)
```

#### 2.6.5 test_refund_request - 退款申请
```python
class TestRefundRequest:
    """退款申请接口测试"""

    @pytest.mark.asyncio
    async def test_refund_within_policy(self, payment_service):
        """测试政策内退款成功"""
        # Setup: 创建并支付订单
        order = await payment_service.create_order(
            user_id="user_ref_001", amount=Decimal("29.90"),
            channel=PaymentChannel.ALIPAY, product_type="subscription",
            product_id="plan_basic_monthly"
        )
        await payment_service._mark_paid(order["order_id"])
        # Input
        with patch.object(payment_service, "_submit_refund_to_channel", return_value=True):
            result = await payment_service.request_refund(
                order_id=order["order_id"],
                reason="不想用了",
                amount=Decimal("29.90")
            )
        # Expected Output
        assert result["refund_status"] == "processing"
        assert result["refund_amount"] == Decimal("29.90")

    @pytest.mark.asyncio
    async def test_partial_refund(self, payment_service):
        """测试部分退款"""
        order = await payment_service.create_order(
            user_id="user_ref_002", amount=Decimal("99.00"),
            channel=PaymentChannel.WECHAT, product_type="subscription",
            product_id="plan_pro_monthly"
        )
        await payment_service._mark_paid(order["order_id"])
        with patch.object(payment_service, "_submit_refund_to_channel", return_value=True):
            result = await payment_service.request_refund(
                order_id=order["order_id"],
                reason="套餐使用不满意",
                amount=Decimal("50.00")
            )
        assert result["refund_amount"] == Decimal("50.00")
        assert result["refund_status"] == "processing"

    @pytest.mark.asyncio
    async def test_refund_exceeds_paid_rejected(self, payment_service):
        """测试退款金额超过支付金额被拒绝"""
        order = await payment_service.create_order(
            user_id="user_ref_003", amount=Decimal("29.90"),
            channel=PaymentChannel.ALIPAY, product_type="subscription",
            product_id="plan_basic_monthly"
        )
        await payment_service._mark_paid(order["order_id"])
        with pytest.raises(ValueError, match="退款金额超过支付金额"):
            await payment_service.request_refund(
                order_id=order["order_id"],
                reason="退款",
                amount=Decimal("100.00")
            )
```

#### 2.6.6 test_balance_deduction - 余额扣减（成本×1.1~1.2）
```python
class TestBalanceDeduction:
    """余额扣减接口测试（含成本加成）"""

    @pytest.mark.asyncio
    async def test_balance_deduction_with_markup(self, payment_service):
        """测试余额扣减含10%~20%成本加成"""
        # Setup: 用户充值100元
        await payment_service.recharge_balance(user_id="user_bal_001", amount=Decimal("100.00"))
        # Input: 实际成本10元，按1.15倍扣减
        result = await payment_service.deduct_balance(
            user_id="user_bal_001",
            base_cost=Decimal("10.00"),
            markup_ratio=Decimal("1.15")
        )
        # Expected Output
        assert result["deducted"] == Decimal("11.50")  # 10 * 1.15
        assert result["remaining_balance"] == Decimal("88.50")
        assert Decimal("1.1") <= result["markup_ratio"] <= Decimal("1.2")

    @pytest.mark.asyncio
    async def test_balance_deduction_insufficient(self, payment_service):
        """测试余额不足时扣减失败"""
        await payment_service.recharge_balance(user_id="user_bal_002", amount=Decimal("5.00"))
        with pytest.raises(ValueError, match="余额不足"):
            await payment_service.deduct_balance(
                user_id="user_bal_002",
                base_cost=Decimal("10.00"),
                markup_ratio=Decimal("1.15")
            )

    @pytest.mark.asyncio
    async def test_markup_ratio_boundary(self, payment_service):
        """测试成本加成比例边界值"""
        await payment_service.recharge_balance(user_id="user_bal_003", amount=Decimal("100.00"))
        # 加成比例不在1.1~1.2范围内应拒绝
        with pytest.raises(ValueError, match="加成比例超出范围"):
            await payment_service.deduct_balance(
                user_id="user_bal_003",
                base_cost=Decimal("10.00"),
                markup_ratio=Decimal("1.5")
            )
```

#### 2.6.7 test_reconciliation - 对账检查
```python
class TestReconciliation:
    """对账检查接口测试"""

    @pytest.mark.asyncio
    async def test_reconciliation_match(self, payment_service):
        """测试对账记录完全匹配"""
        # Setup: 创建并支付几个订单
        for i in range(3):
            order = await payment_service.create_order(
                user_id=f"user_recon_{i}", amount=Decimal("29.90"),
                channel=PaymentChannel.ALIPAY, product_type="subscription",
                product_id="plan_basic_monthly"
            )
            await payment_service._mark_paid(order["order_id"])
        # Input: 模拟网关对账文件
        gateway_records = [
            {"trade_no": f"gateway_{i}", "amount": "29.90", "status": "SUCCESS"}
            for i in range(3)
        ]
        with patch.object(payment_service, "_fetch_gateway_records", return_value=gateway_records):
            result = await payment_service.reconcile(date="2025-01-15")
        # Expected Output
        assert result["matched"] == 3
        assert result["mismatched"] == 0
        assert result["missing_in_local"] == 0
        assert result["missing_in_gateway"] == 0

    @pytest.mark.asyncio
    async def test_reconciliation_mismatch_detected(self, payment_service):
        """测试对账不匹配被检测到"""
        order = await payment_service.create_order(
            user_id="user_recon_err", amount=Decimal("29.90"),
            channel=PaymentChannel.ALIPAY, product_type="subscription",
            product_id="plan_basic_monthly"
        )
        await payment_service._mark_paid(order["order_id"])
        gateway_records = [
            {"trade_no": "gateway_err", "amount": "19.90", "status": "SUCCESS"}
        ]
        with patch.object(payment_service, "_fetch_gateway_records", return_value=gateway_records):
            result = await payment_service.reconcile(date="2025-01-15")
        assert result["mismatched"] >= 1
        assert len(result["mismatch_details"]) >= 1
```

### 2.7 多端认证单元测试

#### 2.7.1 test_wechat_login - 微信小程序登录（code2session）
```python
# tests/unit/test_auth_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.auth import AuthService, AuthProvider


class TestWechatLogin:
    """微信小程序登录接口测试"""

    @pytest.fixture
    def auth_service(self, db_session):
        return AuthService(db=db_session, config={
            "wechat_appid": "wx_test_appid",
            "wechat_secret": "wx_test_secret"
        })

    @pytest.mark.asyncio
    async def test_wechat_login_new_user(self, auth_service):
        """测试微信新用户首次登录自动注册"""
        # Input
        mock_response = {"openid": "wx_openid_001", "session_key": "mock_session_key"}
        with patch.object(auth_service, "_wechat_code2session", return_value=mock_response):
            result = await auth_service.wechat_login(code="mock_wx_code")
        # Expected Output
        assert result["access_token"] is not None
        assert result["user_id"] is not None
        assert result["is_new_user"] is True
        assert result["provider"] == AuthProvider.WECHAT

    @pytest.mark.asyncio
    async def test_wechat_login_existing_user(self, auth_service):
        """测试微信已注册用户登录"""
        mock_response = {"openid": "wx_openid_002", "session_key": "mock_session_key"}
        with patch.object(auth_service, "_wechat_code2session", return_value=mock_response):
            first = await auth_service.wechat_login(code="mock_code_1")
        with patch.object(auth_service, "_wechat_code2session", return_value=mock_response):
            second = await auth_service.wechat_login(code="mock_code_2")
        assert second["user_id"] == first["user_id"]
        assert second["is_new_user"] is False

    @pytest.mark.asyncio
    async def test_wechat_login_invalid_code(self, auth_service):
        """测试无效code登录失败"""
        with patch.object(auth_service, "_wechat_code2session", side_effect=Exception("invalid code")):
            with pytest.raises(ValueError, match="微信登录失败"):
                await auth_service.wechat_login(code="invalid_code")
```

#### 2.7.2 test_douyin_login - 抖音登录
```python
class TestDouyinLogin:
    """抖音登录接口测试"""

    @pytest.mark.asyncio
    async def test_douyin_login_new_user(self, auth_service):
        """测试抖音新用户登录"""
        mock_response = {"openid": "dy_openid_001", "access_token": "dy_token"}
        with patch.object(auth_service, "_douyin_code2session", return_value=mock_response):
            result = await auth_service.douyin_login(code="mock_dy_code")
        assert result["access_token"] is not None
        assert result["is_new_user"] is True
        assert result["provider"] == AuthProvider.DOUYIN

    @pytest.mark.asyncio
    async def test_douyin_login_existing_user(self, auth_service):
        """测试抖音已注册用户登录"""
        mock_response = {"openid": "dy_openid_002", "access_token": "dy_token"}
        with patch.object(auth_service, "_douyin_code2session", return_value=mock_response):
            first = await auth_service.douyin_login(code="code_1")
        with patch.object(auth_service, "_douyin_code2session", return_value=mock_response):
            second = await auth_service.douyin_login(code="code_2")
        assert second["user_id"] == first["user_id"]
```

#### 2.7.3 test_phone_login - 手机号验证码登录
```python
class TestPhoneLogin:
    """手机号验证码登录接口测试"""

    @pytest.mark.asyncio
    async def test_send_sms_code(self, auth_service):
        """测试发送短信验证码"""
        with patch.object(auth_service, "_send_sms", return_value=True):
            result = await auth_service.send_sms_code(phone="13800138000")
        assert result["sent"] is True
        assert result["expire_seconds"] == 300

    @pytest.mark.asyncio
    async def test_phone_login_valid_code(self, auth_service):
        """测试正确验证码登录成功"""
        with patch.object(auth_service, "_verify_sms_code", return_value=True):
            result = await auth_service.phone_login(phone="13800138000", code="123456")
        assert result["access_token"] is not None
        assert result["user_id"] is not None

    @pytest.mark.asyncio
    async def test_phone_login_wrong_code(self, auth_service):
        """测试错误验证码登录失败"""
        with patch.object(auth_service, "_verify_sms_code", return_value=False):
            with pytest.raises(ValueError, match="验证码错误"):
                await auth_service.phone_login(phone="13800138000", code="000000")

    @pytest.mark.asyncio
    async def test_sms_rate_limit(self, auth_service):
        """测试短信发送频率限制"""
        with patch.object(auth_service, "_send_sms", return_value=True):
            await auth_service.send_sms_code(phone="13800138001")
        with pytest.raises(ValueError, match="发送过于频繁"):
            await auth_service.send_sms_code(phone="13800138001")
```

#### 2.7.4 test_bind_account - 绑定第三方账号
```python
class TestBindAccount:
    """绑定第三方账号接口测试"""

    @pytest.mark.asyncio
    async def test_bind_wechat_to_phone_user(self, auth_service):
        """测试手机用户绑定微信账号"""
        # Setup: 手机号注册用户
        with patch.object(auth_service, "_verify_sms_code", return_value=True):
            user = await auth_service.phone_login(phone="13900139000", code="123456")
        # Input: 绑定微信
        mock_wx = {"openid": "wx_bind_001", "session_key": "key"}
        with patch.object(auth_service, "_wechat_code2session", return_value=mock_wx):
            result = await auth_service.bind_account(
                user_id=user["user_id"],
                provider=AuthProvider.WECHAT,
                code="wx_bind_code"
            )
        # Expected Output
        assert result["bound"] is True
        assert AuthProvider.WECHAT in result["linked_providers"]

    @pytest.mark.asyncio
    async def test_bind_duplicate_rejected(self, auth_service):
        """测试重复绑定同一平台被拒绝"""
        with patch.object(auth_service, "_verify_sms_code", return_value=True):
            user = await auth_service.phone_login(phone="13900139001", code="123456")
        mock_wx = {"openid": "wx_bind_002", "session_key": "key"}
        with patch.object(auth_service, "_wechat_code2session", return_value=mock_wx):
            await auth_service.bind_account(
                user_id=user["user_id"], provider=AuthProvider.WECHAT, code="code1"
            )
            with pytest.raises(ValueError, match="已绑定该平台"):
                await auth_service.bind_account(
                    user_id=user["user_id"], provider=AuthProvider.WECHAT, code="code2"
                )
```

#### 2.7.5 test_sso_token - SSO令牌生成与验证
```python
class TestSSOToken:
    """SSO令牌生成与验证接口测试"""

    @pytest.mark.asyncio
    async def test_generate_sso_token(self, auth_service):
        """测试生成SSO令牌"""
        result = await auth_service.generate_sso_token(
            user_id="user_sso_001",
            scope=["novel:read", "novel:write"]
        )
        assert result["token"] is not None
        assert result["expires_in"] > 0
        assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_verify_sso_token_valid(self, auth_service):
        """测试验证有效SSO令牌"""
        token_result = await auth_service.generate_sso_token(
            user_id="user_sso_002", scope=["novel:read"]
        )
        result = await auth_service.verify_sso_token(token_result["token"])
        assert result["valid"] is True
        assert result["user_id"] == "user_sso_002"
        assert "novel:read" in result["scope"]

    @pytest.mark.asyncio
    async def test_verify_sso_token_expired(self, auth_service):
        """测试过期SSO令牌验证失败"""
        with patch("app.services.auth.time.time", return_value=0):
            token_result = await auth_service.generate_sso_token(
                user_id="user_sso_003", scope=["novel:read"]
            )
        result = await auth_service.verify_sso_token(token_result["token"])
        assert result["valid"] is False
        assert result["reason"] == "token_expired"

    @pytest.mark.asyncio
    async def test_verify_sso_token_tampered(self, auth_service):
        """测试篡改令牌验证失败"""
        result = await auth_service.verify_sso_token("tampered.invalid.token")
        assert result["valid"] is False
        assert result["reason"] == "invalid_signature"
```

### 2.8 OpenClaw集成单元测试

#### 2.8.1 test_api_key_auth - API Key认证
```python
# tests/unit/test_openclaw_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.openclaw import OpenClawService, TaskStatus


class TestAPIKeyAuth:
    """OpenClaw API Key认证接口测试"""

    @pytest.fixture
    def openclaw_service(self, db_session):
        return OpenClawService(db=db_session)

    @pytest.mark.asyncio
    async def test_valid_api_key(self, openclaw_service):
        """测试有效API Key认证通过"""
        # Setup: 创建API Key
        key_info = await openclaw_service.create_api_key(
            user_id="user_oc_001", name="test_key"
        )
        # Input
        result = await openclaw_service.authenticate(api_key=key_info["api_key"])
        # Expected Output
        assert result["authenticated"] is True
        assert result["user_id"] == "user_oc_001"
        assert result["key_name"] == "test_key"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, openclaw_service):
        """测试无效API Key认证失败"""
        result = await openclaw_service.authenticate(api_key="invalid_key_12345")
        assert result["authenticated"] is False

    @pytest.mark.asyncio
    async def test_revoked_api_key(self, openclaw_service):
        """测试已吊销API Key认证失败"""
        key_info = await openclaw_service.create_api_key(
            user_id="user_oc_002", name="revoked_key"
        )
        await openclaw_service.revoke_api_key(key_info["api_key"])
        result = await openclaw_service.authenticate(api_key=key_info["api_key"])
        assert result["authenticated"] is False

    @pytest.mark.asyncio
    async def test_api_key_rate_limit(self, openclaw_service):
        """测试API Key请求频率限制"""
        key_info = await openclaw_service.create_api_key(
            user_id="user_oc_003", name="rate_test"
        )
        for _ in range(100):
            await openclaw_service.authenticate(api_key=key_info["api_key"])
        with pytest.raises(ValueError, match="请求频率超限"):
            await openclaw_service.authenticate(api_key=key_info["api_key"])
```

#### 2.8.2 test_create_task - 创建任务
```python
class TestCreateTask:
    """OpenClaw创建任务接口测试"""

    @pytest.mark.asyncio
    async def test_create_novel_task(self, openclaw_service):
        """测试通过API创建小说生成任务"""
        result = await openclaw_service.create_task(
            user_id="user_oc_task_001",
            task_type="novel_generation",
            params={
                "genre": "都市现实",
                "chapters": 18,
                "style": "轻松幽默"
            }
        )
        assert result["task_id"] is not None
        assert result["status"] == TaskStatus.QUEUED
        assert result["estimated_time_seconds"] > 0

    @pytest.mark.asyncio
    async def test_create_task_quota_check(self, openclaw_service):
        """测试创建任务时检查配额"""
        with patch.object(openclaw_service, "_check_quota", return_value=False):
            with pytest.raises(ValueError, match="配额不足"):
                await openclaw_service.create_task(
                    user_id="user_oc_task_002",
                    task_type="novel_generation",
                    params={"genre": "科幻", "chapters": 18}
                )

    @pytest.mark.asyncio
    async def test_create_task_invalid_params(self, openclaw_service):
        """测试无效参数被拒绝"""
        with pytest.raises(ValueError, match="参数校验失败"):
            await openclaw_service.create_task(
                user_id="user_oc_task_003",
                task_type="novel_generation",
                params={"chapters": -1}  # 无效章节数
            )
```

#### 2.8.3 test_task_progress - 任务进度查询
```python
class TestTaskProgress:
    """任务进度查询接口测试"""

    @pytest.mark.asyncio
    async def test_query_task_progress(self, openclaw_service):
        """测试查询任务进度"""
        task = await openclaw_service.create_task(
            user_id="user_oc_prog_001",
            task_type="novel_generation",
            params={"genre": "都市", "chapters": 6}
        )
        result = await openclaw_service.get_task_progress(task["task_id"])
        assert "progress_percent" in result
        assert 0 <= result["progress_percent"] <= 100
        assert result["status"] in [s.value for s in TaskStatus]
        assert "current_step" in result

    @pytest.mark.asyncio
    async def test_query_nonexistent_task(self, openclaw_service):
        """测试查询不存在的任务返回404"""
        with pytest.raises(FileNotFoundError, match="任务不存在"):
            await openclaw_service.get_task_progress("nonexistent_task_id")
```

#### 2.8.4 test_balance_query - 余额查询
```python
class TestBalanceQuery:
    """OpenClaw余额查询接口测试"""

    @pytest.mark.asyncio
    async def test_query_balance(self, openclaw_service):
        """测试查询用户余额"""
        result = await openclaw_service.get_balance(user_id="user_oc_bal_001")
        assert "balance" in result
        assert "currency" in result
        assert result["balance"] >= 0

    @pytest.mark.asyncio
    async def test_query_balance_with_usage(self, openclaw_service):
        """测试余额查询包含使用统计"""
        result = await openclaw_service.get_balance(
            user_id="user_oc_bal_002", include_usage=True
        )
        assert "usage_this_month" in result
        assert "total_spent" in result
```

#### 2.8.5 test_config_sync - 配置同步
```python
class TestConfigSync:
    """配置同步接口测试"""

    @pytest.mark.asyncio
    async def test_sync_config_to_remote(self, openclaw_service):
        """测试配置同步到远程"""
        config = {
            "default_model": "deepseek-v3",
            "max_chapters": 18,
            "batch_size": 3,
            "tts_voice": "fish_audio_default"
        }
        result = await openclaw_service.sync_config(
            user_id="user_oc_cfg_001", config=config, direction="push"
        )
        assert result["synced"] is True
        assert result["version"] > 0

    @pytest.mark.asyncio
    async def test_sync_config_from_remote(self, openclaw_service):
        """测试从远程拉取配置"""
        config = {"default_model": "deepseek-v3", "max_chapters": 18}
        await openclaw_service.sync_config(
            user_id="user_oc_cfg_002", config=config, direction="push"
        )
        result = await openclaw_service.sync_config(
            user_id="user_oc_cfg_002", config=None, direction="pull"
        )
        assert result["config"]["default_model"] == "deepseek-v3"

    @pytest.mark.asyncio
    async def test_config_conflict_resolution(self, openclaw_service):
        """测试配置冲突解决（远程版本更新）"""
        result = await openclaw_service.sync_config(
            user_id="user_oc_cfg_003",
            config={"max_chapters": 24},
            direction="push",
            expected_version=1  # 本地版本号
        )
        if result.get("conflict"):
            assert result["resolution"] in ["local_wins", "remote_wins", "merged"]
```

### 2.9 多平台发布单元测试

#### 2.9.1 test_platform_adapter - 平台适配器
```python
# tests/unit/test_publish_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.publish import PublishService, PlatformAdapter, PlatformType


class TestPlatformAdapter:
    """平台适配器接口测试"""

    @pytest.fixture
    def publish_service(self, db_session):
        return PublishService(db=db_session)

    @pytest.mark.asyncio
    async def test_douyin_adapter_format(self, publish_service):
        """测试抖音平台适配器内容格式化"""
        adapter = publish_service.get_adapter(PlatformType.DOUYIN)
        content = {
            "title": "测试视频标题",
            "video_path": "/tmp/test.mp4",
            "description": "测试描述",
            "tags": ["AI小说", "都市"]
        }
        # Expected Output: 符合抖音API要求的格式
        formatted = await adapter.format_content(content)
        assert "title" in formatted
        assert len(formatted["title"]) <= 55  # 抖音标题限制
        assert "video" in formatted
        assert "poi_id" not in formatted or formatted["poi_id"] is None

    @pytest.mark.asyncio
    async def test_xiaohongshu_adapter_format(self, publish_service):
        """测试小红书平台适配器内容格式化"""
        adapter = publish_service.get_adapter(PlatformType.XIAOHONGSHU)
        content = {
            "title": "测试笔记标题",
            "images": ["/tmp/cover.jpg"],
            "description": "测试内容描述",
            "tags": ["AI写作", "小说"]
        }
        formatted = await adapter.format_content(content)
        assert "title" in formatted
        assert "images" in formatted
        assert len(formatted["tags"]) <= 10  # 小红书标签数限制

    @pytest.mark.asyncio
    async def test_fanqie_adapter_format(self, publish_service):
        """测试番茄小说平台适配器内容格式化"""
        adapter = publish_service.get_adapter(PlatformType.FANQIE)
        content = {
            "novel_title": "都市之巅",
            "chapters": [{"title": "第一章", "content": "正文..."}],
            "genre": "都市现实",
            "synopsis": "简介..."
        }
        formatted = await adapter.format_content(content)
        assert "book_name" in formatted
        assert "category" in formatted
        assert "chapters" in formatted

    @pytest.mark.asyncio
    async def test_unsupported_platform(self, publish_service):
        """测试不支持的平台返回错误"""
        with pytest.raises(ValueError, match="不支持的平台"):
            publish_service.get_adapter("unsupported_platform")
```

#### 2.9.2 test_oauth_bind - OAuth账号绑定
```python
class TestOAuthBind:
    """OAuth账号绑定接口测试"""

    @pytest.mark.asyncio
    async def test_bind_douyin_creator(self, publish_service):
        """测试绑定抖音创作者账号"""
        with patch.object(publish_service, "_exchange_oauth_token", return_value={
            "access_token": "dy_access_token",
            "refresh_token": "dy_refresh_token",
            "expires_in": 86400,
            "open_id": "dy_creator_001"
        }):
            result = await publish_service.bind_platform_account(
                user_id="user_pub_001",
                platform=PlatformType.DOUYIN,
                oauth_code="mock_oauth_code"
            )
        assert result["bound"] is True
        assert result["platform"] == PlatformType.DOUYIN
        assert result["platform_user_id"] == "dy_creator_001"

    @pytest.mark.asyncio
    async def test_refresh_expired_token(self, publish_service):
        """测试刷新过期OAuth令牌"""
        with patch.object(publish_service, "_refresh_oauth_token", return_value={
            "access_token": "new_token",
            "expires_in": 86400
        }):
            result = await publish_service.refresh_platform_token(
                user_id="user_pub_002", platform=PlatformType.DOUYIN
            )
        assert result["refreshed"] is True
        assert result["new_expires_in"] == 86400
```

#### 2.9.3 test_smart_schedule - 智能排期
```python
class TestSmartSchedule:
    """智能排期接口测试"""

    @pytest.mark.asyncio
    async def test_generate_schedule(self, publish_service):
        """测试生成智能发布排期"""
        result = await publish_service.generate_schedule(
            user_id="user_sch_001",
            content_count=7,
            platforms=[PlatformType.DOUYIN, PlatformType.XIAOHONGSHU],
            preferences={"peak_hours": True, "avoid_weekends": False}
        )
        assert len(result["schedule"]) == 7
        for item in result["schedule"]:
            assert "publish_time" in item
            assert "platform" in item
            assert item["platform"] in [PlatformType.DOUYIN, PlatformType.XIAOHONGSHU]

    @pytest.mark.asyncio
    async def test_schedule_respects_platform_limits(self, publish_service):
        """测试排期遵守平台发布频率限制"""
        result = await publish_service.generate_schedule(
            user_id="user_sch_002",
            content_count=20,
            platforms=[PlatformType.DOUYIN],
            preferences={}
        )
        from collections import Counter
        daily_counts = Counter()
        for item in result["schedule"]:
            day = item["publish_time"].date()
            daily_counts[day] += 1
        for day, count in daily_counts.items():
            assert count <= 5  # 抖音每日发布上限

    @pytest.mark.asyncio
    async def test_schedule_peak_hours(self, publish_service):
        """测试高峰时段优先排期"""
        result = await publish_service.generate_schedule(
            user_id="user_sch_003",
            content_count=3,
            platforms=[PlatformType.DOUYIN],
            preferences={"peak_hours": True}
        )
        peak_hours = {11, 12, 18, 19, 20, 21}
        for item in result["schedule"]:
            assert item["publish_time"].hour in peak_hours
```

#### 2.9.4 test_compliance_check - 合规预检
```python
class TestComplianceCheck:
    """合规预检接口测试"""

    @pytest.mark.asyncio
    async def test_content_passes_compliance(self, publish_service):
        """测试正常内容通过合规检查"""
        result = await publish_service.check_compliance(
            content={"title": "美好的一天", "text": "阳光明媚，春暖花开"},
            platform=PlatformType.DOUYIN
        )
        assert result["passed"] is True
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_content_fails_compliance(self, publish_service):
        """测试违规内容被拦截"""
        with patch.object(publish_service, "_run_content_filter", return_value={
            "safe": False, "categories": ["political_sensitive"]
        }):
            result = await publish_service.check_compliance(
                content={"title": "敏感标题", "text": "敏感内容..."},
                platform=PlatformType.DOUYIN
            )
        assert result["passed"] is False
        assert len(result["violations"]) > 0

    @pytest.mark.asyncio
    async def test_platform_specific_rules(self, publish_service):
        """测试平台特定合规规则"""
        content = {"title": "A" * 100, "text": "正常内容"}
        result_dy = await publish_service.check_compliance(
            content=content, platform=PlatformType.DOUYIN
        )
        # 抖音标题超长应报警告
        assert any(v["type"] == "title_too_long" for v in result_dy.get("warnings", []))
```

#### 2.9.5 test_publish_status_track - 发布状态跟踪
```python
class TestPublishStatusTrack:
    """发布状态跟踪接口测试"""

    @pytest.mark.asyncio
    async def test_track_publish_status(self, publish_service):
        """测试跟踪发布状态"""
        # Setup: 模拟已提交发布
        publish_id = "pub_track_001"
        with patch.object(publish_service, "_query_platform_status", return_value={
            "status": "published", "url": "https://douyin.com/video/123"
        }):
            result = await publish_service.get_publish_status(publish_id)
        assert result["status"] in ["pending", "processing", "published", "failed", "rejected"]

    @pytest.mark.asyncio
    async def test_track_multi_platform_status(self, publish_service):
        """测试多平台发布状态聚合"""
        batch_id = "batch_001"
        result = await publish_service.get_batch_status(batch_id)
        assert "platforms" in result
        for platform_status in result["platforms"]:
            assert "platform" in platform_status
            assert "status" in platform_status

    @pytest.mark.asyncio
    async def test_publish_retry_on_failure(self, publish_service):
        """测试发布失败后重试"""
        publish_id = "pub_retry_001"
        with patch.object(publish_service, "_submit_to_platform", side_effect=[
            Exception("网络超时"), {"status": "published"}
        ]):
            result = await publish_service.retry_publish(publish_id, max_retries=2)
        assert result["status"] == "published"
        assert result["retry_count"] == 1
```

### 2.10 视频评审单元测试

#### 2.10.1 test_auto_review - 自动评审
```python
# tests/unit/test_review_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.review import ReviewService, ReviewResult, ReviewLevel


class TestAutoReview:
    """自动评审接口测试"""

    @pytest.fixture
    def review_service(self, db_session):
        return ReviewService(db=db_session)

    @pytest.mark.asyncio
    async def test_auto_review_pass(self, review_service):
        """测试视频自动评审通过"""
        # Input
        result = await review_service.auto_review(
            video_id="video_001",
            video_path="/tmp/test_video.mp4",
            metadata={"duration": 60, "resolution": "1080p", "fps": 30}
        )
        # Expected Output
        assert result["level"] == ReviewLevel.AUTO
        assert result["passed"] is True
        assert result["score"] >= 0.7
        assert "checks" in result
        assert "duration_valid" in result["checks"]
        assert "resolution_valid" in result["checks"]

    @pytest.mark.asyncio
    async def test_auto_review_fail_duration(self, review_service):
        """测试时长不合规自动拒绝"""
        result = await review_service.auto_review(
            video_id="video_002",
            video_path="/tmp/short_video.mp4",
            metadata={"duration": 2, "resolution": "1080p", "fps": 30}
        )
        assert result["passed"] is False
        assert "duration_valid" in result["checks"]
        assert result["checks"]["duration_valid"] is False

    @pytest.mark.asyncio
    async def test_auto_review_borderline_escalates(self, review_service):
        """测试边界分数自动升级到AI评审"""
        with patch.object(review_service, "_compute_auto_score", return_value=0.65):
            result = await review_service.auto_review(
                video_id="video_003",
                video_path="/tmp/borderline.mp4",
                metadata={"duration": 30, "resolution": "720p", "fps": 24}
            )
        assert result["escalated"] is True
        assert result["next_level"] == ReviewLevel.AI
```

#### 2.10.2 test_ai_review - AI深度评审
```python
class TestAIReview:
    """AI深度评审接口测试"""

    @pytest.mark.asyncio
    async def test_ai_review_comprehensive(self, review_service):
        """测试AI综合评审"""
        with patch.object(review_service, "_call_ai_model", return_value={
            "story_coherence": 0.85,
            "visual_quality": 0.80,
            "audio_quality": 0.90,
            "pacing": 0.75,
            "overall": 0.82
        }):
            result = await review_service.ai_review(
                video_id="video_ai_001",
                video_path="/tmp/ai_review.mp4"
            )
        assert result["level"] == ReviewLevel.AI
        assert "story_coherence" in result["scores"]
        assert "visual_quality" in result["scores"]
        assert result["overall_score"] > 0
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_ai_review_low_score_escalates(self, review_service):
        """测试AI评审低分升级到人工评审"""
        with patch.object(review_service, "_call_ai_model", return_value={
            "story_coherence": 0.40,
            "visual_quality": 0.50,
            "audio_quality": 0.45,
            "pacing": 0.35,
            "overall": 0.42
        }):
            result = await review_service.ai_review(
                video_id="video_ai_002", video_path="/tmp/low_score.mp4"
            )
        assert result["escalated"] is True
        assert result["next_level"] == ReviewLevel.HUMAN
```

#### 2.10.3 test_human_review - 人工评审流程
```python
class TestHumanReview:
    """人工评审流程接口测试"""

    @pytest.mark.asyncio
    async def test_assign_human_reviewer(self, review_service):
        """测试分配人工审核员"""
        result = await review_service.assign_reviewer(
            video_id="video_hr_001", reviewer_pool=["reviewer_a", "reviewer_b"]
        )
        assert result["assigned_to"] in ["reviewer_a", "reviewer_b"]
        assert result["deadline"] is not None

    @pytest.mark.asyncio
    async def test_submit_human_review(self, review_service):
        """测试提交人工评审结果"""
        result = await review_service.submit_human_review(
            video_id="video_hr_002",
            reviewer_id="reviewer_a",
            decision="approved",
            comments="质量良好，可以发布",
            scores={"story": 4, "visual": 5, "audio": 4}
        )
        assert result["level"] == ReviewLevel.HUMAN
        assert result["decision"] == "approved"
        assert result["reviewer_id"] == "reviewer_a"

    @pytest.mark.asyncio
    async def test_human_review_reject_with_reason(self, review_service):
        """测试人工评审拒绝并附原因"""
        result = await review_service.submit_human_review(
            video_id="video_hr_003",
            reviewer_id="reviewer_b",
            decision="rejected",
            comments="画面质量太差，需要重新生成",
            scores={"story": 3, "visual": 1, "audio": 2}
        )
        assert result["decision"] == "rejected"
        assert result["revision_required"] is True
```

#### 2.10.4 test_memory_point_detect - 记忆点检测
```python
class TestMemoryPointDetect:
    """记忆点检测接口测试"""

    @pytest.mark.asyncio
    async def test_detect_memory_points(self, review_service):
        """测试检测视频记忆点"""
        with patch.object(review_service, "_analyze_engagement", return_value=[
            {"timestamp": 5.0, "type": "hook", "strength": 0.9},
            {"timestamp": 30.0, "type": "climax", "strength": 0.85},
            {"timestamp": 55.0, "type": "cliffhanger", "strength": 0.8}
        ]):
            result = await review_service.detect_memory_points(
                video_id="video_mp_001", video_path="/tmp/memory_test.mp4"
            )
        assert len(result["memory_points"]) >= 1
        for point in result["memory_points"]:
            assert "timestamp" in point
            assert "type" in point
            assert "strength" in point
            assert point["strength"] >= 0.0

    @pytest.mark.asyncio
    async def test_no_memory_points(self, review_service):
        """测试无记忆点视频标记为低吸引力"""
        with patch.object(review_service, "_analyze_engagement", return_value=[]):
            result = await review_service.detect_memory_points(
                video_id="video_mp_002", video_path="/tmp/boring.mp4"
            )
        assert len(result["memory_points"]) == 0
        assert result["engagement_risk"] == "high"
```

#### 2.10.5 test_opening_quality - 开头质量评分
```python
class TestOpeningQuality:
    """开头质量评分接口测试"""

    @pytest.mark.asyncio
    async def test_opening_quality_score(self, review_service):
        """测试开头质量评分"""
        with patch.object(review_service, "_analyze_opening", return_value={
            "hook_score": 0.85,
            "first_3s_retention": 0.92,
            "visual_impact": 0.80,
            "audio_impact": 0.75
        }):
            result = await review_service.evaluate_opening(
                video_id="video_op_001", video_path="/tmp/opening_test.mp4"
            )
        assert "hook_score" in result
        assert "first_3s_retention" in result
        assert result["overall_opening_score"] > 0
        assert "recommendation" in result

    @pytest.mark.asyncio
    async def test_weak_opening_flagged(self, review_service):
        """测试弱开头被标记"""
        with patch.object(review_service, "_analyze_opening", return_value={
            "hook_score": 0.3,
            "first_3s_retention": 0.4,
            "visual_impact": 0.35,
            "audio_impact": 0.30
        }):
            result = await review_service.evaluate_opening(
                video_id="video_op_002", video_path="/tmp/weak_opening.mp4"
            )
        assert result["overall_opening_score"] < 0.5
        assert result["needs_improvement"] is True
        assert "recommendation" in result
```

### 2.11 内容广场单元测试

#### 2.11.1 test_publish_to_square - 发布到广场
```python
# tests/unit/test_square_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.square import SquareService, ContentType, ContentStatus


class TestPublishToSquare:
    """发布到内容广场接口测试"""

    @pytest.fixture
    def square_service(self, db_session):
        return SquareService(db=db_session)

    @pytest.mark.asyncio
    async def test_publish_novel_to_square(self, square_service):
        """测试发布小说到内容广场"""
        result = await square_service.publish(
            user_id="user_sq_001",
            content_type=ContentType.NOVEL,
            content_id="novel_001",
            title="都市传奇",
            description="一个关于都市的传奇故事",
            tags=["都市", "传奇"]
        )
        assert result["square_id"] is not None
        assert result["status"] == ContentStatus.PUBLISHED
        assert result["content_type"] == ContentType.NOVEL

    @pytest.mark.asyncio
    async def test_publish_video_to_square(self, square_service):
        """测试发布视频到内容广场"""
        result = await square_service.publish(
            user_id="user_sq_002",
            content_type=ContentType.VIDEO,
            content_id="video_001",
            title="AI生成短视频",
            description="由AI自动生成的短视频",
            tags=["AI", "短视频"],
            cover_url="https://example.com/cover.jpg"
        )
        assert result["square_id"] is not None
        assert result["content_type"] == ContentType.VIDEO

    @pytest.mark.asyncio
    async def test_publish_duplicate_rejected(self, square_service):
        """测试重复发布被拒绝"""
        await square_service.publish(
            user_id="user_sq_003", content_type=ContentType.NOVEL,
            content_id="novel_dup", title="重复测试", description="",  tags=[]
        )
        with pytest.raises(ValueError, match="内容已发布"):
            await square_service.publish(
                user_id="user_sq_003", content_type=ContentType.NOVEL,
                content_id="novel_dup", title="重复测试", description="", tags=[]
            )
```

#### 2.11.2 test_interaction - 点赞/收藏/评论
```python
class TestInteraction:
    """内容广场交互接口测试"""

    @pytest.mark.asyncio
    async def test_like_content(self, square_service):
        """测试点赞内容"""
        pub = await square_service.publish(
            user_id="user_int_001", content_type=ContentType.NOVEL,
            content_id="novel_like", title="测试", description="", tags=[]
        )
        result = await square_service.like(
            user_id="user_int_002", square_id=pub["square_id"]
        )
        assert result["liked"] is True
        assert result["like_count"] == 1

    @pytest.mark.asyncio
    async def test_unlike_content(self, square_service):
        """测试取消点赞"""
        pub = await square_service.publish(
            user_id="user_int_003", content_type=ContentType.NOVEL,
            content_id="novel_unlike", title="测试", description="", tags=[]
        )
        await square_service.like(user_id="user_int_004", square_id=pub["square_id"])
        result = await square_service.unlike(user_id="user_int_004", square_id=pub["square_id"])
        assert result["liked"] is False
        assert result["like_count"] == 0

    @pytest.mark.asyncio
    async def test_favorite_content(self, square_service):
        """测试收藏内容"""
        pub = await square_service.publish(
            user_id="user_int_005", content_type=ContentType.NOVEL,
            content_id="novel_fav", title="测试", description="", tags=[]
        )
        result = await square_service.favorite(
            user_id="user_int_006", square_id=pub["square_id"]
        )
        assert result["favorited"] is True
        assert result["favorite_count"] == 1

    @pytest.mark.asyncio
    async def test_comment_content(self, square_service):
        """测试评论内容"""
        pub = await square_service.publish(
            user_id="user_int_007", content_type=ContentType.NOVEL,
            content_id="novel_comment", title="测试", description="", tags=[]
        )
        result = await square_service.comment(
            user_id="user_int_008",
            square_id=pub["square_id"],
            text="写得真好！"
        )
        assert result["comment_id"] is not None
        assert result["text"] == "写得真好！"
        assert result["comment_count"] == 1

    @pytest.mark.asyncio
    async def test_self_like_rejected(self, square_service):
        """测试自己不能给自己点赞"""
        pub = await square_service.publish(
            user_id="user_int_009", content_type=ContentType.NOVEL,
            content_id="novel_self", title="测试", description="", tags=[]
        )
        with pytest.raises(ValueError, match="不能给自己的内容点赞"):
            await square_service.like(user_id="user_int_009", square_id=pub["square_id"])
```

#### 2.11.3 test_report - 举报处理
```python
class TestReport:
    """举报处理接口测试"""

    @pytest.mark.asyncio
    async def test_report_content(self, square_service):
        """测试举报违规内容"""
        pub = await square_service.publish(
            user_id="user_rpt_001", content_type=ContentType.NOVEL,
            content_id="novel_report", title="测试", description="", tags=[]
        )
        result = await square_service.report(
            reporter_id="user_rpt_002",
            square_id=pub["square_id"],
            reason="涉嫌抄袭",
            category="plagiarism"
        )
        assert result["report_id"] is not None
        assert result["status"] == "pending_review"

    @pytest.mark.asyncio
    async def test_report_threshold_auto_hide(self, square_service):
        """测试举报达到阈值自动隐藏"""
        pub = await square_service.publish(
            user_id="user_rpt_003", content_type=ContentType.NOVEL,
            content_id="novel_hide", title="测试", description="", tags=[]
        )
        for i in range(5):
            await square_service.report(
                reporter_id=f"reporter_{i}",
                square_id=pub["square_id"],
                reason="违规内容", category="inappropriate"
            )
        status = await square_service.get_content_status(pub["square_id"])
        assert status["visible"] is False
        assert status["reason"] == "auto_hidden_by_reports"

    @pytest.mark.asyncio
    async def test_duplicate_report_rejected(self, square_service):
        """测试同一用户重复举报被拒绝"""
        pub = await square_service.publish(
            user_id="user_rpt_004", content_type=ContentType.NOVEL,
            content_id="novel_dup_rpt", title="测试", description="", tags=[]
        )
        await square_service.report(
            reporter_id="reporter_dup", square_id=pub["square_id"],
            reason="违规", category="inappropriate"
        )
        with pytest.raises(ValueError, match="已举报过该内容"):
            await square_service.report(
                reporter_id="reporter_dup", square_id=pub["square_id"],
                reason="再次举报", category="inappropriate"
            )
```

#### 2.11.4 test_ranking - 排行榜计算
```python
class TestRanking:
    """排行榜计算接口测试"""

    @pytest.mark.asyncio
    async def test_daily_ranking(self, square_service):
        """测试日榜计算"""
        result = await square_service.get_ranking(
            period="daily", content_type=ContentType.NOVEL, limit=10
        )
        assert len(result["items"]) <= 10
        scores = [item["score"] for item in result["items"]]
        assert scores == sorted(scores, reverse=True)  # 降序排列

    @pytest.mark.asyncio
    async def test_ranking_score_formula(self, square_service):
        """测试排行榜评分公式（综合点赞、收藏、评论）"""
        result = await square_service.calculate_score(
            likes=100, favorites=50, comments=30, views=1000
        )
        assert result["score"] > 0
        # 收藏权重 > 点赞权重 > 评论权重
        score_likes_only = await square_service.calculate_score(
            likes=100, favorites=0, comments=0, views=1000
        )
        score_favs_only = await square_service.calculate_score(
            likes=0, favorites=100, comments=0, views=1000
        )
        assert score_favs_only["score"] > score_likes_only["score"]

    @pytest.mark.asyncio
    async def test_ranking_excludes_hidden(self, square_service):
        """测试排行榜排除被隐藏内容"""
        result = await square_service.get_ranking(
            period="daily", content_type=ContentType.NOVEL, limit=50
        )
        for item in result["items"]:
            assert item["status"] != ContentStatus.HIDDEN
```

### 2.12 专家建议服务单元测试

#### 2.12.1 test_advice_match - 建议匹配
```python
# tests/unit/test_advice_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.advice import AdviceService, AdviceCategory


class TestAdviceMatch:
    """专家建议匹配接口测试"""

    @pytest.fixture
    def advice_service(self, db_session):
        return AdviceService(db=db_session)

    @pytest.mark.asyncio
    async def test_match_advice_by_context(self, advice_service):
        """测试根据上下文匹配建议"""
        # Input
        result = await advice_service.match_advice(
            context={
                "genre": "都市现实",
                "current_chapter": 5,
                "total_chapters": 18,
                "issues": ["节奏过慢", "对话单一"]
            }
        )
        # Expected Output
        assert len(result["advices"]) > 0
        for advice in result["advices"]:
            assert "advice_id" in advice
            assert "content" in advice
            assert "category" in advice
            assert "relevance_score" in advice
            assert advice["relevance_score"] >= 0.5

    @pytest.mark.asyncio
    async def test_match_advice_priority_order(self, advice_service):
        """测试建议按相关度排序"""
        result = await advice_service.match_advice(
            context={"genre": "科幻", "issues": ["世界观模糊"]}
        )
        scores = [a["relevance_score"] for a in result["advices"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_no_advice_found(self, advice_service):
        """测试无匹配建议返回空"""
        with patch.object(advice_service, "_search_advice_db", return_value=[]):
            result = await advice_service.match_advice(
                context={"genre": "unknown_genre", "issues": []}
            )
        assert len(result["advices"]) == 0
        assert result["fallback_used"] is True
```

#### 2.12.2 test_conflict_detect - 建议冲突检测
```python
class TestConflictDetect:
    """建议冲突检测接口测试"""

    @pytest.mark.asyncio
    async def test_detect_conflicting_advice(self, advice_service):
        """测试检测互相冲突的建议"""
        advices = [
            {"advice_id": "adv_001", "content": "加快叙事节奏", "category": "pacing"},
            {"advice_id": "adv_002", "content": "增加细节描写放慢节奏", "category": "pacing"},
        ]
        result = await advice_service.detect_conflicts(advices)
        assert result["has_conflicts"] is True
        assert len(result["conflict_pairs"]) >= 1
        assert result["conflict_pairs"][0]["advice_a"] == "adv_001"
        assert result["conflict_pairs"][0]["advice_b"] == "adv_002"
        assert "resolution" in result["conflict_pairs"][0]

    @pytest.mark.asyncio
    async def test_no_conflicts(self, advice_service):
        """测试无冲突建议"""
        advices = [
            {"advice_id": "adv_003", "content": "增加对话", "category": "dialogue"},
            {"advice_id": "adv_004", "content": "完善世界观", "category": "worldbuilding"},
        ]
        result = await advice_service.detect_conflicts(advices)
        assert result["has_conflicts"] is False
        assert len(result["conflict_pairs"]) == 0

    @pytest.mark.asyncio
    async def test_conflict_auto_resolution(self, advice_service):
        """测试冲突自动解决策略"""
        advices = [
            {"advice_id": "adv_005", "content": "缩短章节", "category": "structure", "priority": 1},
            {"advice_id": "adv_006", "content": "扩展章节内容", "category": "structure", "priority": 2},
        ]
        result = await advice_service.detect_conflicts(advices, auto_resolve=True)
        assert result["has_conflicts"] is True
        assert result["resolved"] is True
        assert result["kept_advice"]["advice_id"] == "adv_005"  # 高优先级保留
```

#### 2.12.3 test_uniqueness_check - 组合唯一性检查
```python
class TestUniquenessCheck:
    """组合唯一性检查接口测试"""

    @pytest.mark.asyncio
    async def test_unique_combination(self, advice_service):
        """测试唯一的建议组合"""
        combination = {
            "genre": "都市现实",
            "style": "轻松幽默",
            "structure": "三幕式",
            "pacing": "快节奏"
        }
        result = await advice_service.check_uniqueness(combination)
        assert result["is_unique"] is True
        assert result["similarity_score"] < 0.8

    @pytest.mark.asyncio
    async def test_duplicate_combination_detected(self, advice_service):
        """测试检测到重复组合"""
        combination = {
            "genre": "都市现实",
            "style": "轻松幽默",
            "structure": "三幕式",
            "pacing": "快节奏"
        }
        # 第一次注册
        await advice_service.register_combination(combination, novel_id="novel_001")
        # 第二次检查唯一性
        result = await advice_service.check_uniqueness(combination)
        assert result["is_unique"] is False
        assert result["similar_novels"] is not None
        assert len(result["similar_novels"]) >= 1

    @pytest.mark.asyncio
    async def test_similar_but_different_combination(self, advice_service):
        """测试相似但不完全相同的组合"""
        await advice_service.register_combination(
            {"genre": "都市现实", "style": "轻松幽默", "structure": "三幕式", "pacing": "快节奏"},
            novel_id="novel_002"
        )
        result = await advice_service.check_uniqueness({
            "genre": "都市现实",
            "style": "轻松幽默",
            "structure": "五幕式",  # 不同的结构
            "pacing": "慢节奏"       # 不同的节奏
        })
        assert result["is_unique"] is True
        assert result["similarity_score"] > 0.3  # 有一定相似度
        assert result["similarity_score"] < 0.8  # 但不算重复

    @pytest.mark.asyncio
    async def test_uniqueness_with_empty_db(self, advice_service):
        """测试空数据库时所有组合均唯一"""
        result = await advice_service.check_uniqueness({
            "genre": "任意", "style": "任意"
        })
        assert result["is_unique"] is True
        assert result["similarity_score"] == 0.0
```

## 3. 集成测试设计

### 3.1 完整流水线集成测试

#### 3.1.1 18章完整流程测试
```python
# tests/integration/test_full_pipeline_18ch.py

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from app.core.pipeline import PipelineController
from app.core.state import StateManager

class TestFullPipeline18Chapters:
    """18章完整流水线集成测试"""
    
    @pytest.fixture
    def pipeline_config(self, tmp_path):
        """创建测试配置"""
        return {
            "data_dir": str(tmp_path),
            "llm_provider": "mock",
            "mock_mode": True,
            "agents": {
                "trend": {"enabled": True, "mock_data": True},
                "style": {"enabled": True, "mock_data": True},
                "planner": {
                    "enabled": True,
                    "batch_size": 3,
                    "max_retries": 3,
                    "review_threshold": 80
                },
                "writer": {
                    "enabled": True,
                    "batch_size": 3,
                    "max_workers": 3,
                    "consistency_threshold": 0.85
                },
                "polish": {"enabled": True},
                "auditor": {
                    "enabled": True,
                    "precision_target": 0.95,
                    "recall_target": 0.90
                },
                "reviser": {"enabled": True}
            }
        }
    
    @pytest.fixture
    def mock_llm_responses(self):
        """创建模拟LLM响应"""
        return {
            "trend_analysis": {
                "hot_genres": [
                    {"name": "都市现实", "heat_index": 95.2, "daily_growth": 12.5},
                    {"name": "玄幻奇幻", "heat_index": 88.7, "daily_growth": 8.3}
                ],
                "emerging_genres": [
                    {"name": "科幻未来", "growth_rate": 0.25, "potential_score": 0.85}
                ],
                "chapter_recommendation": {
                    "min": 12,
                    "recommended": 18,
                    "max": 30,
                    "rationale": "基于市场分析和读者偏好"
                },
                "reader_analysis": {
                    "demographics": {"18-25": 35, "26-35": 45},
                    "behavior_patterns": {"weekday": 65, "weekend": 35}
                }
            },
            "style_analysis": {
                "style_parameters": {
                    "language_complexity": 7.2,
                    "narrative_pace": 6.8,
                    "dialogue_ratio": 0.35,
                    "description_detail": 8.1
                },
                "characteristics": {
                    "sentence_length": {"mean": 25.3, "std": 8.7},
                    "vocabulary_richness": 0.18
                }
            },
            "plan_review": {
                "pass": True,
                "total_score": 85,
                "dimension_scores": {
                    "structure": 88,
                    "character": 82,
                    "plot": 85,
                    "market": 80,
                    "style": 90
                },
                "feedback": "策划案质量良好，结构完整，人物鲜明",
                "issues": []
            },
            "chapter_writing": {
                "content": """
                # 第{chapter}章 {title}
                
                清晨的阳光透过窗帘洒进房间。主角缓缓睁开眼睛，新的一天开始了。
                
                "今天一定要有所突破。"他对自己说。
                
                窗外传来鸟鸣声，一切都显得那么平静。但主角知道，平静之下暗流涌动。
                """,
                "quality_score": 8.5,
                "coherence_score": 9.0,
                "character_score": 8.2
            },
            "polish_result": {
                "polished_text": "优化后的文本...",
                "change_report": {
                    "grammar_fixes": 3,
                    "expression_improvements": 5,
                    "style_adjustments": 2
                },
                "quality_improvement": 0.15
            },
            "audit_result": {
                "needs_revision": False,
                "overall_score": 92,
                "precision": 0.96,
                "recall": 0.91,
                "f1_score": 0.935,
                "issues": [],
                "confidence_level": "high"
            }
        }
    
    @pytest.mark.integration
    @pytest.mark.timeout(600)  # 10分钟超时
    @pytest.mark.asyncio
    async def test_18_chapter_complete_pipeline(self, pipeline_config, mock_llm_responses, tmp_path):
        """测试18章完整流水线"""
        # 创建模拟LLM
        llm_call_count = 0
        
        async def mock_llm_chat(prompt, **kwargs):
            nonlocal llm_call_count
            llm_call_count += 1
            
            prompt_str = str(prompt).lower()
            
            # 根据提示类型返回不同响应
            if "trend" in prompt_str:
                return mock_llm_responses["trend_analysis"]
            elif "style" in prompt_str:
                return mock_llm_responses["style_analysis"]
            elif "review" in prompt_str and "plan" in prompt_str:
                return mock_llm_responses["plan_review"]
            elif "write" in prompt_str or "chapter" in prompt_str:
                # 根据章节号生成不同内容
                chapter_match = re.search(r'chapter[:\s]*(\d+)', prompt_str, re.IGNORECASE)
                if chapter_match:
                    chapter_num = int(chapter_match.group(1))
                    response = mock_llm_responses["chapter_writing"].copy()
                    response["content"] = response["content"].replace("{chapter}", str(chapter_num))
                    response["content"] = response["content"].replace("{title}", f"测试章节{chapter_num}")
                    return response
                return mock_llm_responses["chapter_writing"]
            elif "polish" in prompt_str:
                return mock_llm_responses["polish_result"]
            elif "audit" in prompt_str:
                return mock_llm_responses["audit_result"]
            else:
                return {"result": "default_response"}
        
        # 创建流水线控制器
        with patch('app.core.llm.chat_json', side_effect=mock_llm_chat):
            controller = PipelineController(config=pipeline_config)
            
            # 创建测试任务
            task_id = "integration_test_18ch"
            novel_title = "集成测试小说-18章"
            
            # 执行流水线
            start_time = asyncio.get_event_loop().time()
            
            result = await controller.execute_pipeline(
                task_id=task_id,
                novel_title=novel_title,
                chapter_count=18
            )
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            print(f"\n18章流水线执行时间: {execution_time:.2f}秒")
            print(f"LLM调用次数: {llm_call_count}")
        
        # 验证结果
        assert result["status"] == "success"
        assert result["task_id"] == task_id
        
        # 验证任务目录结构
        task_dir = tmp_path / "tasks" / task_id
        assert task_dir.exists()
        
        # 验证输出文件完整性
        expected_files = [
            "trend_analysis.json",
            "style_parameters.json",
            "planner/策划案.md",
            "planner/故事总纲.md",
            "planner/章节大纲.md",
            "writer/ch_01_raw.md",
            "writer/ch_18_raw.md",
            "polish/ch_01_polished.md",
            "polish/ch_18_polished.md",
            "audit_report.json",
            "progress/TrendAgent.json",
            "progress/PlannerAgent.json",
            "progress/WriterAgent.json",
            "progress/PolishAgent.json",
            "progress/AuditorAgent.json",
            "logs/TrendAgent.jsonl",
            "logs/PlannerAgent.jsonl"
        ]
        
        missing_files = []
        for file_path in expected_files:
            full_path = task_dir / "output" / file_path
            if not full_path.exists():
                missing_files.append(str(file_path))
        
        assert len(missing_files) == 0, f"缺失文件: {missing_files}"
        
        # 验证元数据
        meta_file = task_dir / "meta.json"
        assert meta_file.exists()
        
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        assert meta["task_id"] == task_id
        assert meta["novel_title"] == novel_title
        assert meta["status"] == "completed"
        assert "overall_progress" in meta
        assert meta["overall_progress"] == 1.0  # 100%完成
        
        # 验证所有Agent都执行了
        expected_agents = ["trend", "style", "planner", "writer", "polish", "auditor"]
        for agent in expected_agents:
            assert agent in meta["agents"]
            assert meta["agents"][agent]["status"] == "completed"
        
        # 验证章节数量
        chapter_files = list((task_dir / "output" / "writer").glob("ch_*.md"))
        assert len(chapter_files) == 18
        
        # 验证润色后章节
        polished_files = list((task_dir / "output" / "polish").glob("ch_*.md"))
        assert len(polished_files) == 18
        
        # 验证审计报告
        audit_file = task_dir / "output" / "audit_report.json"
        assert audit_file.exists()
        
        with open(audit_file, 'r', encoding='utf-8') as f:
            audit_report = json.load(f)
        
        assert audit_report["needs_revision"] == False
        assert audit_report["overall_score"] >= 80
        
        # 性能验证：18章应该在合理时间内完成
        # 需求文档要求：最优情况88分钟，平均105分钟，最差135分钟
        # 测试环境应该更快（使用模拟数据）
        assert execution_time < 300  # 5分钟内完成（测试环境）
        
        return {
            "task_id": task_id,
            "execution_time": execution_time,
            "llm_calls": llm_call_count,
            "chapter_count": len(chapter_files),
            "success": True
        }
    
    @pytest.mark.integration
    @pytest.mark.timeout(300)  # 5分钟超时
    @pytest.mark.asyncio
    async def test_pipeline_with_revision_cycle(self, pipeline_config, mock_llm_responses, tmp_path):
        """测试包含修订循环的流水线"""
        revision_triggered = False
        
        async def mock_llm_with_revision(prompt, **kwargs):
            nonlocal revision_triggered
            prompt_str = str(prompt).lower()
            
            if "audit" in prompt_str and not revision_triggered:
                # 第一次审计发现问题
                revision_triggered = True
                return {
                    "needs_revision": True,
                    "overall_score": 65,
                    "precision": 0.85,
                    "recall": 0.80,
                    "f1_score": 0.825,
                    "issues": [
                        {
                            "id": "issue_1",
                            "type": "plot_hole",
                            "severity": "medium",
                            "description": "第3-5章情节衔接不自然",
                            "suggestion": "增加过渡段落"
                        },
                        {
                            "id": "issue_2",
                            "type": "character_inconsistency",
                            "severity": "low",
                            "description": "主角在第2章和第6章性格略有差异",
                            "suggestion": "统一性格描写"
                        }
                    ],
                    "confidence_level": "medium"
                }
            elif "audit" in prompt_str and revision_triggered:
                # 修订后审计通过
                return mock_llm_responses["audit_result"]
            else:
                # 其他情况使用默认响应
                return await self._get_default_response(prompt_str, mock_llm_responses)
        
        # 创建流水线控制器
        with patch('app.core.llm.chat_json', side_effect=mock_llm_with_revision):
            controller = PipelineController(config=pipeline_config)
            
            # 执行6章测试（更容易触发修订）
            task_id = "revision_test_6ch"
            result = await controller.execute_pipeline(
                task_id=task_id,
                novel_title="修订测试小说",
                chapter_count=6
            )
        
        # 验证结果
        assert result["status"] == "success"
        assert revision_triggered == True  # 应该触发了修订
        
        # 验证修订记录
        task_dir = tmp_path / "tasks" / task_id
        revision_file = task_dir / "output" / "revision_report.json"
        
        if revision_file.exists():
            with open(revision_file, 'r', encoding='utf-8') as f:
                revision_data = json.load(f)
            
            assert "revisions" in revision_data
            assert len(revision_data["revisions"]) > 0
            
            # 验证修订问题
            for revision in revision_data["revisions"]:
                assert "issue" in revision
                assert "revised_text" in revision
                assert "changes" in revision
                assert "strategy_used" in revision
        
        return {
            "task_id": task_id,
            "revision_triggered": revision_triggered,
            "has_revision_report": revision_file.exists()
        }
    
    async def _get_default_response(self, prompt_str, mock_responses):
        """获取默认响应"""
        if "trend" in prompt_str:
            return mock_responses["trend_analysis"]
        elif "style" in prompt_str:
            return mock_responses["style_analysis"]
        elif "review" in prompt_str:
            return mock_responses["plan_review"]
        elif "write" in prompt_str or "chapter" in prompt_str:
            return mock_responses["chapter_writing"]
        elif "polish" in prompt_str:
            return mock_responses["polish_result"]
        else:
            return {"result": "default_response"}
```

### 3.2 3章批次机制集成测试

#### 3.2.1 批次写作集成测试
```python
# tests/integration/test_batch_writing.py

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from app.agents.writer import BatchWritingController
from app.agents.planner import ThreeChapterCycleController

class TestBatchWritingIntegration:
    """3章批次写作集成测试"""
    
    @pytest.fixture
    def batch_writing_config(self):
        return {
            "batch_size": 3,
            "max_workers": 3,
            "consistency_threshold": 0.85,
            "quality_threshold": 7.0
        }
    
    @pytest.fixture
    def test_outlines(self):
        """创建测试大纲"""
        return [
            {
                "chapter": 1,
                "title": "开端",
                "summary": "主角出场，引入核心冲突",
                "key_events": ["主角登场", "冲突引入", "悬念设置"],
                "characters": ["主角", "配角A"],
                "word_target": 3000,
                "emotional_arc": "平静→紧张"
            },
            {
                "chapter": 2,
                "title": "发展",
                "summary": "冲突升级，人物关系发展",
                "key_events": ["冲突升级", "人物互动", "线索发现"],
                "characters": ["主角", "配角A", "反派"],
                "word_target": 3200,
                "emotional_arc": "紧张→焦虑"
            },
            {
                "chapter": 3,
                "title": "转折",
                "summary": "关键转折，人物成长",
                "key_events": ["关键转折", "人物成长", "新目标"],
                "characters": ["主角", "配角A", "配角B", "反派"],
                "word_target": 3500,
                "emotional_arc": "焦虑→决心"
            }
        ]
    
    @pytest.mark.integration
    @pytest.mark.timeout(180)  # 3分钟超时
    @pytest.mark.asyncio
    async def test_3_chapter_batch_writing(self, batch_writing_config, test_outlines):
        """测试3章批次写作"""
        # 创建批次控制器
        controller = BatchWritingController(**batch_writing_config)
        
        # 模拟LLM生成
        generated_chapters = []
        
        async def mock_generate_single_chapter(params):
            chapter_num = params["chapter_number"]
            outline = params["outline"]
            
            # 生成模拟章节内容
            content = f"""
            # 第{chapter_num}章 {outline['title']}
            
            这是第{chapter_num}章的内容。{outline['summary']}
            
            主要事件：{', '.join(outline['key_events'][:2])}
            
            出场人物：{', '.join(outline['characters'])}
            
            情感走向：{outline['emotional_arc']}
            
            字数目标：{outline['word_target']}字
            """
            
            generated_chapters.append({
                "chapter_number": chapter_num,
                "content": content,
                "params": params
            })
            
            return content
        
        # 执行批次写作
        with patch.object(controller, '_generate_single_chapter', side_effect=mock_generate_single_chapter):
            result = await controller.write_batch(
                start_chapter=1,
                outlines=test_outlines
            )
        
        # 验证结果
        assert "chapters" in result
        assert "batch_info" in result
        
        chapters = result["chapters"]
        batch_info = result["batch_info"]
        
        # 验证批次信息
        assert batch_info["start_chapter"] == 1
        assert batch_info["end_chapter"] == 3
        assert "consistency_result" in batch_info
        assert "quality_scores" in batch_info
        assert "generated_at" in batch_info
        
        # 验证章节数量
        assert len(chapters) == 3
        
        # 验证章节内容
        for i, chapter in enumerate(chapters, 1):
            assert chapter["chapter_number"] == i
            assert "content" in chapter
            assert len(chapter["content"]) > 100  # 应该有足够内容
            assert chapter["outline"] == test_outlines[i-1]
            assert "generation_time" in chapter
        
        # 验证一致性检查
        consistency = batch_info["consistency_result"]
        assert "passed" in consistency
        assert "pass_rate" in consistency
        assert "issues" in consistency
        
        # 验证质量评估
        quality = batch_info["quality_scores"]
        assert "avg_score" in quality
        assert "scores" in quality
        assert len(quality["scores"]) == 3
        
        # 验证并行生成
        assert len(generated_chapters) == 3
        
        return {
            "batch_size": len(chapters),
            "consistency_passed": consistency["passed"],
            "avg_quality": quality["avg_score"],
            "generation_count": len(generated_chapters)
        }
    
    @pytest.mark.integration
    @pytest.mark.timeout(300)  # 5分钟超时
    @pytest.mark.asyncio
    async def test_multiple_batch_continuity(self, batch_writing_config):
        """测试多批次连续性"""
        # 创建两个批次的大纲
        batch1_outlines = [
            {"chapter": 1, "title": "第1章", "summary": "开端"},
            {"chapter": 2, "title": "第2章", "summary": "发展"},
            {"chapter": 3, "title": "第3章", "summary": "转折"}
        ]
        
        batch2_outlines = [
            {"chapter": 4, "title": "第4章", "summary": "冲突"},
            {"chapter": 5, "title": "第5章", "summary": "高潮"},
            {"chapter": 6, "title": "第6章", "summary": "解决"}
        ]
        
        controller = BatchWritingController(**batch_writing_config)
        
        # 模拟章节生成
        all_chapters = []
        
        async def mock_generate(params):
            chapter_num = params["chapter_number"]
            
            # 根据上下文生成内容
            context = params.get("context", {})
            recent_chapters = context.get("recent_chapters", [])
            
            # 构建连续性内容
            if recent_chapters:
                continuity_ref = f"承接上文：{len(recent_chapters)}章上下文"
            else:
                continuity_ref = "故事开始"
            
            content = f"""
            第{chapter_num}章内容。
            {continuity_ref}
            
            这是连续故事的一部分。
            """
            
            all_chapters.append({
                "chapter": chapter_num,
                "content": content,
                "context": context
            })
            
            return content
        
        # 执行第一批次
        with patch.object(controller, '_generate_single_chapter', side_effect=mock_generate):
            batch1_result = await controller.write_batch(
                start_chapter=1,
                outlines=batch1_outlines
            )
        
        batch1_chapters = batch1_result["chapters"]
        
        # 执行第二批次（使用第一批次的上下文）
        with patch.object(controller, '_generate_single_chapter', side_effect=mock_generate):
            batch2_result = await controller.write_batch(
                start_chapter=4,
                outlines=batch2_outlines,
                previous_chapters=batch1_chapters
            )
        
        # 验证结果
        assert len(all_chapters) == 6
        
        # 验证上下文传递
        for i, chapter_info in enumerate(all_chapters):
            chapter_num = chapter_info["chapter"]
            context = chapter_info["context"]
            
            if chapter_num >= 4:  # 第二批次
                # 应该包含第一批次的上下文
                assert "recent_chapters" in context
                recent = context["recent_chapters"]
                assert len(recent) > 0
                
                # 验证人物状态传递
                assert "character_states" in context
                assert "plot_progress" in context
        
        # 验证批次间一致性
        # 可以通过比较第3章和第4章的内容连续性来验证
        
        return {
            "total_chapters": len(all_chapters),
            "batch1_count": len(batch1_chapters),
            "batch2_count": len(batch2_result["chapters"]),
            "context_passed": True
        }
```

### 3.3 错误恢复集成测试

#### 3.3.1 错误处理集成测试
```python
# tests/integration/test_error_recovery.py

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from app.core.error_recovery import ErrorRecoverySystem
from app.agents.writer import BatchWritingController

class TestErrorRecoveryIntegration:
    """错误恢复集成测试"""
    
    @pytest.fixture
    def error_recovery_system(self):
        return ErrorRecoverySystem(
            max_retries=3,
            backoff_factor=2.0
        )
    
    @pytest.mark.integration
    @pytest.mark.timeout(120)  # 2分钟超时
    @pytest.mark.asyncio
    async def test_timeout_error_recovery(self, error_recovery_system):
        """测试超时错误恢复"""
        error_count = 0
        
        async def operation_with_timeout(context):
            nonlocal error_count
            error_count += 1
            
            if error_count < 3:  # 前两次超时
                raise TimeoutError(f"第{error_count}次超时")
            else:  # 第三次成功
                return {"result": "success", "attempts": error_count}
        
        # 模拟操作上下文
        context = {
            "operation": "batch_writing",
            "batch_size": 3,
            "start_chapter": 1
        }
        
        # 执行带错误恢复的操作
        result = await error_recovery_system.execute_with_recovery(
            operation_with_timeout,
            context,
            error_types=["timeout"]
        )
        
        # 验证结果
        assert result["success"] == True
        assert result["result"]["result"] == "success"
        assert result["result"]["attempts"] == 3
        assert result["retry_count"] == 2  # 重试了2次
        
        # 验证错误历史
        assert len(error_recovery_system.error_history) > 0
        
        return {
            "success": result["success"],
            "total_attempts": error_count,
            "retry_count": result["retry_count"],
            "error_history_size": len(error_recovery_system.error_history)
        }
    
    @pytest.mark.integration
    @pytest.mark.timeout(180)  # 3分钟超时
    @pytest.mark.asyncio
    async def test_network_error_with_fallback(self, error_recovery_system):
        """测试网络错误降级恢复"""
        primary_failures = 0
        
        async def primary_operation(context):
            nonlocal primary_failures
            primary_failures += 1
            
            if primary_failures <= 2:  # 前两次网络错误
                raise ConnectionError("网络连接失败")
            else:
                return {"source": "primary", "data": "主要数据"}
        
        async def fallback_operation(context):
            return {"source": "fallback", "data": "降级数据"}
        
        # 配置错误恢复策略
        error_recovery_system.fallback_operations = {
            "network": fallback_operation
        }
        
        context = {"operation": "data_fetch", "url": "https://api.example.com"}
        
        # 执行操作
        result = await error_recovery_system.execute_with_recovery(
            primary_operation,
            context,
            error_types=["network"]
        )
        
        # 验证结果
        assert result["success"] == True
        assert result["result"]["source"] == "fallback"  # 应该使用了降级
        assert result["result"]["data"] == "降级数据"
        
        # 验证重试次数
        assert primary_failures == 3  # 重试2次 + 最终失败
        
        return {
            "success": result["success"],
            "data_source": result["result"]["source"],
            "primary_attempts": primary_failures,
            "used_fallback": True
        }
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_error_wait_and_retry(self, error_recovery_system):
        """测试资源错误等待重试"""
        import time
        
        operation_times = []
        
        async def resource_intensive_operation(context):
            current_time = time.time()
            operation_times.append(current_time)
            
            if len(operation_times) == 1:  # 第一次资源不足
                raise MemoryError("内存不足，请稍后重试")
            else:  # 第二次成功
                return {"result": "success", "attempt": len(operation_times)}
        
        context = {"operation": "batch_processing", "data_size": "large"}
        
        # 执行操作
        start_time = time.time()
        result = await error_recovery_system.execute_with_recovery(
            resource_intensive_operation,
            context,
            error_types=["resource"]
        )
        end_time = time.time()
        
        # 验证结果
        assert result["success"] == True
        assert result["result"]["result"] == "success"
        assert result["result"]["attempt"] == 2  # 第二次成功
        
        # 验证等待时间
        if len(operation_times) == 2:
            wait_time = operation_times[1] - operation_times[0]
            # 应该等待了配置的时间（资源错误默认等待60秒）
            # 测试中可能实际等待时间较短，但应该大于0
            assert wait_time > 0
        
        # 验证总执行时间
        total_time = end_time - start_time
        assert total_time > 1  # 至少应该有等待时间
        
        return {
            "success": result["success"],
            "total_attempts": len(operation_times),
            "total_time": total_time,
            "recovered_from_resource_error": True
        }
```

### 3.4 集成测试与系统测试的边界

| 类型 | 典型载体 | 依赖 |
|------|----------|------|
| **集成测试**（§3.1–§3.3） | `pytest` + Mock LLM / 测试库 | PostgreSQL（或项目约定的测试 DB）；**无** Docker 编排、**无** Redis |
| **系统测试**（§6.3、`docs/TESTING.md`） | 手工或脚本 + 真实 systemd 进程 | 104 或等价裸机；TC-S01/S02、TC-C01–C12 |

集成测试**不替代**发版前的系统测试：后者验证磁盘门禁、内存、journal 与真实支付沙箱回调路径。

---

## 4. 性能测试设计

### 4.0 环境与指标分级

- **104 对齐档（B）**：在目标机或限制 cgroup 的 Runner 上执行；`max_concurrent_tasks ≤ 2`；单测进程峰值内存建议断言 **≤300MB**；磁盘写入使用临时目录并在用例 `teardown` 删除。
- **扩展档（A）**：用于开发机/CI 基准对比，可保留较高并发与较宽内存阈值，但 **CI 仍不启动 Redis**，与架构一致。

以下代码示例中，`test_concurrent_batch_performance` 的 **104 对齐断言** 以注释形式标注；默认示例改为「最多 2 个并发 pipeline」，与架构文档一致。

### 4.1 批次性能基准测试

#### 4.1.1 3章批次性能测试
```python
# tests/performance/test_batch_performance.py

import pytest
import asyncio
import time
import statistics
from datetime import datetime

class TestBatchPerformance:
    """批次性能基准测试"""
    
    @pytest.mark.performance
    @pytest.mark.benchmark
    @pytest.mark.timeout(600)  # 10分钟超时
    @pytest.mark.asyncio
    async def test_3_chapter_batch_performance(self):
        """测试3章批次性能基准"""
        from app.agents.writer import BatchWritingController
        
        # 配置
        config = {
            "batch_size": 3,
            "max_workers": 3,
            "consistency_threshold": 0.85
        }
        
        controller = BatchWritingController(**config)
        
        # 创建测试数据
        test_outlines = []
        for i in range(1, 10):  # 3个批次，共9章
            test_outlines.append({
                "chapter": i,
                "title": f"第{i}章",
                "summary": f"这是第{i}章的概要",
                "key_events": [f"事件{i}.1", f"事件{i}.2"],
                "characters": ["主角", f"配角{i}"],
                "word_target": 3000 + (i * 100)
            })
        
        # 性能指标收集
        batch_times = []
        chapter_times = []
        memory_samples = []
        
        import psutil
        import os
        process = psutil.Process(os.getpid())
        
        # 执行3个批次
        for batch_start in range(0, 9, 3):
            batch_outlines = test_outlines[batch_start:batch_start + 3]
            
            # 记录开始时间和内存
            start_time = time.time()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 执行批次
            result = await controller.write_batch(
                start_chapter=batch_start + 1,
                outlines=batch_outlines,
                mock_mode=True  # 使用模拟模式避免实际LLM调用
            )
            
            # 记录结束时间和内存
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024
            
            # 计算指标
            batch_time = end_time - start_time
            memory_used = end_memory - start_memory
            
            batch_times.append(batch_time)
            memory_samples.append(memory_used)
            
            # 记录章节生成时间（如果有）
            if "generation_times" in result.get("batch_info", {}):
                chapter_times.extend(result["batch_info"]["generation_times"])
            
            print(f"批次{batch_start//3 + 1}: {batch_time:.2f}秒, 内存变化: {memory_used:.2f}MB")
        
        # 性能分析
        avg_batch_time = statistics.mean(batch_times)
        std_batch_time = statistics.stdev(batch_times) if len(batch_times) > 1 else 0
        
        avg_memory_change = statistics.mean(memory_samples)
        max_memory = max(memory_samples)
        
        # 性能要求验证
        print(f"\n性能测试结果:")
        print(f"  测试批次: {len(batch_times)}")
        print(f"  平均批次时间: {avg_batch_time:.2f}秒")
        print(f"  批次时间标准差: {std_batch_time:.2f}秒")
        print(f"  平均内存变化: {avg_memory_change:.2f}MB")
        print(f"  最大内存增长: {max_memory:.2f}MB")
        
        # 性能断言
        # 需求文档要求：单批次（3章）生成和审核：6.5分钟
        assert avg_batch_time < 390  # 6.5分钟 = 390秒
        
        # 稳定性要求：标准差不超过平均值的50%
        if avg_batch_time > 0:
            stability = std_batch_time / avg_batch_time
            assert stability < 0.5, f"批次时间不稳定: {stability:.2%}"
        
        # 内存要求：104 对齐档建议批次间内存增长不超过 80MB（1GB 机器更严）
        assert max_memory < 100, f"内存增长过高: {max_memory:.2f}MB"
        # 若在 104 上实测，可改为 assert max_memory < 80
        
        return {
            "batch_count": len(batch_times),
            "avg_batch_time_seconds": avg_batch_time,
            "batch_time_std": std_batch_time,
            "avg_memory_change_mb": avg_memory_change,
            "max_memory_growth_mb": max_memory,
            "meets_performance_requirements": True
        }
    
    @pytest.mark.performance
    @pytest.mark.benchmark
    @pytest.mark.timeout(300)  # 5分钟超时
    @pytest.mark.asyncio
    async def test_concurrent_batch_performance(self):
        """测试并发批次性能（104 对齐：最多 2 路并发）"""
        from app.core.pipeline import PipelineController
        
        # 配置：与生产 104 环境一致——并发≤2，避免 OOM
        config = {
            "max_concurrent_tasks": 2,
            "agents": {
                "writer": {
                    "batch_size": 3,
                    "max_workers": 2
                }
            }
        }
        
        controller = PipelineController(config)
        
        # 创建并发任务
        tasks = []
        start_time = time.time()
        
        concurrent_n = 2  # 104 策略：禁止 5 路并发；扩展档可改为 5 并单独 job
        for i in range(concurrent_n):
            task = asyncio.create_task(
                controller.execute_pipeline(
                    task_id=f"concurrent_perf_{i}",
                    novel_title=f"并发性能测试{i}",
                    chapter_count=3,  # 短任务
                    mock_mode=True
                )
            )
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 分析结果
        successful = 0
        failed = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
                print(f"任务失败: {result}")
            elif result.get("status") == "success":
                successful += 1
        
        # 性能分析
        avg_task_time = total_time / len(tasks) if tasks else 0
        throughput = successful / total_time if total_time > 0 else 0
        
        print(f"\n并发性能测试结果:")
        print(f"  总任务数: {len(tasks)}")
        print(f"  成功数: {successful}")
        print(f"  失败数: {failed}")
        print(f"  总执行时间: {total_time:.2f}秒")
        print(f"  平均任务时间: {avg_task_time:.2f}秒")
        print(f"  吞吐量: {throughput:.3f} 任务/秒")
        
        # 性能断言（2 个任务时应全部成功）
        assert successful >= concurrent_n - 1, f"并发任务成功数不足: {successful}/{concurrent_n}"
        assert failed == 0, "不应该有任务失败"
        
        # 并发效率：5个任务应该在合理时间内完成
        # 单个3章任务约1分钟，5个并发应该小于5分钟
        assert total_time < 300  # 5分钟
        
        return {
            "total_tasks": len(tasks),
            "successful_tasks": successful,
            "failed_tasks": failed,
            "total_time_seconds": total_time,
            "avg_task_time_seconds": avg_task_time,
            "throughput_tasks_per_second": throughput,
            "concurrent_efficiency": successful / len(tasks)
        }
```

### 4.2 内存使用性能测试

#### 4.2.1 长期运行内存测试
```python
# tests/performance/test_memory_performance.py

import pytest
import asyncio
import time
import psutil
import os
from datetime import datetime

class TestMemoryPerformance:
    """内存使用性能测试"""
    
    @pytest.mark.performance
    @pytest.mark.memory
    @pytest.mark.timeout(900)  # 15分钟超时
    @pytest.mark.asyncio
    async def test_long_running_memory_usage(self):
        """测试长期运行内存使用"""
        from app.agents.writer import BatchWritingController
        
        controller = BatchWritingController(batch_size=3, max_workers=3)
        
        process = psutil.Process(os.getpid())
        
        # 内存采样
        memory_samples = []
        batch_count = 0
        
        # 初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_samples.append({
            "time": 0,
            "memory_mb": initial_memory,
            "batch": 0
        })
        
        print(f"初始内存: {initial_memory:.2f}MB")
        
        # 模拟长期运行（10个批次）
        for batch_num in range(1, 11):
            # 创建测试大纲
            outlines = []
            for i in range(3):
                chapter_num = (batch_num - 1) * 3 + i + 1
                outlines.append({
                    "chapter": chapter_num,
                    "title": f"第{chapter_num}章",
                    "summary": f"长期测试第{chapter_num}章",
                    "key_events": [f"测试事件{chapter_num}.1"],
                    "characters": ["测试主角"],
                    "word_target": 3000
                })
            
            # 执行批次
            await controller.write_batch(
                start_chapter=(batch_num - 1) * 3 + 1,
                outlines=outlines,
                mock_mode=True
            )
            
            batch_count += 1
            
            # 采样内存
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append({
                "time": batch_num * 30,  # 假设每个批次30秒
                "memory_mb": current_memory,
                "batch": batch_num
            })
            
            print(f"批次{batch_num}: 内存 {current_memory:.2f}MB")
            
            # 模拟批次间清理
            if hasattr(controller, 'clear_cache'):
                controller.clear_cache()
            
            # 短暂暂停
            await asyncio.sleep(0.1)
        
        # 最终内存
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # 内存分析
        memory_values = [s["memory_mb"] for s in memory_samples]
        max_memory = max(memory_values)
        min_memory = min(memory_values)
        avg_memory = sum(memory_values) / len(memory_values)
        
        # 内存泄漏检测
        memory_leak = final_memory - initial_memory
        memory_growth_rate = memory_leak / len(memory_samples)
        
        print(f"\n内存使用分析:")
        print(f"  初始内存: {initial_memory:.2f}MB")
        print(f"  最终内存: {final_memory:.2f}MB")
        print(f"  峰值内存: {max_memory:.2f}MB")
        print(f"  平均内存: {avg_memory:.2f}MB")
        print(f"  内存增长: {memory_leak:.2f}MB")
        print(f"  每批次增长: {memory_growth_rate:.3f}MB/批次")
        
        # 内存断言
        # 需求文档要求：峰值内存<650MB
        assert max_memory < 650, f"峰值内存过高: {max_memory:.2f}MB"
        
        # 内存泄漏：长期运行增长不超过200MB
        assert memory_leak < 200, f"可能的内存泄漏: {memory_leak:.2f}MB增长"
        
        # 批次间增长：每批次不超过20MB
        assert memory_growth_rate < 20, f"批次间内存增长过高: {memory_growth_rate:.2f}MB/批次"
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "peak_memory_mb": max_memory,
            "avg_memory_mb": avg_memory,
            "memory_growth_mb": memory_leak,
            "growth_per_batch_mb": memory_growth_rate,
            "batch_count": batch_count,
            "meets_memory_requirements": True
        }
```

## 5. 测试执行与报告

### 5.1 测试执行脚本

#### 5.1.1 完整测试套件执行
```bash
#!/bin/bash
# run_tests.sh

echo "=== AI小说生成Agent系统测试套件执行 ==="
echo "开始时间: $(date)"
echo ""

# 1. 单元测试
echo "1. 执行单元测试..."
pytest tests/unit/ -v \
  --cov=app \
  --cov-report=term \
  --cov-report=html:coverage_html \
  --cov-report=xml:coverage.xml \
  --junitxml=test_results_unit.xml

UNIT_EXIT_CODE=$?
echo "单元测试退出码: $UNIT_EXIT_CODE"
echo ""

# 2. 集成测试
echo "2. 执行集成测试..."
pytest tests/integration/ -v \
  -m "integration" \
  --junitxml=test_results_integration.xml

INTEGRATION_EXIT_CODE=$?
echo "集成测试退出码: $INTEGRATION_EXIT_CODE"
echo ""

# 3. 性能测试
echo "3. 执行性能测试..."
pytest tests/performance/ -v \
  -m "performance" \
  --junitxml=test_results_performance.xml

PERFORMANCE_EXIT_CODE=$?
echo "性能测试退出码: $PERFORMANCE_EXIT_CODE"
echo ""

# 4. 生成测试报告
echo "4. 生成测试报告..."
python -c "
import json
import xml.etree.ElementTree as ET
from datetime import datetime

def parse_junit_xml(file_path):
    \"\"\"解析JUnit XML文件\"\"\"
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        tests = int(root.attrib.get('tests', 0))
        failures = int(root.attrib.get('failures', 0))
        errors = int(root.attrib.get('errors', 0))
        skipped = int(root.attrib.get('skipped', 0))
        time = float(root.attrib.get('time', 0))
        
        return {
            'tests': tests,
            'failures': failures,
            'errors': errors,
            'skipped': skipped,
            'time': time,
            'success_rate': (tests - failures - errors) / tests if tests > 0 else 0
        }
    except Exception as e:
        return {'error': str(e)}

# 解析各测试类型结果
unit_results = parse_junit_xml('test_results_unit.xml')
integration_results = parse_junit_xml('test_results_integration.xml')
performance_results = parse_junit_xml('test_results_performance.xml')

# 生成汇总报告
summary = {
    'timestamp': datetime.now().isoformat(),
    'overall': {
        'unit_tests': unit_results,
        'integration_tests': integration_results,
        'performance_tests': performance_results,
        'total_tests': unit_results.get('tests', 0) + integration_results.get('tests', 0) + performance_results.get('tests', 0),
        'total_failures': unit_results.get('failures', 0) + integration_results.get('failures', 0) + performance_results.get('failures', 0),
        'total_errors': unit_results.get('errors', 0) + integration_results.get('errors', 0) + performance_results.get('errors', 0),
        'all_passed': unit_results.get('failures', 0) == 0 and unit_results.get('errors', 0) == 0 and
                     integration_results.get('failures', 0) == 0 and integration_results.get('errors', 0) == 0 and
                     performance_results.get('failures', 0) == 0 and performance_results.get('errors', 0) == 0
    },
    'exit_codes': {
        'unit': $UNIT_EXIT_CODE,
        'integration': $INTEGRATION_EXIT_CODE,
        'performance': $PERFORMANCE_EXIT_CODE
    }
}

# 计算总体成功率
total_tests = summary['overall']['total_tests']
total_failures = summary['overall']['total_failures']
total_errors = summary['overall']['total_errors']

if total_tests > 0:
    success_rate = (total_tests - total_failures - total_errors) / total_tests
    summary['overall']['success_rate'] = success_rate
else:
    summary['overall']['success_rate'] = 0

# 保存报告
with open('test_summary.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

# 打印报告
print('测试执行完成！')
print(f'总测试数: {total_tests}')
print(f'失败数: {total_failures}')
print(f'错误数: {total_errors}')
print(f'成功率: {success_rate:.2%}')
print(f'整体通过: {\"是\" if summary[\"overall\"][\"all_passed\"] else \"否\"}')
"

# 5. 检查退出码
echo ""
echo "5. 检查测试结果..."
if [ $UNIT_EXIT_CODE -eq 0 ] && [ $INTEGRATION_EXIT_CODE -eq 0 ] && [ $PERFORMANCE_EXIT_CODE -eq 0 ]; then
    echo "✅ 所有测试通过！"
    EXIT_CODE=0
else
    echo "❌ 有测试失败"
    EXIT_CODE=1
fi

echo ""
echo "结束时间: $(date)"
echo "测试报告已生成:"
echo "  - test_summary.json (测试汇总)"
echo "  - coverage_html/ (代码覆盖率HTML报告)"
echo "  - coverage.xml (代码覆盖率XML报告)"
echo "  - test_results_*.xml (各测试类型详细结果)"

exit $EXIT_CODE
```

### 5.2 持续集成配置

#### 5.2.1 GitHub Actions配置
```yaml
# .github/workflows/test.yml
name: AI小说生成Agent系统测试

on:
  push:
    branches: [ master, develop ]
  pull_request:
    branches: [ master ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      # 与生产一致：仅 PostgreSQL，不启动 Redis / RabbitMQ（架构约束）
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: ai_novel_test
        options: >-
          --health-cmd "pg_isready -U test -d ai_novel_test"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: 设置Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: 安装依赖
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov pytest-mock
        pip install pytest-benchmark  # 性能测试
    
    - name: 运行单元测试
      run: |
        pytest tests/unit/ -v \
          --cov=app \
          --cov-report=term \
          --cov-report=xml:coverage.xml \
          --junitxml=test-results/unit.xml
      env:
        PYTHONPATH: ${{ github.workspace }}/backend
        DATABASE_URL: postgresql://test:test@localhost:5432/ai_novel_test
    
    - name: 运行集成测试
      run: |
        pytest tests/integration/ -v \
          -m "integration" \
          --junitxml=test-results/integration.xml
      env:
        PYTHONPATH: ${{ github.workspace }}/backend
        DATABASE_URL: postgresql://test:test@localhost:5432/ai_novel_test
        TEST_MODE: "true"
        MOCK_LLM: "true"
    
    - name: 运行性能测试
      run: |
        pytest tests/performance/ -v \
          -m "performance" \
          --junitxml=test-results/performance.xml
      env:
        PYTHONPATH: ${{ github.workspace }}/backend
        DATABASE_URL: postgresql://test:test@localhost:5432/ai_novel_test
        TEST_MODE: "true"
        MOCK_LLM: "true"
    
    - name: 上传测试结果
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results-${{ matrix.python-version }}
        path: |
          test-results/
          coverage.xml
    
    - name: 上传覆盖率到Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: 生成测试报告
      run: |
        python scripts/generate_test_report.py
      env:
        PYTHONPATH: ${{ github.workspace }}/backend
    
    - name: 上传测试报告
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-report-${{ matrix.python-version }}
        path: test-report.html
```

## 6. 测试质量指标

### 6.1 测试覆盖率目标
```yaml
# .coveragerc
[run]
source = app
omit = 
    */tests/*
    */__pycache__/*
    */migrations/*
    */admin.py
    */apps.py
    */models.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if settings.DEBUG
    if 0:
    if TYPE_CHECKING:

fail_under = 85
```

### 6.2 性能基准指标
```json
{
  "performance_benchmarks": {
    "batch_writing": {
      "3_chapter_batch": {
        "target_time_seconds": 390,
        "acceptable_range": "300-480",
        "memory_limit_mb_ci": 650,
        "memory_limit_mb_production_104": 300,
        "cpu_usage_percent": 80
      }
    },
    "concurrent_tasks": {
      "2_concurrent_104": {
        "description": "104 裸机 1GB 内存策略",
        "max_parallel_pipelines": 2,
        "throughput_tasks_per_hour": 8,
        "response_time_seconds": 300,
        "error_rate_percent": 5
      },
      "extended_ci": {
        "description": "扩展档（非 104 验收）",
        "max_parallel_pipelines": 5,
        "memory_limit_mb": 650
      }
    },
    "memory_usage": {
      "peak_memory_mb_production_104": 300,
      "peak_memory_mb_ci": 650,
      "average_memory_mb_104": 200,
      "memory_leak_per_hour_mb": 20
    }
  }
}
```

### 6.3 系统测试设计（裸机验收，与 `docs/TESTING.md` 对齐）

**定义**：系统测试在**目标运行形态**下验证完整行为——**模块化单体** + **systemd** + **PostgreSQL** + 本地数据目录，不依赖 Docker、Redis、RabbitMQ。

| 类别 | 内容 | 参考 |
|------|------|------|
| 部署形态 | `systemctl status ai-novel-agent`（及可选 worker）为 `active` | 运维 runbook |
| 健康检查 | `GET /api/health` 或 `/health` 返回 DB 可达；含磁盘/内存字段时符合 TC-C11/C12 | TESTING.md |
| 业务 E2E | TC-C01–TC-C10（注册、支付、OpenClaw、多端、视频、发布、幂等、广场、对账） | TESTING.md |
| 资源门禁 | TC-C11 磁盘、TC-C12 内存 | TESTING.md |
| 冒烟 | TC-S01–TC-S02（systemd + journal） | TESTING.md |

**执行顺序建议**：先 **TC-S*** 环境与资源门禁 → 再 **TC-C08**（幂等）→ **TC-C01/C02** → 其余按优先级。

**数据与清理**：系统测试在 104 上执行须使用**测试账号**；任务输出写入可清理路径；执行后运行归档/删除脚本，避免占满 95% 磁盘。

**与单元/集成测试分工**：单元测试（§2）验证模块与表逻辑；集成测试（§3）验证 Agent 流水线与 DB；系统测试验证**真实进程、真实 systemd、真实磁盘约束**下的验收标准。

## 7. 总结

本文档提供了AI小说生成Agent系统的完整测试方案，包括：

### 7.1 测试覆盖
1. **单元测试**：精细到接口级别，覆盖所有模块的公开接口
2. **集成测试**：验证7个Agent的协作和完整流水线
3. **性能测试**：验证3章批次机制的性能指标
4. **错误恢复测试**：测试系统的健壮性和恢复能力

### 7.2 关键测试点
1. **TrendAgent**：题材库管理、热度计算、趋势预测
2. **PlannerAgent**：3章周期审核、加权随机题材选择
3. **WriterAgent**：3章批次生成、上下文管理、一致性检查
4. **AuditorAgent**：量化指标计算、置信度评分

### 7.3 质量保障
1. **代码覆盖率**：≥85%
2. **接口测试**：100%公开接口覆盖
3. **性能达标**：满足需求文档的性能指标
4. **错误处理**：所有错误类型都有恢复策略

### 7.4 自动化执行
1. **本地测试脚本**：一键执行完整测试套件（不拉起 Redis）
2. **持续集成**：GitHub Actions 使用 **PostgreSQL 16** 服务容器，与生产存储栈一致
3. **测试报告**：自动生成详细测试报告
4. **质量门禁**：代码覆盖率、性能基准检查（区分 **104 档** 与 **扩展档**）
5. **系统测试**：发版前在 104 或等价环境执行 `docs/TESTING.md` 中 TC-S*、TC-C*（§6.3）

本测试文档确保系统在 **104 裸机资源约束** 与模块化单体架构下，仍能满足需求与设计中的质量与验收标准。
