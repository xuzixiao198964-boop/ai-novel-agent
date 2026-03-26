# AI小说生成Agent系统 - 详细设计文档

## 1. TrendAgent详细设计

### 1.1 模块结构
```
backend/app/agents/trend/
├── __init__.py
├── main.py                    # 主执行入口
├── data_collector.py          # 数据采集模块
├── genre_analyzer.py          # 题材分析模块
├── trend_predictor.py         # 趋势预测模块
├── genre_library.py           # 题材库管理
├── cache_manager.py           # 缓存管理
├── output_formatter.py        # 输出格式化
└── utils/
    ├── http_client.py         # HTTP客户端
    ├── text_similarity.py     # 文本相似度计算
    └── time_utils.py          # 时间处理工具
```

### 1.2 数据采集模块设计

#### 1.2.1 类定义
```python
class DataCollector:
    def __init__(self, config):
        self.config = config
        self.platforms = {
            "qidian": QidianCollector(),
            "jinjiang": JinjiangCollector(),
            "fanqie": FanqieCollector(),
            "zongheng": ZonghengCollector()
        }
        self.cache = CacheManager(ttl=3600)  # 1小时缓存
    
    async def collect_daily_data(self):
        """每日数据采集主函数"""
        results = {}
        
        # 并行采集各平台数据
        async with asyncio.TaskGroup() as tg:
            for platform_name, collector in self.platforms.items():
                task = tg.create_task(
                    self._collect_platform_data(platform_name, collector)
                )
                results[platform_name] = task
        
        # 合并和去重
        merged_data = self._merge_platform_data(results)
        
        # 数据清洗和验证
        cleaned_data = self._clean_and_validate(merged_data)
        
        return cleaned_data
    
    async def _collect_platform_data(self, platform_name, collector):
        """采集单个平台数据"""
        try:
            # 检查缓存
            cache_key = f"{platform_name}_daily_{datetime.now().date()}"
            cached = self.cache.get(cache_key)
            if cached:
                return cached
            
            # 执行采集
            data = await collector.collect(
                categories=["hot", "new", "rising"],
                limit_per_category=50
            )
            
            # 缓存结果
            self.cache.set(cache_key, data)
            
            return data
        except Exception as e:
            logger.error(f"采集{platform_name}数据失败: {e}")
            return self._get_fallback_data(platform_name)
```

#### 1.2.2 平台采集器接口
```python
class BasePlatformCollector(ABC):
    @abstractmethod
    async def collect(self, categories, limit_per_category):
        """采集平台数据"""
        pass
    
    @abstractmethod
    def parse_html(self, html_content):
        """解析HTML内容"""
        pass
    
    @abstractmethod
    def extract_novel_info(self, element):
        """提取小说信息"""
        pass

class QidianCollector(BasePlatformCollector):
    def __init__(self):
        self.base_url = "https://www.qidian.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
    
    async def collect(self, categories, limit_per_category):
        """采集起点数据"""
        data = []
        
        for category in categories:
            url = f"{self.base_url}/rank/{category}"
            
            try:
                # 使用代理和随机延迟避免反爬
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                async with httpx.AsyncClient(
                    headers=self.headers,
                    timeout=30.0,
                    follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    # 解析HTML
                    novels = self.parse_html(response.text)
                    
                    # 提取详细信息
                    for novel in novels[:limit_per_category]:
                        novel_info = self.extract_novel_info(novel)
                        novel_info["platform"] = "qidian"
                        novel_info["category"] = category
                        data.append(novel_info)
                        
            except Exception as e:
                logger.warning(f"采集起点{category}分类失败: {e}")
                continue
        
        return data
```

### 1.3 题材库管理模块

#### 1.3.1 数据库设计
```sql
-- genre_library.db 数据库设计
CREATE TABLE genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- 题材名称
    category TEXT,                       -- 一级分类
    subcategory TEXT,                    -- 二级标签
    description TEXT,                    -- 题材描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE genre_heat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_id INTEGER NOT NULL,
    date DATE NOT NULL,
    platform TEXT NOT NULL,              -- 平台名称
    read_count INTEGER DEFAULT 0,        -- 阅读量
    discuss_count INTEGER DEFAULT 0,     -- 讨论量
    collect_count INTEGER DEFAULT 0,     -- 收藏量
    share_count INTEGER DEFAULT 0,       -- 分享量
    heat_index REAL DEFAULT 0.0,         -- 综合热度指数
    reader_age_distribution JSON,        -- 年龄分布
    reader_gender_ratio JSON,            -- 性别比例
    FOREIGN KEY (genre_id) REFERENCES genres(id),
    UNIQUE(genre_id, date, platform)
);

CREATE TABLE genre_similarity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_id_1 INTEGER NOT NULL,
    genre_id_2 INTEGER NOT NULL,
    similarity_score REAL NOT NULL,      -- 相似度分数(0-1)
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (genre_id_1) REFERENCES genres(id),
    FOREIGN KEY (genre_id_2) REFERENCES genres(id),
    UNIQUE(genre_id_1, genre_id_2)
);

CREATE TABLE genre_vectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_id INTEGER NOT NULL UNIQUE,
    vector BLOB NOT NULL,                -- 文本向量(768维float32)
    vector_model TEXT DEFAULT 'sentence-bert',
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (genre_id) REFERENCES genres(id)
);
```

#### 1.3.2 题材库管理类
```python
class GenreLibrary:
    def __init__(self, db_path="data/genre_library.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.vector_model = None
        
    def initialize(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # 创建表
        with open("schema.sql", "r", encoding="utf-8") as f:
            schema = f.read()
        self.conn.executescript(schema)
        
        # 加载向量模型
        self.vector_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # 初始化默认题材
        self._initialize_default_genres()
    
    def add_daily_heat_data(self, platform_data):
        """添加每日热度数据"""
        cursor = self.conn.cursor()
        today = datetime.now().date()
        
        for platform, novels in platform_data.items():
            for novel in novels:
                # 获取或创建题材
                genre_id = self._get_or_create_genre(novel["genre"])
                
                # 计算综合热度
                heat_index = self._calculate_heat_index(novel)
                
                # 插入热度数据
                cursor.execute("""
                    INSERT OR REPLACE INTO genre_heat 
                    (genre_id, date, platform, read_count, discuss_count, 
                     collect_count, share_count, heat_index, reader_age_distribution, 
                     reader_gender_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    genre_id, today, platform,
                    novel.get("read_count", 0),
                    novel.get("discuss_count", 0),
                    novel.get("collect_count", 0),
                    novel.get("share_count", 0),
                    heat_index,
                    json.dumps(novel.get("reader_age", {})),
                    json.dumps(novel.get("reader_gender", {}))
                ))
        
        self.conn.commit()
    
    def calculate_similarity(self):
        """计算题材相似度"""
        cursor = self.conn.cursor()
        
        # 获取所有题材
        cursor.execute("SELECT id, name, description FROM genres")
        genres = cursor.fetchall()
        
        # 计算向量
        genre_vectors = {}
        for genre in genres:
            text = f"{genre['name']} {genre['description']}"
            vector = self.vector_model.encode(text)
            genre_vectors[genre['id']] = vector
        
        # 计算相似度矩阵
        similarities = []
        genre_ids = list(genre_vectors.keys())
        
        for i in range(len(genre_ids)):
            for j in range(i + 1, len(genre_ids)):
                id1, id2 = genre_ids[i], genre_ids[j]
                vec1, vec2 = genre_vectors[id1], genre_vectors[id2]
                
                # 计算余弦相似度
                similarity = cosine_similarity(
                    vec1.reshape(1, -1), 
                    vec2.reshape(1, -1)
                )[0][0]
                
                similarities.append((id1, id2, similarity))
        
        # 批量插入
        cursor.executemany("""
            INSERT OR REPLACE INTO genre_similarity 
            (genre_id_1, genre_id_2, similarity_score)
            VALUES (?, ?, ?)
        """, similarities)
        
        self.conn.commit()
    
    def get_hot_genres(self, days=7, limit=20):
        """获取热门题材"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                g.id, g.name, g.category, g.subcategory,
                AVG(gh.heat_index) as avg_heat,
                COUNT(DISTINCT gh.date) as data_days,
                SUM(gh.read_count) as total_read,
                SUM(gh.discuss_count) as total_discuss
            FROM genres g
            JOIN genre_heat gh ON g.id = gh.genre_id
            WHERE gh.date >= date('now', ?)
            GROUP BY g.id, g.name, g.category, g.subcategory
            ORDER BY avg_heat DESC
            LIMIT ?
        """
        
        cursor.execute(query, (f"-{days} days", limit))
        results = cursor.fetchall()
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "heat_index": row["avg_heat"],
                "data_coverage": row["data_days"] / days,
                "total_read": row["total_read"],
                "total_discuss": row["total_discuss"]
            }
            for row in results
        ]
    
    def apply_heat_decay(self):
        """应用热度衰减"""
        cursor = self.conn.cursor()
        
        # 获取所有题材的最新热度
        cursor.execute("""
            SELECT genre_id, MAX(date) as latest_date
            FROM genre_heat
            GROUP BY genre_id
        """)
        
        for row in cursor.fetchall():
            genre_id = row["genre_id"]
            latest_date = datetime.strptime(row["latest_date"], "%Y-%m-%d").date()
            days_passed = (datetime.now().date() - latest_date).days
            
            if days_passed > 0:
                # 应用指数衰减
                decay_factor = math.exp(-0.05 * days_passed)
                
                # 更新热度
                cursor.execute("""
                    UPDATE genre_heat
                    SET heat_index = heat_index * ?
                    WHERE genre_id = ? AND date = ?
                """, (decay_factor, genre_id, row["latest_date"]))
        
        self.conn.commit()
    
    def remove_inactive_genres(self, inactive_days=30):
        """移除不活跃题材"""
        cursor = self.conn.cursor()
        
        # 找出30天内没有热度的题材
        cursor.execute("""
            SELECT g.id, g.name
            FROM genres g
            LEFT JOIN genre_heat gh ON g.id = gh.genre_id 
                AND gh.date >= date('now', ?)
            WHERE gh.genre_id IS NULL
        """, (f"-{inactive_days} days",))
        
        inactive_genres = cursor.fetchall()
        
        # 移入历史表（实际实现中应有历史表）
        for genre in inactive_genres:
            logger.info(f"移除不活跃题材: {genre['name']}")
            # 这里可以备份到历史表
        
        return inactive_genres
```

### 1.4 趋势预测模块

#### 1.4.1 趋势分析算法
```python
class TrendPredictor:
    def __init__(self):
        self.regression_model = LinearRegression()
        self.time_series_model = None
        
    def analyze_trends(self, heat_data, window_sizes=[7, 30, 90]):
        """分析多时间窗口趋势"""
        trends = {}
        
        for window in window_sizes:
            # 计算移动平均
            ma_trend = self._calculate_moving_average(heat_data, window)
            
            # 计算增长率
            growth_rate = self._calculate_growth_rate(ma_trend)
            
            # 趋势方向判断
            trend_direction = self._determine_trend_direction(growth_rate)
            
            trends[f"{window}_day"] = {
                "moving_average": ma_trend,
                "growth_rate": growth_rate,
                "direction": trend_direction,
                "stability": self._calculate_stability(ma_trend)
            }
        
        return trends
    
    def predict_future_trend(self, historical_data, days_ahead=30):
        """预测未来趋势"""
        # 准备时间序列数据
        dates = [d["date"] for d in historical_data]
        values = [d["heat_index"] for d in historical_data]
        
        # 转换为数值索引
        x = np.arange(len(dates)).reshape(-1, 1)
        y = np.array(values)
        
        # 训练线性回归模型
        self.regression_model.fit(x, y)
        
        # 预测未来值
        future_x = np.arange(len(dates), len(dates) + days_ahead).reshape(-1, 1)
        future_y = self.regression_model.predict(future_x)
        
        # 计算置信区间
        confidence = self._calculate_confidence_interval(x, y, future_x)
        
        return {
            "predictions": [
                {
                    "date": (datetime.strptime(dates[-1], "%Y-%m-%d") + 
                            timedelta(days=i+1)).strftime("%Y-%m-%d"),
                    "predicted_heat": float(future_y[i]),
                    "confidence_low": float(confidence[0][i]),
                    "confidence_high": float(confidence[1][i])
                }
                for i in range(days_ahead)
            ],
            "r_squared": self.regression_model.score(x, y),
            "trend_slope": float(self.regression_model.coef_[0])
        }
    
    def identify_emerging_genres(self, heat_data, min_growth_rate=0.2):
        """识别新兴题材"""
        emerging = []
        
        for genre_id, data in heat_data.items():
            if len(data) < 7:  # 至少需要7天数据
                continue
            
            # 计算最近7天增长率
            recent_data = data[-7:]
            growth = self._calculate_growth_rate(recent_data)
            
            if growth >= min_growth_rate:
                # 检查加速度（增长是否在加速）
                acceleration = self._calculate_acceleration(recent_data)
                
                # 检查稳定性
                stability = self._calculate_stability(recent_data)
                
                emerging.append({
                    "genre_id": genre_id,
                    "growth_rate": growth,
                    "acceleration": acceleration,
                    "stability": stability,
                    "current_heat": recent_data[-1]["heat_index"],
                    "potential_score": self._calculate_potential_score(
                        growth, acceleration, stability
                    )
                })
        
        # 按潜力分数排序
        emerging.sort(key=lambda x: x["potential_score"], reverse=True)
        
        return emerging[:10]  # 返回前10个新兴题材
```

### 1.5 输出格式化模块

#### 1.5.1 JSON输出格式
```python
class OutputFormatter:
    def format_trend_analysis(self, analysis_data):
        """格式化趋势分析报告"""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "data_sources": analysis_data.get("sources", []),
                "analysis_period": analysis_data.get("period", "7d")
            },
            "hot_genres": self._format_hot_genres(analysis_data["hot_genres"]),
            "emerging_genres": self._format_emerging_genres(analysis_data["emerging_genres"]),
            "trend_analysis": {
                "short_term": analysis_data.get("trends", {}).get("7_day", {}),
                "medium_term": analysis_data.get("trends", {}).get("30_day", {}),
                "long_term": analysis_data.get("trends", {}).get("90_day", {})
            },
            "reader_analysis": {
                "demographics": analysis_data.get("reader_demographics", {}),
                "behavior_patterns": analysis_data.get("reader_behavior", {}),
                "preference_insights": analysis_data.get("preference_insights", {})
            },
            "market_analysis": {
                "saturation_level": analysis_data.get("market_saturation", 0.0),
                "opportunity_areas": analysis_data.get("opportunities", []),
                "competitive_landscape": analysis_data.get("competition", {})
            },
            "recommendations": {
                "chapter_count": {
                    "min": analysis_data.get("chapter_min", 12),
                    "recommended": analysis_data.get("chapter_recommended", 18),
                    "max": analysis_data.get("chapter_max", 30),
                    "rationale": analysis_data.get("chapter_rationale", "")
                },
                "genre_selection": analysis_data.get("genre_recommendations", []),
                "timing_suggestions": analysis_data.get("timing_suggestions", [])
            },
            "predictions": {
                "next_7_days": analysis_data.get("predictions", {}).get("7_day", []),
                "next_30_days": analysis_data.get("predictions", {}).get("30_day", []),
                "next_90_days": analysis_data.get("predictions", {}).get("90_day", [])
            }
        }
        
        return report
    
    def _format_hot_genres(self, hot_genres):
        """格式化热门题材数据"""
        formatted = []
        
        for genre in hot_genres:
            formatted.append({
                "rank": genre.get("rank", 0),
                "name": genre["name"],
                "category": genre.get("category", ""),
                "subcategory": genre.get("subcategory", ""),
                "heat_index": round(genre.get("heat_index", 0.0), 2),
                "daily_growth": round(genre.get("daily_growth", 0.0), 2),
                "stability": round(genre.get("stability", 0.0), 2),
                "reader_profile": {
                    "age_distribution": genre.get("reader_age", {}),
                    "gender_ratio": genre.get("reader_gender", {}),
                    "reading_habits": genre.get("reading_habits", {})
                },
                "market_metrics": {
                    "saturation": genre.get("market_saturation", 0.0),
                    "competition": genre.get("competition_level", 0.0),
                    "opportunity": genre.get("opportunity_score", 0.0)
                }
            })
        
        return formatted
```

## 2. PlannerAgent详细设计

### 2.1 3章周期审核机制实现

#### 2.1.1 核心控制器
```python
class ThreeChapterCycleController:
    def __init__(self, config):
        self.config = config
        self.batch_size = 3
        self.max_retries = 3
        self.fixed_settings = {}
        self.review_history = []
        
    async def execute_planning(self, total_chapters, trend_data, style_data):
        """执行完整策划流程"""
        # 1. 题材选择
        selected_genres = self._select_genres(trend_data)
        
        # 2. 故事总纲生成
        story_spine = await self._generate_story_spine(
            selected_genres, style_data, total_chapters
        )
        
        # 3. 章节大纲生成（3章周期）
        chapter_outlines = []
        current_chapter = 1
        
        while current_chapter <= total_chapters:
            batch_end = min(current_chapter + self.batch_size - 1, total_chapters)
            
            # 生成当前批次大纲
            batch_outlines = await self._generate_batch_outlines(
                current_chapter, batch_end, story_spine
            )
            
            # 深度审核当前批次
            review_result = await self._deep_review_batch(
                batch_outlines, current_chapter == 1  # 首次审核更严格
            )
            
            if review_result["pass"]:
                # 固化设定（如果是前3章）
                if current_chapter == 1:
                    self.fixed_settings = self._extract_fixed_settings(batch_outlines)
                
                # 保存通过的大纲
                chapter_outlines.extend(batch_outlines)
                current_chapter = batch_end + 1
                
                # 记录审核历史
                self.review_history.append({
                    "batch": f"{current_chapter}-{batch_end}",
                    "result": "passed",
                    "score": review_result["score"],
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # 修订循环
                revised = await self._revision_cycle(
                    batch_outlines, review_result, current_chapter
                )
                
                if revised["success"]:
                    chapter_outlines.extend(revised["outlines"])
                    current_chapter = batch_end + 1
                else:
                    # 修订失败，需要人工干预
                    raise PlanningError(
                        f"批次{current_chapter}-{batch_end}修订失败，需要人工干预"
                    )
        
        return {
            "story_spine": story_spine,
            "chapter_outlines": chapter_outlines,
            "fixed_settings": self.fixed_settings,
            "review_history": self.review_history,
            "total_chapters": total_chapters
        }
    
    async def _deep_review_batch(self, batch_outlines, is_first_batch=False):
        """深度审核批次大纲"""
        # 准备审核数据
        review_data = {
            "outlines": batch_outlines,
            "fixed_settings": self.fixed_settings if not is_first_batch else {},
            "is_first_batch": is_first_batch
        }
        
        # 调用LLM审核
        prompt = self._build_review_prompt(review_data)
        llm_response = await llm.chat_json(prompt, temperature=0.0)
        
        # 计算审核分数
        scores = self._calculate_review_scores(llm_response, is_first_batch)
        total_score = self._calculate_total_score(scores, is_first_batch)
        
        # 判断是否通过
        pass_threshold = 85 if is_first_batch else 80
        dimension_threshold = 70 if is_first_batch else 60
        
        passed = (
            total_score >= pass_threshold and
            all(score >= dimension_threshold for score in scores.values())
        )
        
        return {
            "pass": passed,
            "total_score": total_score,
            "dimension_scores": scores,
            "llm_feedback": llm_response.get("feedback", ""),
            "specific_issues": llm_response.get("issues", [])
        }
    
    def _calculate_review_scores(self, llm_response, is_first_batch):
        """计算各维度审核分数"""
        weights = {
            "structure": 0.30,      # 结构完整性
            "character": 0.25,      # 人物一致性
            "plot": 0.20,           # 情节逻辑性
            "market": 0.15,         # 市场匹配度
            "style": 0.10           # 风格符合度
        }
        
        if is_first_batch:
            # 首次审核更重视结构和人物
            weights["structure"] = 0.35
            weights["character"] = 0.30
            weights["market"] = 0.10
            weights["style"] = 0.05
        
        scores = {}
        
        for dimension in weights.keys():
            # 从LLM响应中提取维度评分
            dimension_data = llm_response.get(dimension, {})
            raw_score = dimension_data.get("score", 50)  # 默认50分
            
            # 应用权重调整
            adjusted_score = raw_score * weights[dimension]
            scores[dimension] = min(100, adjusted_score * 100 / weights[dimension])
        
        return scores
```

### 2.2 题材选择算法实现

#### 2.2.1 加权随机选择器
```python
class GenreSelector:
    def __init__(self, genre_library):
        self.genre_library = genre_library
        self.recent_creations = []  # 最近创作记录
        self.selection_history = []  # 选择历史
        
    def select_genres(self, trend_data, count=3, avoid_recent=True):
        """选择多个题材（支持多题材融合）"""
        # 获取热门题材
        hot_genres = self.genre_library.get_hot_genres(days=7, limit=50)
        
        if not hot_genres:
            return self._get_fallback_genres(count)
        
        # 计算选择概率
        probabilities = []
        for genre in hot_genres:
            prob = self._calculate_selection_probability(
                genre, trend_data, avoid_recent
            )
            probabilities.append(prob)
        
        # 归一化概率
        total_prob = sum(probabilities)
        if total_prob == 0:
            normalized = [1.0 / len(hot_genres)] * len(hot_genres)
        else:
            normalized = [p / total_prob for p in probabilities]
        
        # 加权随机选择
        selected_indices = np.random.choice(
            len(hot_genres),
            size=min(count, len(hot_genres)),
            p=normalized,
            replace=False
        )
        
        selected = [hot_genres[i] for i in selected_indices]
        
        # 记录选择历史
        self._record_selection(selected)
        
        return selected
    
    def _calculate_selection_probability(self, genre, trend_data, avoid_recent):
        """计算单个题材的选择概率"""
        # 1. 热度权重
        heat_weight = self._calculate_heat_weight(genre, trend_data)
        
        # 2. 创新系数
        innovation_coef = self._calculate_innovation_coefficient(genre)
        
        # 3. 回避系数
        avoidance_coef = self._calculate_avoidance_coefficient(
            genre, avoid_recent
        )
        
        # 4. 多样性系数（鼓励选择不同类别）
        diversity_coef = self._calculate_diversity_coefficient(genre)
        
        # 综合概率
        probability = (
            heat_weight * 
            innovation_coef * 
            avoidance_coef * 
            diversity_coef
        )
        
        return max(0.01, probability)  # 确保最小概率
    
    def _calculate_heat_weight(self, genre, trend_data):
        """计算热度权重"""
        base_heat = genre.get("heat_index", 50)
        
        # 时间衰减
        days_since_update = genre.get("days_since_update", 7)
        decay_factor = math.exp(-0.05 * days_since_update)
        
        # 趋势调整
        trend_adjustment = 1.0
        if genre["name"] in trend_data.get("rising_genres", []):
            trend_adjustment = 1.5  # 上升趋势加成
        elif genre["name"] in trend_data.get("declining_genres", []):
            trend_adjustment = 0.7  # 下降趋势折扣
        
        heat_weight = base_heat * decay_factor * trend_adjustment
        
        # 归一化到0-1范围
        return heat_weight / 100.0
    
    def _calculate_innovation_coefficient(self, genre):
        """计算创新系数"""
        rank = genre.get("rank", 999)
        
        if rank <= 10:
            return 0.7  # 热门题材，避免过度集中
        elif rank <= 30:
            return 1.0  # 稳定题材，平衡选择
        else:
            # 检查是否为新兴题材
            growth_rate = genre.get("daily_growth", 0.0)
            if growth_rate >= 0.2:  # 日增长率≥20%
                return 1.5  # 新兴题材，鼓励尝试
            else:
                return 0.5  # 冷门题材，适度尝试
    
    def _calculate_avoidance_coefficient(self, genre, avoid_recent):
        """计算回避系数"""
        if not avoid_recent:
            return 1.0
        
        genre_name = genre["name"]
        current_time = datetime.now()
        
        # 检查最近创作记录
        for creation in self.recent_creations:
            if creation["genre"] == genre_name:
                days_passed = (current_time - creation["time"]).days
                
                if days_passed < 7:
                    return 0.3  # 7天内创作过，强烈回避
                elif days_passed < 30:
                    return 0.7  # 8-30天内创作过，适度回避
                else:
                    return 1.2  # 30天以上未创作，鼓励选择
        
        # 全新题材
        return 1.5
    
    def _calculate_diversity_coefficient(self, genre):
        """计算多样性系数"""
        category = genre.get("category", "other")
        
        # 检查最近选择的题材类别
        recent_categories = [
            g.get("category", "other") 
            for g in self.selection_history[-5:]  # 最近5次选择
        ]
        
        # 计算当前类别在最近选择中的频率
        category_count = recent_categories.count(category)
        frequency = category_count / len(recent_categories) if recent_categories else 0
        
        # 频率越高，系数越低（鼓励多样性）
        diversity_coef = 1.0 - (frequency * 0.5)
        
        return max(0.5, diversity_coef)  # 确保最小系数
```

### 2.3 多题材融合策略

#### 2.3.1 融合控制器
```python
class GenreFusionController:
    def __init__(self, similarity_threshold=0.7):
        self.similarity_threshold = similarity_threshold
        
    def fuse_genres(self, primary_genre, secondary_genres):
        """融合多个题材"""
        # 验证题材兼容性
        compatible = self._check_compatibility(primary_genre, secondary_genres)
        
        if not compatible["all_compatible"]:
            # 调整或替换不兼容的题材
            secondary_genres = self._adjust_incompatible_genres(
                primary_genre, secondary_genres, compatible["incompatible"]
            )
        
        # 确定融合策略
        fusion_strategy = self._determine_fusion_strategy(
            primary_genre, secondary_genres
        )
        
        # 生成融合后的题材描述
        fused_description = self._generate_fused_description(
            primary_genre, secondary_genres, fusion_strategy
        )
        
        return {
            "primary_genre": primary_genre,
            "secondary_genres": secondary_genres,
            "fusion_strategy": fusion_strategy,
            "fused_description": fused_description,
            "compatibility_score": compatible["overall_score"],
            "innovation_score": self._calculate_innovation_score(
                primary_genre, secondary_genres
            )
        }
    
    def _check_compatibility(self, primary_genre, secondary_genres):
        """检查题材兼容性"""
        incompatible = []
        compatibility_scores = []
        
        for secondary in secondary_genres:
            # 计算相似度
            similarity = self._calculate_genre_similarity(
                primary_genre, secondary
            )
            
            if similarity < 0.3:
                # 相似度过低，可能难以融合
                incompatible.append({
                    "genre": secondary,
                    "similarity": similarity,
                    "reason": "题材差异过大"
                })
                compatibility_scores.append(0.0)
            elif similarity > 0.8:
                # 相似度过高，缺乏创新性
                compatibility_scores.append(0.7)
            else:
                # 适度相似，易于融合
                compatibility_scores.append(0.9)
        
        overall_score = sum(compatibility_scores) / len(compatibility_scores) if compatibility_scores else 0.0
        
        return {
            "all_compatible": len(incompatible) == 0,
            "incompatible": incompatible,
            "compatibility_scores": compatibility_scores,
            "overall_score": overall_score
        }
    
    def _determine_fusion_strategy(self, primary_genre, secondary_genres):
        """确定融合策略"""
        # 分析题材特征
        primary_features = self._extract_genre_features(primary_genre)
        secondary_features = [
            self._extract_genre_features(g) for g in secondary_genres
        ]
        
        # 确定主次关系
        if len(secondary_genres) == 1:
            return {
                "type": "primary_secondary",
                "primary_weight": 0.6,
                "secondary_weight": 0.4,
                "fusion_method": "theme_integration"  # 主题融合
            }
        elif len(secondary_genres) == 2:
            return {
                "type": "primary_with_two_supporting",
                "primary_weight": 0.5,
                "secondary_weights": [0.3, 0.2],
                "fusion_method": "layered_integration"  # 分层融合
            }
        else:
            return {
                "type": "complex_fusion",
                "primary_weight": 0.4,
                "secondary_weights": [0.2] * len(secondary_genres),
                "fusion_method": "modular_integration"  # 模块化融合
            }
```

## 3. WriterAgent详细设计

### 3.1 3章批次生成机制

#### 3.1.1 批次写作控制器
```python
class BatchWritingController:
    def __init__(self, batch_size=3, max_workers=3):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.context_manager = ContextManager()
        self.consistency_checker = ConsistencyChecker()
        self.quality_evaluator = QualityEvaluator()
        
    async def write_batch(self, start_chapter, outlines, previous_chapters=None):
        """生成3章批次"""
        # 准备上下文
        if previous_chapters:
            self.context_manager.update_context(previous_chapters[-self.batch_size:])
        
        # 并行生成章节
        chapters = await self._generate_chapters_parallel(
            start_chapter, outlines
        )
        
        # 批次内一致性检查
        consistency_result = self.consistency_checker.check_batch_consistency(chapters)
        
        if not consistency_result["passed"]:
            # 批次内修订
            chapters = await self._revise_batch_internally(
                chapters, consistency_result["issues"]
            )
        
        # 质量评估
        quality_scores = self.quality_evaluator.evaluate_batch(chapters)
        
        # 更新上下文
        self.context_manager.update_context(chapters)
        
        return {
            "chapters": chapters,
            "batch_info": {
                "start_chapter": start_chapter,
                "end_chapter": start_chapter + len(chapters) - 1,
                "consistency_result": consistency_result,
                "quality_scores": quality_scores,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    async def _generate_chapters_parallel(self, start_chapter, outlines):
        """并行生成多个章节"""
        chapters = []
        
        # 使用线程池并行生成
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for i, outline in enumerate(outlines):
                chapter_num = start_chapter + i
                
                # 准备章节生成参数
                context = self.context_manager.get_context_for_chapter(chapter_num)
                generation_params = self._prepare_generation_params(
                    chapter_num, outline, context
                )
                
                # 提交生成任务
                future = executor.submit(
                    self._generate_single_chapter,
                    generation_params
                )
                futures.append((chapter_num, future))
            
            # 收集结果
            for chapter_num, future in futures:
                try:
                    chapter_content = future.result(timeout=300)  # 5分钟超时
                    chapters.append({
                        "chapter_number": chapter_num,
                        "content": chapter_content,
                        "outline": outlines[chapter_num - start_chapter],
                        "generation_time": datetime.now().isoformat()
                    })
                except TimeoutError:
                    logger.error(f"章节{chapter_num}生成超时")
                    # 使用降级策略生成简单内容
                    fallback_content = self._generate_fallback_content(
                        chapter_num, outlines[chapter_num - start_chapter]
                    )
                    chapters.append({
                        "chapter_number": chapter_num,
                        "content": fallback_content,
                        "outline": outlines[chapter_num - start_chapter],
                        "generation_time": datetime.now().isoformat(),
                        "is_fallback": True
                    })
        
        # 按章节号排序
        chapters.sort(key=lambda x: x["chapter_number"])
        
        return chapters
    
    def _prepare_generation_params(self, chapter_num, outline, context):
        """准备章节生成参数"""
        return {
            "chapter_number": chapter_num,
            "outline": outline,
            "context": context,
            "style_parameters": self.context_manager.get_style_parameters(),
            "character_states": self.context_manager.get_character_states(),
            "plot_progress": self.context_manager.get_plot_progress(),
            "writing_guidelines": self._get_writing_guidelines(chapter_num)
        }
    
    async def _revise_batch_internally(self, chapters, issues):
        """批次内修订"""
        revised_chapters = []
        
        for chapter in chapters:
            chapter_issues = [
                issue for issue in issues 
                if issue["chapter"] == chapter["chapter_number"]
            ]
            
            if chapter_issues:
                # 需要修订
                revised = await self._revise_single_chapter(
                    chapter, chapter_issues
                )
                revised_chapters.append(revised)
            else:
                # 无需修订
                revised_chapters.append(chapter)
        
        # 重新检查一致性
        new_consistency = self.consistency_checker.check_batch_consistency(
            revised_chapters
        )
        
        if new_consistency["passed"]:
            return revised_chapters
        else:
            # 如果仍然有问题，进行二次修订
            return await self._revise_batch_internally(
                revised_chapters, new_consistency["issues"]
            )
```

### 3.2 上下文管理模块

#### 3.2.1 上下文管理器
```python
class ContextManager:
    def __init__(self, context_window_size=3):
        self.context_window_size = context_window_size
        self.recent_chapters = []  # 最近章节内容
        self.character_states = {}  # 人物状态
        self.plot_progress = {}  # 情节进展
        self.style_parameters = {}  # 风格参数
        self.world_building = {}  # 世界观设定
        
    def update_context(self, new_chapters):
        """更新上下文窗口"""
        # 添加新章节
        self.recent_chapters.extend(new_chapters)
        
        # 保持窗口大小
        if len(self.recent_chapters) > self.context_window_size:
            self.recent_chapters = self.recent_chapters[-self.context_window_size:]
        
        # 更新人物状态
        for chapter in new_chapters:
            self._update_character_states(chapter)
        
        # 更新情节进展
        self._update_plot_progress(new_chapters)
        
        # 更新世界观（如果有新设定）
        self._update_world_building(new_chapters)
    
    def get_context_for_chapter(self, chapter_num):
        """获取指定章节的上下文"""
        # 最近章节的摘要
        recent_summaries = [
            self._summarize_chapter(chap) 
            for chap in self.recent_chapters[-self.context_window_size:]
        ]
        
        # 相关人物状态
        relevant_characters = self._get_relevant_characters(chapter_num)
        
        # 相关情节线
        relevant_plots = self._get_relevant_plots(chapter_num)
        
        return {
            "recent_chapters": recent_summaries,
            "character_states": relevant_characters,
            "plot_progress": relevant_plots,
            "world_building": self.world_building,
            "style_parameters": self.style_parameters,
            "chapter_position": self._get_chapter_position(chapter_num)
        }
    
    def _update_character_states(self, chapter):
        """更新人物状态"""
        # 从章节内容中提取人物信息
        character_info = self._extract_character_info(chapter["content"])
        
        for char_name, char_data in character_info.items():
            if char_name not in self.character_states:
                # 新人物
                self.character_states[char_name] = {
                    "first_appearance": chapter["chapter_number"],
                    "traits": char_data.get("traits", {}),
                    "relationships": char_data.get("relationships", {}),
                    "development": []
                }
            
            # 更新状态
            current_state = self.character_states[char_name]
            
            # 记录发展
            development_entry = {
                "chapter": chapter["chapter_number"],
                "actions": char_data.get("actions", []),
                "dialogues": char_data.get("dialogues", []),
                "emotional_state": char_data.get("emotional_state", "neutral"),
                "relationships_changes": char_data.get("relationship_changes", {})
            }
            
            current_state["development"].append(development_entry)
            
            # 更新特征（如果有变化）
            if "trait_changes" in char_data:
                for trait, value in char_data["trait_changes"].items():
                    current_state["traits"][trait] = value
            
            # 更新关系
            if "relationships" in char_data:
                current_state["relationships"].update(char_data["relationships"])
    
    def _update_plot_progress(self, new_chapters):
        """更新情节进展"""
        for chapter in new_chapters:
            # 提取情节元素
            plot_elements = self._extract_plot_elements(chapter["content"])
            
            for plot_id, element in plot_elements.items():
                if plot_id not in self.plot_progress:
                    self.plot_progress[plot_id] = {
                        "type": element["type"],
                        "introduced_in": chapter["chapter_number"],
                        "progress": [],
                        "status": "ongoing"
                    }
                
                # 记录进展
                self.plot_progress[plot_id]["progress"].append({
                    "chapter": chapter["chapter_number"],
                    "development": element["development"],
                    "significance": element["significance"]
                })
                
                # 检查是否解决
                if element.get("resolved", False):
                    self.plot_progress[plot_id]["status"] = "resolved"
                    self.plot_progress[plot_id]["resolved_in"] = chapter["chapter_number"]
```

### 3.3 一致性检查模块

#### 3.3.1 一致性检查器
```python
class ConsistencyChecker:
    def __init__(self):
        self.rules = self._load_consistency_rules()
        
    def check_batch_consistency(self, chapters):
        """检查批次内一致性"""
        issues = []
        
        if len(chapters) < 2:
            return {"passed": True, "issues": issues}
        
        # 检查章节间连续性
        continuity_issues = self._check_chapter_continuity(chapters)
        issues.extend(continuity_issues)
        
        # 检查人物一致性
        character_issues = self._check_character_consistency(chapters)
        issues.extend(character_issues)
        
        # 检查情节逻辑
        plot_issues = self._check_plot_logic(chapters)
        issues.extend(plot_issues)
        
        # 检查时间线
        timeline_issues = self._check_timeline_consistency(chapters)
        issues.extend(timeline_issues)
        
        # 检查设定一致性
        setting_issues = self._check_setting_consistency(chapters)
        issues.extend(setting_issues)
        
        # 计算通过率
        total_checks = len(chapters) * 5  # 5个检查维度
        passed_checks = total_checks - len(issues)
        pass_rate = passed_checks / total_checks if total_checks > 0 else 1.0
        
        passed = pass_rate >= 0.85  # 85%通过率
        
        return {
            "passed": passed,
            "pass_rate": pass_rate,
            "issues": issues,
            "total_checks": total_checks,
            "passed_checks": passed_checks
        }
    
    def _check_chapter_continuity(self, chapters):
        """检查章节连续性"""
        issues = []
        
        for i in range(len(chapters) - 1):
            current = chapters[i]
            next_chap = chapters[i + 1]
            
            # 检查情节衔接
            if not self._check_plot_connection(current, next_chap):
                issues.append({
                    "type": "plot_discontinuity",
                    "severity": "high",
                    "chapters": [current["chapter_number"], next_chap["chapter_number"]],
                    "description": "情节衔接不自然",
                    "suggestion": "增加过渡段落或调整情节顺序"
                })
            
            # 检查时间连续性
            time_gap = self._check_time_gap(current, next_chap)
            if time_gap and time_gap > 7:  # 超过7天的时间跳跃
                issues.append({
                    "type": "time_gap_too_large",
                    "severity": "medium",
                    "chapters": [current["chapter_number"], next_chap["chapter_number"]],
                    "description": f"时间跳跃过大: {time_gap}天",
                    "suggestion": "添加时间过渡说明或调整时间线"
                })
        
        return issues
    
    def _check_character_consistency(self, chapters):
        """检查人物一致性"""
        issues = []
        character_tracker = {}
        
        for chapter in chapters:
            # 提取本章人物信息
            chapter_characters = self._extract_characters_from_chapter(chapter)
            
            for char_name, char_info in chapter_characters.items():
                if char_name not in character_tracker:
                    # 首次出现
                    character_tracker[char_name] = {
                        "first_seen": chapter["chapter_number"],
                        "traits": char_info.get("traits", {}),
                        "last_seen": chapter["chapter_number"],
                        "appearances": [chapter["chapter_number"]]
                    }
                else:
                    # 检查特征一致性
                    tracker = character_tracker[char_name]
                    
                    # 检查特征变化是否合理
                    trait_issues = self._check_trait_consistency(
                        tracker["traits"], char_info.get("traits", {}),
                        chapter["chapter_number"] - tracker["last_seen"]
                    )
                    
                    if trait_issues:
                        issues.extend(trait_issues)
                    
                    # 更新跟踪器
                    tracker["last_seen"] = chapter["chapter_number"]
                    tracker["appearances"].append(chapter["chapter_number"])
                    
                    # 合并特征（取最新值）
                    tracker["traits"].update(char_info.get("traits", {}))
        
        return issues
```

## 4. AuditorAgent详细设计

### 4.1 量化指标计算系统

#### 4.1.1 指标计算器
```python
class MetricsCalculator:
    def __init__(self):
        self.metrics_config = self._load_metrics_config()
        
    def calculate_all_metrics(self, audit_results, ground_truth=None):
        """计算所有量化指标"""
        metrics = {}
        
        # 基础指标
        metrics["precision"] = self.calculate_precision(
            audit_results["identified_issues"],
            ground_truth["actual_issues"] if ground_truth else []
        )
        
        metrics["recall"] = self.calculate_recall(
            audit_results["identified_issues"],
            ground_truth["actual_issues"] if ground_truth else []
        )
        
        metrics["f1_score"] = self.calculate_f1(
            metrics["precision"], metrics["recall"]
        )
        
        # 维度指标
        for dimension in ["plot", "character", "logic", "style", "language"]:
            dimension_metrics = self.calculate_dimension_metrics(
                audit_results, dimension, ground_truth
            )
            metrics[dimension] = dimension_metrics
        
        # 综合指标
        metrics["overall_score"] = self.calculate_overall_score(metrics)
        metrics["confidence_level"] = self.calculate_confidence_level(metrics)
        
        return metrics
    
    def calculate_precision(self, identified_issues, actual_issues):
        """计算准确率"""
        if not identified_issues:
            return 1.0  # 没有识别问题，视为准确
        
        # 匹配识别的问题
        true_positives = 0
        for identified in identified_issues:
            if self._is_true_positive(identified, actual_issues):
                true_positives += 1
        
        precision = true_positives / len(identified_issues)
        
        return precision
    
    def calculate_recall(self, identified_issues, actual_issues):
        """计算召回率"""
        if not actual_issues:
            return 1.0  # 没有实际问题，视为全召回
        
        # 匹配实际问题
        true_positives = 0
        for actual in actual_issues:
            if self._is_identified(actual, identified_issues):
                true_positives += 1
        
        recall = true_positives / len(actual_issues)
        
        return recall
    
    def calculate_f1(self, precision, recall):
        """计算F1分数"""
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * (precision * recall) / (precision + recall)
        return f1
    
    def calculate_dimension_metrics(self, audit_results, dimension, ground_truth):
        """计算维度指标"""
        dimension_issues = [
            issue for issue in audit_results["identified_issues"]
            if issue.get("dimension") == dimension
        ]
        
        if ground_truth:
            dimension_ground_truth = [
                issue for issue in ground_truth["actual_issues"]
                if issue.get("dimension") == dimension
            ]
        else:
            dimension_ground_truth = []
        
        precision = self.calculate_precision(
            dimension_issues, dimension_ground_truth
        )
        recall = self.calculate_recall(
            dimension_issues, dimension_ground_truth
        )
        f1 = self.calculate_f1(precision, recall)
        
        # 计算维度特定指标
        if dimension == "plot":
            additional = self._calculate_plot_specific_metrics(dimension_issues)
        elif dimension == "character":
            additional = self._calculate_character_specific_metrics(dimension_issues)
        elif dimension == "logic":
            additional = self._calculate_logic_specific_metrics(dimension_issues)
        else:
            additional = {}
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "issue_count": len(dimension_issues),
            "additional_metrics": additional
        }
    
    def calculate_overall_score(self, metrics):
        """计算综合评分"""
        weights = {
            "precision": 0.25,
            "recall": 0.25,
            "f1_score": 0.20,
            "plot": 0.10,
            "character": 0.10,
            "logic": 0.05,
            "style": 0.03,
            "language": 0.02
        }
        
        score = 0
        total_weight = 0
        
        for metric_name, weight in weights.items():
            if metric_name in ["precision", "recall", "f1_score"]:
                value = metrics.get(metric_name, 0.0)
                score += value * weight
                total_weight += weight
            elif metric_name in ["plot", "character", "logic", "style", "language"]:
                dimension_metrics = metrics.get(metric_name, {})
                dimension_score = dimension_metrics.get("f1_score", 0.0)
                score += dimension_score * weight
                total_weight += weight
        
        # 归一化到0-100分
        if total_weight > 0:
            normalized_score = (score / total_weight) * 100
        else:
            normalized_score = 0.0
        
        return round(normalized_score, 2)
    
    def calculate_confidence_level(self, metrics):
        """计算置信度等级"""
        overall_score = metrics.get("overall_score", 0.0)
        precision = metrics.get("precision", 0.0)
        recall = metrics.get("recall", 0.0)
        
        if overall_score >= 90 and precision >= 0.95 and recall >= 0.90:
            return "high"
        elif overall_score >= 70 and precision >= 0.85 and recall >= 0.80:
            return "medium"
        else:
            return "low"
```

### 4.2 置信度评分系统

#### 4.2.1 置信度计算器
```python
class ConfidenceCalculator:
    def __init__(self):
        self.confidence_factors = {
            "evidence_strength": 0.30,
            "issue_severity": 0.25,
            "pattern_consistency": 0.20,
            "context_relevance": 0.15,
            "historical_accuracy": 0.10
        }
    
    def calculate_confidence(self, issue, context):
        """计算单个问题的置信度"""
        confidence_scores = {}
        
        # 证据强度
        evidence_score = self._calculate_evidence_score(issue)
        confidence_scores["evidence_strength"] = evidence_score
        
        # 问题严重性
        severity_score = self._calculate_severity_score(issue)
        confidence_scores["issue_severity"] = severity_score
        
        # 模式一致性
        pattern_score = self._calculate_pattern_score(issue, context)
        confidence_scores["pattern_consistency"] = pattern_score
        
        # 上下文相关性
        context_score = self._calculate_context_score(issue, context)
        confidence_scores["context_relevance"] = context_score
        
        # 历史准确性
        history_score = self._calculate_history_score(issue, context)
        confidence_scores["historical_accuracy"] = history_score
        
        # 加权计算总置信度
        total_confidence = 0
        total_weight = 0
        
        for factor, weight in self.confidence_factors.items():
            score = confidence_scores.get(factor, 0.5)  # 默认0.5
            total_confidence += score * weight
            total_weight += weight
        
        final_confidence = total_confidence / total_weight if total_weight > 0 else 0.5
        
        # 确定置信度等级
        confidence_level = self._determine_confidence_level(final_confidence)
        
        return {
            "confidence_score": round(final_confidence, 3),
            "confidence_level": confidence_level,
            "factor_scores": confidence_scores,
            "issue_id": issue.get("id"),
            "calculated_at": datetime.now().isoformat()
        }
    
    def _calculate_evidence_score(self, issue):
        """计算证据强度分数"""
        evidence = issue.get("evidence", [])
        
        if not evidence:
            return 0.3  # 无证据，低置信度
        
        # 评估证据质量
        evidence_scores = []
        for ev in evidence:
            score = self._evaluate_single_evidence(ev)
            evidence_scores.append(score)
        
        # 取平均分
        avg_score = sum(evidence_scores) / len(evidence_scores)
        
        # 考虑证据数量
        quantity_factor = min(1.0, len(evidence) / 5.0)  # 最多5个证据
        
        final_score = avg_score * quantity_factor
        
        return min(1.0, final_score)
    
    def _evaluate_single_evidence(self, evidence):
        """评估单个证据"""
        evidence_type = evidence.get("type", "text")
        
        if evidence_type == "direct_text":
            # 直接文本证据
            text = evidence.get("text", "")
            relevance = evidence.get("relevance", 0.5)
            
            # 文本长度和明确性
            if len(text) > 50:
                length_factor = 1.0
            elif len(text) > 20:
                length_factor = 0.8
            else:
                length_factor = 0.5
            
            return relevance * length_factor
            
        elif evidence_type == "pattern":
            # 模式证据
            pattern_strength = evidence.get("strength", 0.5)
            occurrences = evidence.get("occurrences", 1)
            
            # 出现次数越多，置信度越高
            occurrence_factor = min(1.0, occurrences / 3.0)
            
            return pattern_strength * occurrence_factor
            
        elif evidence_type == "contradiction":
            # 矛盾证据
            source_a = evidence.get("source_a", {})
            source_b = evidence.get("source_b", {})
            
            # 检查来源可靠性
            reliability_a = source_a.get("reliability", 0.5)
            reliability_b = source_b.get("reliability", 0.5)
            
            avg_reliability = (reliability_a + reliability_b) / 2
            
            # 矛盾明显程度
            clarity = evidence.get("clarity", 0.5)
            
            return avg_reliability * clarity
            
        else:
            # 其他类型证据
            return evidence.get("confidence", 0.5)
    
    def _calculate_severity_score(self, issue):
        """计算问题严重性分数"""
        severity = issue.get("severity", "medium")
        
        severity_map = {
            "critical": 1.0,   # 严重问题，高置信度
            "high": 0.8,       # 重要问题，较高置信度
            "medium": 0.6,     # 中等问题，中等置信度
            "low": 0.4,        # 轻微问题，较低置信度
            "minor": 0.2       # 微小问题，低置信度
        }
        
        return severity_map.get(severity, 0.6)
    
    def _determine_confidence_level(self, confidence_score):
        """确定置信度等级"""
        if confidence_score >= 0.9:
            return "high"
        elif confidence_score >= 0.7:
            return "medium"
        elif confidence_score >= 0.5:
            return "low"
        else:
            return "very_low"
```

## 5. 系统集成详细设计

### 5.1 任务流水线状态机

#### 5.1.1 状态机设计
```python
class PipelineStateMachine:
    def __init__(self):
        self.states = {
            "created": self._state_created,
            "trend_analysis": self._state_trend_analysis,
            "style_analysis": self._state_style_analysis,
            "planning": self._state_planning,
            "writing": self._state_writing,
            "polishing": self._state_polishing,
            "auditing": self._state_auditing,
            "revising": self._state_revising,
            "completed": self._state_completed,
            "failed": self._state_failed,
            "paused": self._state_paused
        }
        
        self.transitions = {
            "created": ["trend_analysis", "failed"],
            "trend_analysis": ["style_analysis", "failed"],
            "style_analysis": ["planning", "failed"],
            "planning": ["writing", "revising", "failed"],
            "writing": ["polishing", "revising", "failed"],
            "polishing": ["auditing", "revising", "failed"],
            "auditing": ["completed", "revising", "failed"],
            "revising": ["writing", "polishing", "auditing", "failed"],
            "completed": [],
            "failed": ["retrying", "abandoned"],
            "paused": ["resuming", "abandoned"]
        }
    
    async def transition(self, current_state, event, task_data):
        """执行状态转换"""
        # 检查转换是否允许
        allowed_transitions = self.transitions.get(current_state, [])
        if event not in allowed_transitions:
            raise StateTransitionError(
                f"不允许从{current_state}转换到{event}"
            )
        
        # 执行状态处理函数
        handler = self.states.get(event)
        if not handler:
            raise StateTransitionError(f"未知状态: {event}")
        
        try:
            result = await handler(task_data)
            return {
                "success": True,
                "new_state": event,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"状态{event}处理失败: {e}")
            return {
                "success": False,
                "new_state": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _state_planning(self, task_data):
        """策划状态处理"""
        planner = PlannerAgent()
        
        # 获取趋势和风格数据
        trend_result = task_data.get("trend_result")
        style_result = task_data.get("style_result")
        
        if not trend_result or not style_result:
            raise MissingDependencyError("缺少趋势或风格数据")
        
        # 执行策划
        planning_result = await planner.execute(
            task_id=task_data["task_id"],
            trend_data=trend_result,
            style_data=style_result,
            total_chapters=task_data.get("chapter_count", 18)
        )
        
        # 检查是否需要修订
        if planning_result.get("needs_revision"):
            return {
                "next_state": "revising",
                "result": planning_result,
                "revision_reason": "策划审核未通过"
            }
        else:
            return {
                "next_state": "writing",
                "result": planning_result
            }
    
    async def _state_writing(self, task_data):
        """写作状态处理"""
        writer = WriterAgent()
        
        # 获取策划结果
        planning_result = task_data.get("planning_result")
        if not planning_result:
            raise MissingDependencyError("缺少策划数据")
        
        # 执行写作
        writing_result = await writer.execute(
            task_id=task_data["task_id"],
            outlines=planning_result["chapter_outlines"],
            batch_size=3  # 3章批次
        )
        
        # 检查批次质量
        batch_quality = writing_result.get("batch_quality", {})
        if batch_quality.get("needs_revision"):
            return {
                "next_state": "revising",
                "result": writing_result,
                "revision_reason": "批次质量未达标"
            }
        else:
            return {
                "next_state": "polishing",
                "result": writing_result
            }
```

### 5.2 错误恢复系统

#### 5.2.1 错误处理器
```python
class ErrorRecoverySystem:
    def __init__(self, max_retries=3, backoff_factor=2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.error_history = {}
        
    async def handle_error(self, error, context):
        """处理错误并决定恢复策略"""
        error_type = self._classify_error(error)
        error_id = self._generate_error_id(error, context)
        
        # 记录错误
        self._record_error(error_id, error_type, error, context)
        
        # 获取恢复策略
        recovery_strategy = self._get_recovery_strategy(
            error_type, error_id, context
        )
        
        # 执行恢复
        recovery_result = await self._execute_recovery(
            recovery_strategy, context
        )
        
        return {
            "error_id": error_id,
            "error_type": error_type,
            "recovery_strategy": recovery_strategy,
            "recovery_result": recovery_result,
            "can_continue": recovery_result.get("success", False)
        }
    
    def _classify_error(self, error):
        """错误分类"""
        error_str = str(error).lower()
        
        if any(word in error_str for word in ["timeout", "timed out", "time out"]):
            return "timeout"
        elif any(word in error_str for word in ["network", "connection", "http"]):
            return "network"
        elif any(word in error_str for word in ["parse", "json", "format"]):
            return "parse"
        elif any(word in error_str for word in ["memory", "resource", "disk"]):
            return "resource"
        elif any(word in error_str for word in ["llm", "api", "service"]):
            return "service"
        else:
            return "unknown"
    
    def _get_recovery_strategy(self, error_type, error_id, context):
        """获取恢复策略"""
        # 检查错误历史
        error_count = self.error_history.get(error_id, {}).get("count", 0)
        
        if error_count >= self.max_retries:
            return {
                "action": "escalate",
                "reason": f"达到最大重试次数: {error_count}",
                "requires_human": True
            }
        
        # 根据错误类型选择策略
        strategies = {
            "timeout": {
                "action": "retry",
                "max_retries": 3,
                "backoff": self.backoff_factor,
                "adjust_timeout": True
            },
            "network": {
                "action": "retry",
                "max_retries": 5,
                "backoff": self.backoff_factor * 1.5,
                "use_fallback": True
            },
            "parse": {
                "action": "retry",
                "max_retries": 2,
                "backoff": 1.0,
                "adjust_parsing": True
            },
            "resource": {
                "action": "wait_and_retry",
                "wait_time": 60,  # 等待60秒
                "max_retries": 2,
                "reduce_load": True
            },
            "service": {
                "action": "switch_provider",
                "fallback_provider": "openai",  # 切换到备用提供商
                "max_retries": 2
            },
            "unknown": {
                "action": "retry",
                "max_retries": 1,
                "backoff": 1.0,
                "log_details": True
            }
        }
        
        strategy = strategies.get(error_type, strategies["unknown"])
        strategy["retry_count"] = error_count + 1
        
        return strategy
    
    async def _execute_recovery(self, strategy, context):
        """执行恢复"""
        action = strategy.get("action")
        
        if action == "retry":
            return await self._execute_retry(strategy, context)
        elif action == "wait_and_retry":
            return await self._execute_wait_and_retry(strategy, context)
        elif action == "switch_provider":
            return await self._execute_switch_provider(strategy, context)
        elif action == "escalate":
            return await self._execute_escalation(strategy, context)
        else:
            return {"success": False, "reason": f"未知恢复动作: {action}"}
    
    async def _execute_retry(self, strategy, context):
        """执行重试"""
        retry_count = strategy.get("retry_count", 1)
        max_retries = strategy.get("max_retries", 3)
        backoff = strategy.get("backoff", 2.0)
        
        if retry_count > max_retries:
            return {
                "success": False,
                "reason": f"达到最大重试次数: {retry_count}/{max_retries}"
            }
        
        # 计算等待时间（指数退避）
        wait_time = backoff ** (retry_count - 1)
        
        logger.info(f"第{retry_count}次重试，等待{wait_time:.1f}秒")
        await asyncio.sleep(wait_time)
        
        # 调整参数（如果需要）
        adjusted_context = self._adjust_context_for_retry(context, strategy)
        
        return {
            "success": True,
            "action": "retry",
            "retry_number": retry_count,
            "wait_time": wait_time,
            "adjusted_context": adjusted_context
        }
```

## 6. 部署与配置详细设计

### 6.1 服务器环境配置

#### 6.1.1 系统服务配置
```ini
# /etc/systemd/system/ai-novel-agent.service
[Unit]
Description=AI Novel Agent System
After=network.target
Requires=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ai-novel-agent
Environment="PATH=/opt/ai-novel-agent/venv/bin"
Environment="PYTHONPATH=/opt/ai-novel-agent/backend"
Environment="LOG_LEVEL=INFO"
Environment="DATA_DIR=/opt/ai-novel-agent/data"
Environment="CACHE_DIR=/opt/ai-novel-agent/cache"

# 主服务
ExecStart=/opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 9000 \
    --workers 4 \
    --log-level info

# 定时任务服务（题材库每日更新）
ExecStartPost=/opt/ai-novel-agent/venv/bin/python -m backend.scripts.daily_update

# 健康检查
ExecStartPost=/opt/ai-novel-agent/venv/bin/python -m backend.scripts.health_check

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-novel-agent

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096
MemoryMax=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

#### 6.1.2 目录结构配置
```bash
# 创建完整的目录结构
/opt/ai-novel-agent/
├── backend/                    # 源代码
│   ├── app/                   # 应用代码
│   │   ├── agents/           # 7个Agent模块
│   │   ├── api/              # API接口
│   │   ├── core/             # 核心模块
│   │   ├── novel_platform/   # 小说平台集成
│   │   └── main.py           # 主入口
│   ├── scripts/              # 脚本目录
│   │   ├── daily_update.py   # 每日更新脚本
│   │   ├── health_check.py   # 健康检查脚本
│   │   ├── backup_data.py    # 数据备份脚本
│   │   └── cleanup_old.py    # 清理旧数据脚本
│   ├── tests/                # 测试目录
│   └── requirements.txt      # 依赖文件
├── data/                     # 数据目录
│   ├── tasks/               # 任务数据
│   ├── genre_library.db     # 题材库数据库
│   ├── cache/               # 缓存数据
│   └── logs/                # 系统日志
├── venv/                    # Python虚拟环境
├── config/                  # 配置文件
│   ├── system.yaml         # 系统配置
│   ├── agents.yaml         # Agent配置
│   └── llm_providers.yaml  # LLM提供商配置
├── backups/                 # 备份目录
└── README.md               # 说明文档

# 设置权限
chown -R root:root /opt/ai-novel-agent
chmod 755 /opt/ai-novel-agent
chmod -R 755 /opt/ai-novel-agent/backend
chmod -R 777 /opt/ai-novel-agent/data  # 数据目录需要写权限
chmod -R 755 /opt/ai-novel-agent/scripts
```

#### 6.1.3 配置文件示例
```yaml
# config/system.yaml
system:
  name: "ai-novel-agent"
  version: "1.0.0"
  environment: "production"
  data_dir: "/opt/ai-novel-agent/data"
  log_dir: "/opt/ai-novel-agent/data/logs"
  cache_dir: "/opt/ai-novel-agent/data/cache"
  
  server:
    host: "0.0.0.0"
    port: 9000
    workers: 4
    timeout: 300
    max_requests: 1000
    
  database:
    genre_library: "/opt/ai-novel-agent/data/genre_library.db"
    backup_interval: 86400  # 24小时
    max_backups: 30
    
  monitoring:
    health_check_interval: 300  # 5分钟
    disk_space_threshold: 0.8   # 80%
    memory_threshold: 0.9       # 90%
    log_retention_days: 30

# config/agents.yaml
agents:
  trend:
    enabled: true
    daily_update_time: "00:00"
    platforms: ["qidian", "jinjiang", "fanqie"]
    cache_ttl: 3600
    similarity_threshold: 0.7
    heat_decay_rate: 0.05
    
  planner:
    enabled: true
    batch_size: 3
    max_retries: 3
    review_threshold: 80
    genre_selection:
      hot_weight: 0.7
      emerging_weight: 0.3
      avoidance_days: 7
      
  writer:
    enabled: true
    batch_size: 3
    max_workers: 3
    context_window: 3
    consistency_threshold: 0.85
    
  auditor:
    enabled: true
    precision_target: 0.95
    recall_target: 0.90
    confidence_thresholds:
      high: 0.9
      medium: 0.7
      low: 0.5

# config/llm_providers.yaml
llm_providers:
  deepseek:
    enabled: true
    api_key: "${DEEPSEEK_API_KEY}"
    base_url: "https://api.deepseek.com"
    model: "deepseek-chat"
    temperature: 0.7
    max_tokens: 4000
    timeout: 60
    
  openai:
    enabled: false  # 备用提供商
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 4000
    timeout: 60
    
  fallback:
    enabled: true
    strategy: "reduce_quality"
    min_tokens: 1000
    max_retries: 2
```

### 6.2 监控与维护脚本

#### 6.2.1 健康检查脚本
```python
#!/usr/bin/env python3
# backend/scripts/health_check.py

import asyncio
import json
import psutil
import sqlite3
from pathlib import Path
from datetime import datetime

class HealthChecker:
    def __init__(self, config_path="config/system.yaml"):
        self.config = self._load_config(config_path)
        self.checks = [
            self.check_disk_space,
            self.check_memory_usage,
            self.check_cpu_load,
            self.check_database,
            self.check_llm_connectivity,
            self.check_agent_status
        ]
    
    async def run_checks(self):
        """运行所有健康检查"""
        results = {}
        
        for check in self.checks:
            check_name = check.__name__.replace("check_", "")
            try:
                result = await check()
                results[check_name] = result
            except Exception as e:
                results[check_name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        # 计算整体健康状态
        overall_healthy = all(
            r.get("healthy", False) for r in results.values()
        )
        
        report = {
            "overall_health": overall_healthy,
            "timestamp": datetime.now().isoformat(),
            "checks": results
        }
        
        # 保存报告
        self._save_report(report)
        
        # 发送警报（如果需要）
        if not overall_healthy:
            await self._send_alerts(report)
        
        return report
    
    async def check_disk_space(self):
        """检查磁盘空间"""
        data_dir = Path(self.config["system"]["data_dir"])
        stat = psutil.disk_usage(data_dir)
        
        used_percent = stat.percent / 100
        threshold = self.config["system"]["monitoring"]["disk_space_threshold"]
        
        healthy = used_percent < threshold
        
        return {
            "healthy": healthy,
            "total_gb": round(stat.total / (1024**3), 2),
            "used_gb": round(stat.used / (1024**3), 2),
            "free_gb": round(stat.free / (1024**3), 2),
            "used_percent": round(used_percent * 100, 1),
            "threshold_percent": round(threshold * 100, 1),
            "timestamp": datetime.now().isoformat()
        }
    
    async def check_database(self):
        """检查数据库状态"""
        db_path = Path(self.config["system"]["database"]["genre_library"])
        
        if not db_path.exists():
            return {
                "healthy": False,
                "error": "数据库文件不存在",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # 检查数据量
            cursor.execute("SELECT COUNT(*) FROM genres")
            genre_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM genre_heat")
            heat_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "healthy": True,
                "tables": len(tables),
                "genre_count": genre_count,
                "heat_records": heat_count,
                "db_size_mb": round(db_path.stat().st_size / (1024**2), 2),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def check_agent_status(self):
        """检查Agent状态"""
        agents_config = self.config.get("agents", {})
        status = {}
        
        for agent_name, agent_config in agents_config.items():
            if not agent_config.get("enabled", False):
                status[agent_name] = {"enabled": False, "healthy": True}
                continue
            
            # 检查Agent特定指标
            if agent_name == "trend":
                agent_status = await self._check_trend_agent()
            elif agent_name == "planner":
                agent_status = await self._check_planner_agent()
            else:
                agent_status = {"healthy": True, "last_run": "unknown"}
            
            status[agent_name] = agent_status
        
        overall_healthy = all(
            s.get("healthy", False) for s in status.values()
        )
        
        return {
            "healthy": overall_healthy,
            "agents": status,
            "timestamp": datetime.now().isoformat()
        }
```

#### 6.2.2 每日更新脚本
```python
#!/usr/bin/env python3
# backend/scripts/daily_update.py

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from app.agents.trend import TrendAgent
from app.core.state import StateManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def daily_update():
    """每日更新任务"""
    logger.info("开始每日更新任务")
    
    try:
        # 1. 更新趋势数据
        logger.info("更新趋势数据...")
        trend_agent = TrendAgent()
        trend_result = await trend_agent.collect_daily_data()
        
        # 2. 更新题材库
        logger.info("更新题材库...")
        await trend_agent.update_genre_library(trend_result)
        
        # 3. 计算相似度
        logger.info("计算题材相似度...")
        await trend_agent.calculate_similarity()
        
        # 4. 应用热度衰减
        logger.info("应用热度衰减...")
        await trend_agent.apply_heat_decay()
        
        # 5. 清理不活跃题材
        logger.info("清理不活跃题材...")
        removed = await trend_agent.remove_inactive_genres(days=30)
        if removed:
            logger.info(f"移除了{len(removed)}个不活跃题材")
        
        # 6. 备份数据
        logger.info("备份数据...")
        await backup_data()
        
        logger.info("每日更新任务完成")
        
        return {
            "success": True,
            "trend_data_collected": len(trend_result.get("novels", [])),
            "genres_updated": len(trend_result.get("genres", [])),
            "inactive_removed": len(removed),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"每日更新失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def backup_data():
    """备份数据"""
    data_dir = Path("data")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    # 创建带时间戳的备份目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}"
    backup_path.mkdir()
    
    # 备份数据库
    db_files = list(data_dir.glob("*.db"))
    for db_file in db_files:
        backup_file = backup_path / db_file.name
        backup_file.write_bytes(db_file.read_bytes())
    
    # 备份配置文件
    config_files = list(Path("config").glob("*.yaml"))
    for config_file in config_files:
        backup_file = backup_path / config_file.name
        backup_file.write_bytes(config_file.read_bytes())
    
    # 清理旧备份（保留最近30天）
    cleanup_old_backups(backup_dir, days=30)
    
    return {
        "backup_path": str(backup_path),
        "files_backed_up": len(db_files) + len(config_files),
        "timestamp": datetime.now().isoformat()
    }

def cleanup_old_backups(backup_dir, days=30):
    """清理旧备份"""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for backup in backup_dir.iterdir():
        if backup.is_dir() and backup.name.startswith("backup_"):
            try:
                # 从目录名解析时间
                date_str = backup.name.replace("backup_", "")
                backup_date = datetime.strptime(date_str[:8], "%Y%m%d")
                
                if backup_date < cutoff_date:
                    import shutil
                    shutil.rmtree(backup)
                    logger.info(f"清理旧备份: {backup.name}")
            except Exception as e:
                logger.warning(f"无法解析备份目录时间: {backup.name}, {e}")

if __name__ == "__main__":
    asyncio.run(daily_update())
```

## 7. 测试详细设计

### 7.1 单元测试设计

#### 7.1.1 TrendAgent测试
```python
# tests/test_trend_agent.py

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.agents.trend import TrendAgent, GenreLibrary, DataCollector

class TestTrendAgent:
    @pytest.fixture
    def trend_agent(self):
        return TrendAgent()
    
    @pytest.fixture
    def mock_genre_library(self):
        library = Mock(spec=GenreLibrary)
        library.get_hot_genres.return_value = [
            {"id": 1, "name": "都市现实", "heat_index": 95.2},
            {"id": 2, "name": "玄幻奇幻", "heat_index": 88.7}
        ]
        return library
    
    @pytest.mark.asyncio
    async def test_collect_daily_data(self, trend_agent):
        """测试每日数据采集"""
        with patch.object(DataCollector, 'collect_daily_data') as mock_collect:
            mock_collect.return_value = {
                "qidian": [
                    {"title": "测试小说1", "genre": "都市现实", "read_count": 1000}
                ]
            }
            
            result = await trend_agent.collect_daily_data()
            
            assert "qidian" in result
            assert len(result["qidian"]) == 1
            mock_collect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_genre_library(self, trend_agent, mock_genre_library):
        """测试题材库更新"""
        trend_agent.genre_library = mock_genre_library
        
        test_data = {
            "qidian": [
                {"title": "测试小说", "genre": "都市现实", "read_count": 1000}
            ]
        }
        
        await trend_agent.update_genre_library(test_data)
        
        mock_genre_library.add_daily_heat_data.assert_called_once_with(test_data)
    
    def test_calculate_heat_index(self, trend_agent):
        """测试热度计算"""
        novel_data = {
            "read_count": 1000,
            "discuss_count": 200,
            "collect_count": 150,
            "share_count": 50
        }
        
        heat_index = trend_agent._calculate_heat_index(novel_data)
        
        # 验证计算公式: 0.4×阅读量 + 0.3×讨论量 + 0.2×收藏量 + 0.1×分享量
        expected = 0.4*1000 + 0.3*200 + 0.2*150 + 0.1*50
        assert heat_index == expected
    
    def test_heat_decay_calculation(self, trend_agent):
        """测试热度衰减计算"""
        # 初始热度100，经过7天衰减
        initial_heat = 100.0
        days_passed = 7
        decay_rate = 0.05
        
        decayed_heat = trend_agent._apply_heat_decay(
            initial_heat, days_passed, decay_rate
        )
        
        expected = initial_heat * (2.71828 ** (-decay_rate * days_passed))
        assert abs(decayed_heat - expected) < 0.01

class TestGenreLibrary:
    @pytest.fixture
    def genre_library(self, tmp_path):
        db_path = tmp_path / "test_genre_library.db"
        library = GenreLibrary(db_path=str(db_path))
        library.initialize()
        return library
    
    def test_add_and_get_genre(self, genre_library):
        """测试添加和获取题材"""
        # 添加题材
        genre_id = genre_library._get_or_create_genre("测试题材")
        assert genre_id is not None
        
        # 获取题材
        genre = genre_library.get_genre_by_name("测试题材")
        assert genre["name"] == "测试题材"
    
    def test_similarity_calculation(self, genre_library):
        """测试相似度计算"""
        # 添加两个题材
        genre1_id = genre_library._get_or_create_genre("都市现实")
        genre2_id = genre_library._get_or_create_genre("都市言情")
        
        # 计算相似度
        genre_library.calculate_similarity()
        
        # 验证相似度存储
        similarity = genre_library.get_similarity(genre1_id, genre2_id)
        assert 0 <= similarity <= 1

class TestDataCollector:
    @pytest.fixture
    def data_collector(self):
        return DataCollector(config={"cache_ttl": 3600})
    
    @pytest.mark.asyncio
    async def test_platform_collection(self, data_collector):
        """测试平台数据采集"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '<html>测试HTML</html>'
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # 测试单个平台采集
            collector = Mock()
            collector.collect.return_value = [{"title": "测试小说"}]
            
            data_collector.platforms = {"test": collector}
            
            result = await data_collector.collect_daily_data()
            
            assert "test" in result
            collector.collect.assert_called_once()
```

### 7.2 集成测试设计

#### 7.2.1 完整流水线测试
```python
# tests/test_integration.py

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from app.core.pipeline import PipelineController
from app.core.state import StateManager

class TestFullPipeline:
    @pytest.fixture
    def pipeline_controller(self, tmp_path):
        # 使用临时目录作为数据目录
        config = {
            "data_dir": str(tmp_path),
            "llm_provider": "mock",
            "agents": {
                "trend": {"enabled": True, "mock_data": True},
                "style": {"enabled": True, "mock_data": True},
                "planner": {"enabled": True, "batch_size": 3},
                "writer": {"enabled": True, "batch_size": 3},
                "polish": {"enabled": True},
                "auditor": {"enabled": True},
                "reviser": {"enabled": True}
            }
        }
        
        controller = PipelineController(config)
        return controller
    
    @pytest.fixture
    def mock_llm_responses(self):
        """模拟LLM响应"""
        return {
            "trend_analysis": {
                "hot_genres": [{"name": "都市现实", "heat_index": 95.2}],
                "chapter_recommendation": {"min": 12, "recommended": 18, "max": 30}
            },
            "style_analysis": {
                "style_parameters": {"language_complexity": 7.2}
            },
            "plan_review": {
                "pass": True,
                "score": 85,
                "feedback": "策划案质量良好"
            },
            "chapter_writing": {
                "content": "这是测试章节内容。",
                "quality_score": 8.5
            },
            "audit_result": {
                "needs_revision": False,
                "issues": [],
                "overall_score": 90
            }
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(300)  # 5分钟超时
    async def test_complete_pipeline_18_chapters(self, pipeline_controller, mock_llm_responses, tmp_path):
        """测试完整的18章流水线"""
        # 模拟所有LLM调用
        with patch('app.core.llm.chat_json') as mock_chat_json:
            def side_effect(prompt, **kwargs):
                # 根据提示内容返回不同的模拟响应
                prompt_str = str(prompt).lower()
                
                if "trend" in prompt_str:
                    return mock_llm_responses["trend_analysis"]
                elif "style" in prompt_str:
                    return mock_llm_responses["style_analysis"]
                elif "review" in prompt_str:
                    return mock_llm_responses["plan_review"]
                elif "write" in prompt_str or "chapter" in prompt_str:
                    return mock_llm_responses["chapter_writing"]
                elif "audit" in prompt_str:
                    return mock_llm_responses["audit_result"]
                else:
                    return {"result": "default_response"}
            
            mock_chat_json.side_effect = side_effect
        
        # 创建测试任务
        task_id = "test_pipeline_18ch"
        novel_title = "测试小说-18章完整流程"
        
        # 执行流水线
        result = await pipeline_controller.execute_pipeline(
            task_id=task_id,
            novel_title=novel_title,
            chapter_count=18
        )
        
        # 验证结果
        assert result["status"] == "success"
        assert result["task_id"] == task_id
        
        # 验证任务目录结构
        task_dir = tmp_path / "tasks" / task_id
        assert task_dir.exists()
        
        # 验证输出文件
        output_files = [
            "trend_analysis.json",
            "style_parameters.json",
            "planner/故事总纲.md",
            "planner/章节大纲.md",
            "writer/ch_01_raw.md",
            "writer/ch_18_raw.md",
            "polish/ch_01_polished.md",
            "audit_report.json"
        ]
        
        for file in output_files:
            file_path = task_dir / "output" / file
            assert file_path.exists(), f"文件不存在: {file_path}"
        
        # 验证元数据
        meta_file = task_dir / "meta.json"
        assert meta_file.exists()
        
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        assert meta["task_id"] == task_id
        assert meta["novel_title"] == novel_title
        assert meta["status"] == "completed"
        assert len(meta["agents"]) == 7  # 所有7个Agent都应该执行
        
        # 验证章节数量
        chapter_files = list((task_dir / "output" / "writer").glob("ch_*.md"))
        assert len(chapter_files) == 18
        
        return result
    
    @pytest.mark.asyncio
    async def test_pipeline_with_revision(self, pipeline_controller, mock_llm_responses):
        """测试包含修订的流水线"""
        # 模拟审计发现问题需要修订
        revision_count = 0
        
        def mock_llm_side_effect(prompt, **kwargs):
            nonlocal revision_count
            prompt_str = str(prompt).lower()
            
            if "audit" in prompt_str and revision_count == 0:
                # 第一次审计发现问题
                revision_count += 1
                return {
                    "needs_revision": True,
                    "issues": [{
                        "type": "plot_hole",
                        "severity": "medium",
                        "description": "情节漏洞需要修复"
                    }],
                    "overall_score": 65
                }
            elif "audit" in prompt_str and revision_count > 0:
                # 修订后审计通过
                return {
                    "needs_revision": False,
                    "issues": [],
                    "overall_score": 85
                }
            else:
                # 其他情况返回默认响应
                return mock_llm_responses.get(
                    next((k for k in mock_llm_responses if k in prompt_str), "default"),
                    {"result": "default_response"}
                )
        
        with patch('app.core.llm.chat_json') as mock_chat_json:
            mock_chat_json.side_effect = mock_llm_side_effect
            
            # 执行流水线
            result = await pipeline_controller.execute_pipeline(
                task_id="test_with_revision",
                novel_title="测试修订流程",
                chapter_count=6  # 测试6章流程
            )
        
        # 验证结果
        assert result["status"] == "success"
        assert revision_count > 0  # 应该发生了修订
        
        # 验证修订记录
        task_dir = Path(pipeline_controller.config["data_dir"]) / "tasks" / "test_with_revision"
        revision_file = task_dir / "output" / "revision_report.json"
        
        if revision_file.exists():
            with open(revision_file, 'r', encoding='utf-8') as f:
                revision_data = json.load(f)
            
            assert "revisions" in revision_data
            assert len(revision_data["revisions"]) > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_error_recovery(self, pipeline_controller):
        """测试错误恢复机制"""
        call_count = 0
        
        def mock_llm_with_error(prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 3:
                # 第三次调用模拟超时错误
                raise TimeoutError("LLM API超时")
            elif call_count == 4:
                # 第四次调用应该成功（重试后）
                return {"result": "success_after_retry"}
            else:
                return {"result": "normal_response"}
        
        with patch('app.core.llm.chat_json') as mock_chat_json:
            mock_chat_json.side_effect = mock_llm_with_error
            
            # 执行流水线
            result = await pipeline_controller.execute_pipeline(
                task_id="test_error_recovery",
                novel_title="测试错误恢复",
                chapter_count=3
            )
        
        # 验证结果
        assert result["status"] == "success"
        assert call_count >= 4  # 应该发生了重试
        
        # 验证错误日志
        task_dir = Path(pipeline_controller.config["data_dir"]) / "tasks" / "test_error_recovery"
        log_files = list((task_dir / "logs").glob("*.jsonl"))
        
        error_found = False
        for log_file in log_files:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    log_entry = json.loads(line)
                    if log_entry.get("level") == "ERROR" and "timeout" in log_entry.get("message", "").lower():
                        error_found = True
                        break
        
        assert error_found, "应该记录超时错误日志"
```

### 7.3 性能测试设计

#### 7.3.1 负载测试
```python
# tests/test_performance.py

import pytest
import asyncio
import time
import statistics
from datetime import datetime

class TestPerformance:
    @pytest.mark.asyncio
    async def test_batch_writing_performance(self):
        """测试批次写作性能"""
        from app.agents.writer import BatchWritingController
        
        controller = BatchWritingController(batch_size=3, max_workers=3)
        
        # 准备测试数据
        test_outlines = [
            {
                "chapter": i + 1,
                "title": f"测试章节{i+1}",
                "summary": f"这是第{i+1}章的概要",
                "key_events": ["事件1", "事件2"],
                "characters": ["主角", "配角"],
                "word_target": 3000
            }
            for i in range(9)  # 测试3个批次，共9章
        ]
        
        execution_times = []
        
        # 执行3个批次
        for batch_start in range(0, 9, 3):
            batch_outlines = test_outlines[batch_start:batch_start + 3]
            
            start_time = time.time()
            
            result = await controller.write_batch(
                start_chapter=batch_start + 1,
                outlines=batch_outlines
            )
            
            end_time = time.time()
            batch_time = end_time - start_time
            
            execution_times.append(batch_time)
            
            # 验证结果
            assert "chapters" in result
            assert len(result["chapters"]) == 3
            assert result["batch_info"]["start_chapter"] == batch_start + 1
            assert result["batch_info"]["end_chapter"] == batch_start + 3
        
        # 性能分析
        avg_time = statistics.mean(execution_times)
        std_time = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        
        print(f"\n批次写作性能测试结果:")
        print(f"  测试批次: {len(execution_times)}")
        print(f"  平均时间: {avg_time:.2f}秒/批次")
        print(f"  标准差: {std_time:.2f}秒")
        print(f"  总时间: {sum(execution_times):.2f}秒")
        
        # 性能要求：每个批次不超过10分钟
        assert avg_time < 600, f"批次写作时间过长: {avg_time:.2f}秒"
        
        # 稳定性要求：标准差不超过平均值的50%
        if avg_time > 0:
            stability = std_time / avg_time
            assert stability < 0.5, f"批次写作时间不稳定: {stability:.2%}"
    
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self):
        """测试并发任务执行"""
        from app.core.pipeline import PipelineController
        
        controller = PipelineController(config={"max_concurrent_tasks": 3})
        
        # 创建多个并发任务
        tasks = []
        for i in range(5):  # 创建5个任务，超过并发限制
            task_id = f"concurrent_test_{i}"
            task = asyncio.create_task(
                controller.execute_pipeline(
                    task_id=task_id,
                    novel_title=f"并发测试小说{i}",
                    chapter_count=3,  # 短任务用于测试
                    mock_mode=True  # 使用模拟模式避免实际LLM调用
                )
            )
            tasks.append((task_id, task))
        
        # 等待所有任务完成
        start_time = time.time()
        results = []
        
        for task_id, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=300)
                results.append((task_id, result))
            except asyncio.TimeoutError:
                results.append((task_id, {"status": "timeout"}))
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 分析结果
        successful = sum(1 for _, r in results if r.get("status") == "success")
        failed = len(results) - successful
        
        print(f"\n并发任务执行测试结果:")
        print(f"  总任务数: {len(tasks)}")
        print(f"  成功数: {successful}")
        print(f"  失败数: {failed}")
        print(f"  总执行时间: {total_time:.2f}秒")
        print(f"  平均每个任务: {total_time/len(tasks):.2f}秒")
        
        # 验证并发控制
        assert successful >= 3, "应该至少有3个任务成功执行"
        
        # 验证没有死锁或资源竞争
        assert failed == 0, f"有{failed}个任务失败"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """测试负载下的内存使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 记录初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行负载测试
        from app.agents.writer import BatchWritingController
        
        controller = BatchWritingController(batch_size=3, max_workers=3)
        
        memory_samples = []
        
        # 模拟多个批次写作
        for i in range(10):  # 10个批次
            # 执行一个批次
            await controller.write_batch(
                start_chapter=i*3 + 1,
                outlines=[{"title": f"测试{i*3+j+1}"} for j in range(3)],
                mock_mode=True
            )
            
            # 记录内存使用
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
            # 清理缓存（模拟批次间清理）
            if hasattr(controller, 'clear_cache'):
                controller.clear_cache()
        
        # 分析内存使用
        max_memory = max(memory_samples)
        avg_memory = statistics.mean(memory_samples)
        
        print(f"\n内存使用测试结果:")
        print(f"  初始内存: {initial_memory:.2f} MB")
        print(f"  峰值内存: {max_memory:.2f} MB")
        print(f"  平均内存: {avg_memory:.2f} MB")
        print(f"  内存增长: {max_memory - initial_memory:.2f} MB")
        
        # 内存要求：峰值不超过1GB
        assert max_memory < 1024, f"内存使用过高: {max_memory:.2f} MB"
        
        # 内存泄漏检查：最终内存不应比初始高太多
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_leak = final_memory - initial_memory
        
        assert memory_leak < 100, f"可能的内存泄漏: {memory_leak:.2f} MB增长"
```

## 8. 部署检查清单

### 8.1 预部署检查
```bash
#!/bin/bash
# deploy_checklist.sh

echo "=== AI小说生成Agent系统部署检查清单 ==="
echo ""

# 1. 系统要求检查
echo "1. 检查系统要求:"
echo "   - Python版本: $(python3 --version)"
echo "   - 内存总量: $(free -h | awk '/^Mem:/ {print $2}')"
echo "   - 磁盘空间: $(df -h /opt | awk 'NR==2 {print $4}') 可用"
echo "   - CPU核心数: $(nproc) 个"

# 2. 目录权限检查
echo ""
echo "2. 检查目录权限:"
check_dirs=(
    "/opt/ai-novel-agent"
    "/opt/ai-novel-agent/backend"
    "/opt/ai-novel-agent/data"
    "/opt/ai-novel-agent/scripts"
)

for dir in "${check_dirs[@]}"; do
    if [ -d "$dir" ]; then
        perm=$(stat -c "%a" "$dir")
        owner=$(stat -c "%U:%G" "$dir")
        echo "   - $dir: 权限 $perm, 所有者 $owner"
    else
        echo "   - $dir: 目录不存在"
    fi
done

# 3. 配置文件检查
echo ""
echo "3. 检查配置文件:"
config_files=(
    "/opt/ai-novel-agent/config/system.yaml"
    "/opt/ai-novel-agent/config/agents.yaml"
    "/opt/ai-novel-agent/config/llm_providers.yaml"
    "/opt/ai-novel-agent/backend/.env"
)

for file in "${config_files[@]}"; do
    if [ -f "$file" ]; then
        size=$(stat -c "%s" "$file")
        echo "   - $file: 存在 (${size}字节)"
        
        # 检查敏感信息
        if [[ "$file" == *".env" ]] || [[ "$file" == *"llm_providers.yaml" ]]; then
            if grep -q "api_key" "$file"; then
                echo "     ⚠️  包含API密钥，请确保安全"
            fi
        fi
    else
        echo "   - $file: 文件不存在"
    fi
done

# 4. 服务状态检查
echo ""
echo "4. 检查服务状态:"
if systemctl is-active --quiet ai-novel-agent; then
    echo "   - ai-novel-agent服务: 运行中"
    echo "   - 服务PID: $(systemctl show -p MainPID ai-novel-agent | cut -d= -f2)"
else
    echo "   - ai-novel-agent服务: 未运行"
fi

# 5. 数据库检查
echo ""
echo "5. 检查数据库:"
db_file="/opt/ai-novel-agent/data/genre_library.db"
if [ -f "$db_file" ]; then
    db_size=$(stat -c "%s" "$db_file")
    echo "   - 题材库数据库: 存在 (${db_size}字节)"
    
    # 尝试连接数据库
    if command -v sqlite3 &> /dev/null; then
        table_count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "无法连接")
        echo "   - 数据库表数量: $table_count"
    fi
else
    echo "   - 题材库数据库: 不存在（首次运行时会自动创建）"
fi

# 6. 网络连接检查
echo ""
echo "6. 检查网络连接:"
echo "   - 检查LLM API连接..."
if curl -s --connect-timeout 5 https://api.deepseek.com/health > /dev/null; then
    echo "   - DeepSeek API: 可访问"
else
    echo "   - DeepSeek API: 无法访问"
fi

# 7. 依赖检查
echo ""
echo "7. 检查Python依赖:"
venv_python="/opt/ai-novel-agent/venv/bin/python"
if [ -f "$venv_python" ]; then
    echo "   - 虚拟环境: 存在"
    
    # 检查主要依赖
    deps=("fastapi" "uvicorn" "httpx" "sqlalchemy" "pydantic")
    for dep in "${deps[@]}"; do
        if "$venv_python" -c "import $dep" 2>/dev/null; then
            version=$("$venv_python" -c "import $dep; print($dep.__version__)" 2>/dev/null || echo "未知版本")
            echo "   - $dep: 已安装 ($version)"
        else
            echo "   - $dep: 未安装"
        fi
    done
else
    echo "   - 虚拟环境: 不存在"
fi

echo ""
echo "=== 检查完成 ==="
```

### 8.2 部署脚本
```bash
#!/bin/bash
# deploy.sh

set -e  # 遇到错误退出

echo "开始部署AI小说生成Agent系统..."
echo ""

# 1. 创建目录结构
echo "1. 创建目录结构..."
mkdir -p /opt/ai-novel-agent/{backend,data/{tasks,cache,logs},config,backups,scripts}
mkdir -p /opt/ai-novel-agent/backend/{app,scripts,tests}

# 2. 复制代码
echo "2. 复制代码文件..."
cp -r ../backend/* /opt/ai-novel-agent/backend/
cp -r ../config/* /opt/ai-novel-agent/config/
cp ../scripts/* /opt/ai-novel-agent/scripts/

# 3. 设置权限
echo "3. 设置权限..."
chown -R root:root /opt/ai-novel-agent
chmod 755 /opt/ai-novel-agent
chmod -R 755 /opt/ai-novel-agent/backend
chmod -R 755 /opt/ai-novel-agent/scripts
chmod -R 777 /opt/ai-novel-agent/data  # 数据目录需要写权限

# 4. 创建虚拟环境
echo "4. 创建Python虚拟环境..."
cd /opt/ai-novel-agent
python3 -m venv venv

# 5. 安装依赖
echo "5. 安装Python依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# 6. 创建systemd服务
echo "6. 创建systemd服务..."
cat > /etc/systemd/system/ai-novel-agent.service << EOF
[Unit]
Description=AI Novel Agent System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ai-novel-agent
Environment="PATH=/opt/ai-novel-agent/venv/bin"
Environment="PYTHONPATH=/opt/ai-novel-agent/backend"
ExecStart=/opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. 启用并启动服务
echo "7. 启用并启动服务..."
systemctl daemon-reload
systemctl enable ai-novel-agent
systemctl start ai-novel-agent

# 8. 创建定时任务（每日更新）
echo "8. 创建定时任务..."
cat > /etc/cron.d/ai-novel-agent-daily << EOF
# 每天00:00更新题材库
0 0 * * * root /opt/ai-novel-agent/venv/bin/python /opt/ai-novel-agent/backend/scripts/daily_update.py >> /opt/ai-novel-agent/data/logs/daily_update.log 2>&1

# 每小时健康检查
0 * * * * root /opt/ai-novel-agent/venv/bin/python /opt/ai-novel-agent/backend/scripts/health_check.py >> /opt/ai-novel-agent/data/logs/health_check.log 2>&1
EOF

# 9. 初始化数据库
echo "9. 初始化数据库..."
cd /opt/ai-novel-agent/backend
python -c "
from app.agents.trend.genre_library import GenreLibrary
library = GenreLibrary('/opt/ai-novel-agent/data/genre_library.db')
library.initialize()
print('数据库初始化完成')
"

# 10. 验证部署
echo "10. 验证部署..."
sleep 5  # 等待服务启动

if systemctl is-active --quiet ai-novel-agent; then
    echo "✅ 服务运行正常"
    
    # 测试API
    if curl -s http://localhost:9000/api/health | grep -q "healthy"; then
        echo "✅ API接口正常"
    else
        echo "⚠️  API接口可能有问题"
    fi
else
    echo "❌ 服务启动失败"
    journalctl -u ai-novel-agent -n 20 --no-pager
    exit 1
fi

echo ""
echo "=== 部署完成 ==="
echo "服务地址: http://$(hostname -I | awk '{print $1}'):9000"
echo "管理命令: systemctl status ai-novel-agent"
echo "查看日志: journalctl -u ai-novel-agent -f"
```

## 9. 总结

本详细设计文档提供了AI小说生成Agent系统的完整技术实现方案，包括：

### 9.1 核心特性实现
1. **TrendAgent完整实现**：题材库动态管理、每日更新、热度衰减、相似度计算
2. **PlannerAgent 3章周期审核**：加权随机题材选择、多题材融合、审核量化标准
3. **WriterAgent 3章批次生成**：并行写作、上下文管理、一致性检查
4. **AuditorAgent量化审计**：准确率/召回率计算、置信度评分、问题覆盖
5. **完整错误恢复系统**：错误分类、重试策略、状态恢复

### 9.2 系统集成
1. **状态机驱动的流水线**：7个Agent顺序执行，支持修订循环
2. **健壮的数据存储**：SQLite数据库 + 文件系统，支持备份恢复
3. **完整的监控体系**：健康检查、性能监控、日志系统
4. **生产就绪的部署**：systemd服务、定时任务、配置管理

### 9.3 质量保障
1. **全面的测试套件**：单元测试、集成测试、性能测试
2. **详细的部署检查**：预部署验证、自动化部署脚本
3. **完善的文档**：配置说明、监控指南、故障排除

### 9.4 技术亮点
1. **算法创新**：加权随机题材选择、热度衰减模型、3章批次审核
2. **工程实践**：模块化设计、错误隔离、状态恢复、性能优化
3. **可维护性**：清晰的代码结构、完整的测试覆盖、详细的文档

本设计基于现有项目代码，确保可实施性，同时按照需求文档的要求，实现了所有核心功能。系统设计考虑了生产环境的实际需求，包括性能、可靠性、可维护性和可扩展性。
"