# AI小说生成Agent系统 - 测试文档

## 文档概述

本文档基于需求文档、概要设计文档和详细设计文档，定义AI小说生成Agent系统的完整测试策略。包括单元测试（精细到接口级别）、集成测试、性能测试和部署测试。

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
| 集成测试 | Agent间协作 | 数据流、状态转换、错误传播 | 端到端流程100%通过 |
| 性能测试 | 关键路径 | 响应时间、资源使用、并发能力 | 满足性能需求指标 |
| 部署测试 | 生产环境 | 安装、配置、监控、备份 | 一键部署成功 |

### 1.3 测试环境
```yaml
测试环境:
  开发环境:
    - 位置: 本地开发机
    - 用途: 单元测试、接口测试
    - 数据: 模拟数据、测试数据库
  
  集成环境:
    - 位置: 测试服务器
    - 用途: 集成测试、性能测试
    - 数据: 真实数据、完整数据库
  
  生产环境:
    - 位置: 104.244.90.202:9000
    - 用途: 部署验证、监控测试
    - 数据: 生产数据备份
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

## 4. 性能测试设计

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
        
        # 内存要求：批次间内存增长不超过100MB
        assert max_memory < 100, f"内存增长过高: {max_memory:.2f}MB"
        
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
        """测试并发批次性能"""
        from app.core.pipeline import PipelineController
        
        # 配置
        config = {
            "max_concurrent_tasks": 3,
            "agents": {
                "writer": {
                    "batch_size": 3,
                    "max_workers": 3
                }
            }
        }
        
        controller = PipelineController(config)
        
        # 创建并发任务
        tasks = []
        start_time = time.time()
        
        for i in range(5):  # 5个并发任务
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
        
        # 性能断言
        assert successful >= 3, "应该至少成功3个任务"
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
      # 如果需要数据库或其他服务
      redis:
        image: redis
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
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
    
    - name: 运行集成测试
      run: |
        pytest tests/integration/ -v \
          -m "integration" \
          --junitxml=test-results/integration.xml
      env:
        PYTHONPATH: ${{ github.workspace }}/backend
        TEST_MODE: "true"
        MOCK_LLM: "true"
    
    - name: 运行性能测试
      run: |
        pytest tests/performance/ -v \
          -m "performance" \
          --junitxml=test-results/performance.xml
      env:
        PYTHONPATH: ${{ github.workspace }}/backend
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
        "memory_limit_mb": 650,
        "cpu_usage_percent": 80
      }
    },
    "concurrent_tasks": {
      "3_concurrent": {
        "throughput_tasks_per_hour": 20,
        "response_time_seconds": 180,
        "error_rate_percent": 5
      }
    },
    "memory_usage": {
      "peak_memory_mb": 650,
      "average_memory_mb": 450,
      "memory_leak_per_hour_mb": 50
    }
  }
}
```

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
1. **本地测试脚本**：一键执行完整测试套件
2. **持续集成**：GitHub Actions自动测试
3. **测试报告**：自动生成详细测试报告
4. **质量门禁**：代码覆盖率、性能基准检查

本测试文档确保系统按照需求文档和设计文档的要求，实现高质量、高性能、高可靠的AI小说生成Agent系统。
