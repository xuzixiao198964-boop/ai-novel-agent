# AI小说生成Agent系统 - 概要设计文档

## 1. 系统架构概述

### 1.1 设计原则
- **模块化设计**：7个Agent独立模块，通过标准接口通信
- **流水线执行**：严格按顺序执行，前一个Agent完成后触发下一个
- **状态驱动**：中央状态管理器协调各Agent状态和进度
- **数据持久化**：所有中间产物和最终结果持久化存储
- **错误隔离**：单个Agent失败不影响整体流水线，支持重试

### 1.2 系统架构图
```
┌─────────────────────────────────────────────────────────────┐
│                    Web前端 (FastAPI + 静态页面)              │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    API网关层 (FastAPI路由)                   │
│  ├─ 任务管理API (创建/启动/停止/查询)                        │
│  ├─ 进度查询API (整体进度/各Agent详情)                       │
│  ├─ 文件管理API (上传/下载/预览)                            │
│  └─ 系统管理API (运行模式/配置/健康检查)                     │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    Agent调度层 (Pipeline控制器)              │
│  ├─ 流水线执行器 (按顺序触发Agent)                          │
│  ├─ 状态同步器 (实时更新Agent状态)                          │
│  ├─ 错误处理器 (重试/降级/恢复)                             │
│  └─ 进度追踪器 (计算整体完成度)                             │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  TrendAgent │ StyleAgent  │ PlannerAgent│ WriterAgent │
│ (趋势分析)  │ (风格解析)  │ (策划)      │ (写作)      │
└─────────────┴─────────────┴─────────────┴─────────────┘
                               │
┌─────────────┬─────────────┬─────────────┐
│ PolishAgent │ AuditorAgent│ ReviserAgent│
│ (润色)      │ (审计)      │ (修订)      │
└─────────────┴─────────────┴─────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    数据存储层 (文件系统 + 内存状态)           │
│  ├─ 任务目录结构 (按task_id组织)                            │
│  ├─ Agent输出文件 (JSON/Markdown格式)                       │
│  ├─ 进度状态文件 (实时更新)                                 │
│  ├─ 日志文件 (按Agent分割)                                  │
│  └─ 长期记忆库 (7个真相文件)                                │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    外部服务层                                │
│  ├─ LLM API (DeepSeek/OpenAI兼容接口)                       │
│  ├─ 小说平台API (趋势数据爬取)                              │
│  └─ 系统服务 (systemd守护进程)                              │
└─────────────────────────────────────────────────────────────┘
```

## 2. Agent详细设计

### 2.1 TrendAgent（趋势分析Agent）

#### 2.1.1 模块结构
```
trend_agent/
├── __init__.py
├── main.py              # 主执行入口
├── data_collector.py    # 数据采集模块
├── genre_manager.py     # 题材库管理模块
├── trend_analyzer.py    # 趋势分析模块
├── cache_manager.py     # 缓存管理模块
└── output_generator.py  # 输出生成模块
```

#### 2.1.2 核心算法实现
**题材库动态管理**：
```python
class GenreManager:
    def __init__(self):
        self.genres_db = "backend/data/genre_library.db"
        self.active_genres = {}  # 活跃题材库
        self.history_genres = {} # 历史题材库
    
    def daily_update(self):
        """每日00:00自动更新"""
        # 1. 采集各平台数据
        new_genres = self.collect_platform_data()
        
        # 2. 相似度过滤（<70%相似度纳入）
        filtered = self.filter_by_similarity(new_genres, threshold=0.7)
        
        # 3. 热度衰减计算
        self.apply_heat_decay()
        
        # 4. 30天淘汰机制
        self.remove_inactive_genres(days=30)
        
        # 5. 持久化存储
        self.save_to_db()
    
    def calculate_similarity(self, genre1, genre2):
        """文本向量化相似度计算"""
        # 使用BERT或TF-IDF计算相似度
        pass
    
    def apply_heat_decay(self):
        """指数衰减模型：热度 = 初始热度 × e^(-λ×天数)"""
        for genre in self.active_genres.values():
            days = (datetime.now() - genre.last_update).days
            genre.heat = genre.initial_heat * math.exp(-0.05 * days)
```

**热度计算算法**：
```python
def calculate_comprehensive_heat(self, data):
    """综合热度计算：0.4×阅读量 + 0.3×讨论量 + 0.2×收藏量 + 0.1×分享量"""
    read_weight = 0.4
    discuss_weight = 0.3
    collect_weight = 0.2
    share_weight = 0.1
    
    heat = (
        data.read_count * read_weight +
        data.discuss_count * discuss_weight +
        data.collect_count * collect_weight +
        data.share_count * share_weight
    )
    return heat
```

#### 2.1.3 输出格式
```json
{
  "trend_analysis": {
    "timestamp": "2026-03-26T00:00:00",
    "hot_genres": [
      {
        "rank": 1,
        "name": "都市现实",
        "heat_index": 95.2,
        "sub_genres": ["职场商战", "校园青春"],
        "reader_profile": {
          "age_distribution": {"18-25": 35, "26-35": 45},
          "gender_ratio": {"male": 40, "female": 60},
          "reading_time": {"weekday": 65, "weekend": 35}
        }
      }
    ],
    "emerging_genres": [
      {
        "name": "科幻未来",
        "growth_rate": 25.3,
        "daily_discussion": 1500
      }
    ],
    "chapter_recommendation": {
      "min": 12,
      "recommended": 18,
      "max": 30
    },
    "market_analysis": {
      "saturation_level": 75.2,
      "opportunity_points": ["跨界融合", "细分领域"]
    }
  }
}
```

### 2.2 StyleAgent（风格解析Agent）

#### 2.2.1 模块结构
```
style_agent/
├── __init__.py
├── main.py
├── text_analyzer.py      # 文本分析模块
├── style_extractor.py    # 风格特征提取模块
├── parameter_generator.py # 参数生成模块
└── template_matcher.py   # 模板匹配模块
```

#### 2.2.2 核心算法实现
**风格参数量化**：
```python
class StyleAnalyzer:
    def analyze_novel_style(self, novel_text):
        """深度分析小说风格特征"""
        # 1. 语言复杂度分析
        complexity = self.calculate_language_complexity(novel_text)
        
        # 2. 叙事节奏分析
        rhythm = self.analyze_narrative_rhythm(novel_text)
        
        # 3. 对话特征分析
        dialogue_features = self.extract_dialogue_features(novel_text)
        
        # 4. 描写详细度分析
        description_detail = self.analyze_description_detail(novel_text)
        
        # 5. 情感曲线分析
        emotion_curve = self.extract_emotion_curve(novel_text)
        
        return {
            "language_complexity": complexity,  # 1-10分
            "narrative_rhythm": rhythm,         # 快/中/慢
            "dialogue_ratio": dialogue_features["ratio"],  # 20-40%
            "description_detail": description_detail,      # 详细程度
            "emotion_intensity": emotion_curve["intensity"]  # 情感强度
        }
```

### 2.3 PlannerAgent（策划Agent）- 3章周期审核机制

#### 2.3.1 模块结构
```
planner_agent/
├── __init__.py
├── main.py
├── genre_selector.py     # 题材选择模块
├── story_outline.py      # 故事总纲生成模块
├── chapter_planner.py    # 章节规划模块
├── review_mechanism.py   # 3章周期审核机制
├── setting_solidifier.py # 设定固化模块
└── output_generator.py   # 输出生成模块
```

#### 2.3.2 核心算法实现
**加权随机选择算法**：
```python
class GenreSelector:
    def weighted_random_selection(self, genres_data):
        """按比例随机选择题材"""
        # 计算选择概率：热度权重 × 创新系数 × 回避系数
        probabilities = []
        for genre in genres_data:
            heat_weight = self.normalize_heat(genre.heat)
            innovation_coef = self.get_innovation_coefficient(genre.rank)
            avoidance_coef = self.get_avoidance_coefficient(genre.last_used)
            
            probability = heat_weight * innovation_coef * avoidance_coef
            probabilities.append(probability)
        
        # 归一化概率
        total = sum(probabilities)
        normalized = [p/total for p in probabilities]
        
        # 加权随机选择
        selected = random.choices(genres_data, weights=normalized, k=1)[0]
        return selected
    
    def get_innovation_coefficient(self, rank):
        """创新系数计算"""
        if rank <= 10:      # 热门题材
            return 0.7
        elif rank <= 30:    # 稳定题材
            return 1.0
        elif rank <= 35:    # 新兴题材（增长最快前5）
            return 1.5
        else:               # 冷门题材
            return 0.5
    
    def get_avoidance_coefficient(self, days_since_last_use):
        """回避系数计算"""
        if days_since_last_use <= 7:    # 近期已创作
            return 0.3
        elif days_since_last_use <= 30: # 适度重复
            return 0.7
        elif days_since_last_use > 30:  # 长期未创作
            return 1.2
        else:                           # 全新题材
            return 1.5
```

**3章周期审核机制**：
```python
class ThreeChapterReviewMechanism:
    def __init__(self):
        self.current_batch = 1
        self.solidified_settings = {}
        self.review_count = 0
    
    def process_chapter_batch(self, chapters_data):
        """处理3章批次"""
        # 1. 生成前3章大纲
        if self.current_batch == 1:
            outline = self.generate_first_three_chapters(chapters_data)
            
            # 2. 深度审核
            review_result = self.deep_review(outline)
            
            # 3. 审核通过则固化设定
            if review_result["pass"]:
                self.solidify_settings(outline)
                self.current_batch += 1
                return True
            else:
                # 4. 修订重试
                return self.revise_and_retry(outline, review_result)
        
        # 5. 后续批次基于固化设定生成
        else:
            outline = self.generate_next_batch(chapters_data, self.solidified_settings)
            review_result = self.batch_review(outline)
            
            if review_result["pass"]:
                self.current_batch += 1
                return True
            else:
                return self.revise_and_retry(outline, review_result)
    
    def solidify_settings(self, outline):
        """固化设定"""
        self.solidified_settings = {
            "core_characters": outline["characters"],
            "world_rules": outline["world_rules"],
            "main_conflict": outline["main_conflict"],
            "emotional_tone": outline["emotional_tone"],
            "chapter_length": outline["chapter_length"],
            "dialogue_ratio": outline["dialogue_ratio"]
        }
```

**审核量化标准实现**：
```python
class ReviewQuantification:
    def calculate_review_score(self, outline):
        """计算审核总分"""
        scores = {
            "structure": self.evaluate_structure(outline),      # 权重30%
            "character": self.evaluate_character(outline),      # 权重25%
            "market": self.evaluate_market_match(outline),      # 权重20%
            "feasibility": self.evaluate_feasibility(outline),  # 权重15%
            "style": self.evaluate_style_match(outline)         # 权重10%
        }
        
        total_score = sum(
            score * weight for score, weight in zip(
                scores.values(), 
                [0.3, 0.25, 0.2, 0.15, 0.1]
            )
        )
        
        # 检查单项阈值
        min_scores = {
            "structure": 70,
            "character": 70,
            "market": 60,
            "feasibility": 60,
            "style": 60
        }
        
        all_pass = all(
            scores[key] >= min_scores[key] 
            for key in min_scores
        )
        
        return {
            "total_score": total_score,
            "dimension_scores": scores,
            "pass": total_score >= 80 and all_pass
        }
```

### 2.4 WriterAgent（写作Agent）- 3章批次生成机制

#### 2.4.1 模块结构
```
writer_agent/
├── __init__.py
├── main.py
├── chapter_generator.py  # 章节生成模块
├── batch_manager.py      # 批次管理模块
├── internal_review.py    # 批次内审核模块
├── consistency_checker.py # 一致性检查模块
└── output_formatter.py   # 输出格式化模块
```

#### 2.4.2 核心算法实现
**3章批次生成流程**：
```python
class ThreeChapterBatchWriter:
    def __init__(self, total_chapters):
        self.total_chapters = total_chapters
        self.batch_size = 3
        self.current_batch = 0
        self.solidified_content = {}
    
    def generate_novel(self, outline):
        """生成完整小说"""
        chapters = []
        
        while self.current_batch * self.batch_size < self.total_chapters:
            # 1. 批次准备
            batch_start = self.current_batch * self.batch_size
            batch_end = min(batch_start + self.batch_size, self.total_chapters)
            
            # 2. 3章并行生成
            batch_chapters = self.generate_batch_parallel(
                outline, batch_start, batch_end
            )
            
            # 3. 批次内审核
            review_result = self.internal_batch_review(batch_chapters)
            
            if review_result["pass"]:
                # 4. 内容固化
                self.solidify_batch_content(batch_chapters)
                chapters.extend(batch_chapters)
                self.current_batch += 1
            else:
                # 5. 问题修订
                batch_chapters = self.revise_batch(
                    batch_chapters, review_result["issues"]
                )
                # 重新审核
                continue
        
        return chapters
    
    def internal_batch_review(self, batch_chapters):
        """批次内审核"""
        scores = {
            "plot_coherence": self.evaluate_plot_coherence(batch_chapters),  # 权重40%
            "character_consistency": self.evaluate_character_consistency(batch_chapters),  # 权重30%
            "style_consistency": self.evaluate_style_consistency(batch_chapters),  # 权重20%
            "language_quality": self.evaluate_language_quality(batch_chapters)     # 权重10%
        }
        
        total_score = sum(
            score * weight for score, weight in zip(
                scores.values(),
                [0.4, 0.3, 0.2, 0.1]
            )
        )
        
        # 检查单章最低分
        chapter_scores = [self.evaluate_single_chapter(ch) for ch in batch_chapters]
        min_chapter_score = min(chapter_scores)
        
        return {
            "total_score": total_score,
            "chapter_scores": chapter_scores,
            "pass": total_score >= 75 and min_chapter_score >= 65
        }
```

### 2.5 AuditorAgent（审计Agent）

#### 2.5.1 模块结构
```
auditor_agent/
├── __init__.py
├── main.py
├── plot_auditor.py       # 情节连贯性审计
├── character_auditor.py  # 人物一致性审计
├── logic_auditor.py      # 逻辑合理性审计
├── style_auditor.py      # 风格符合度审计
├── language_auditor.py   # 语言质量审计
└── metrics_calculator.py # 量化指标计算
```

#### 2.5.2 核心算法实现
**量化指标计算**：
```python
class AuditMetricsCalculator:
    def calculate_precision(self, identified_issues, actual_issues):
        """准确率计算：正确识别的问题数 / 总识别的问题数"""
        true_positives = len(set(identified_issues) & set(actual_issues))
        total_identified = len(identified_issues)
        
        if total_identified == 0:
            return 0.0
        
        precision = true_positives / total_identified
        return precision
    
    def calculate_recall(self, identified_issues, actual_issues):
        """召回率计算：正确识别的问题数 / 实际存在的问题总数"""
        true_positives = len(set(identified_issues) & set(actual_issues))
        total_actual = len(actual_issues)
        
        if total_actual == 0:
            return 1.0  # 如果没有问题，召回率为100%
        
        recall = true_positives / total_actual
        return recall
    
    def calculate_f1_score(self, precision, recall):
        """F1分数计算：2 × (准确率 × 召回率) / (准确率 + 召回率)"""
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * (precision * recall) / (precision + recall)
        return f1
    
    def calculate_confidence_score(self, issue):
        """置信度评分计算"""
        # 基于问题明显程度、证据强度、历史准确率
        evidence_strength = self.evaluate_evidence_strength(issue)
        historical_accuracy = self.get_historical_accuracy(issue.type)
        clarity_score = self.evaluate_issue_clarity(issue)
        
        confidence = (
            evidence_strength * 0.4 +
            historical_accuracy * 0.4 +
            clarity_score * 0.2
        )
        
        return confidence
```

### 2.6 ReviserAgent（修订Agent）

#### 2.6.1 模块结构
```
reviser_agent/
├── __init__.py
├── main.py
├── issue_analyzer.py     # 问题分析模块
├── revision_strategy.py  # 修订策略模块
├── minimal_revision.py   # 最小化修订模块
├── quality_validator.py  # 质量验证模块
└── progress_tracker.py   # 进度追踪模块
```

#### 2.6.2 核心算法实现
**增量修订原则**：
```python
class MinimalRevisionStrategy:
    def revise_content(self, original_content, audit_report):
        """最小化修订"""
        revisions = []
        
        for issue in audit_report["issues"]:
            if issue["severity"] == "critical":
                # 严重问题：必须解决
                revision = self.apply_critical_fix(original_content, issue)
                revisions.append(revision)
            elif issue["severity"] == "major":
                # 重要问题：尽量解决
                if random.random() < 0.8:  # 80%解决率
                    revision = self.apply_major_fix(original_content, issue)
                    revisions.append(revision)
            elif issue["severity"] == "minor":
                # 轻微问题：选择性解决
                if random.random() < 0.5:  # 50%解决率
                    revision = self.apply_minor_fix(original_content, issue)
                    revisions.append(revision)
        
        # 合并所有修订，确保最小化修改
        revised_content = self.merge_revisions(original_content, revisions)
        
        # 验证修订质量提升
        quality_improvement = self.calculate_quality_improvement(
            original_content, revised_content
        )
        
        return {
            "revised_content": revised_content,
            "revisions_applied": len(revisions),
            "quality_improvement": quality_improvement,
            "critical_issues_resolved": self.count_resolved_issues(
                audit_report, "critical"
            )
        }
    
    def calculate_quality_improvement(self, original, revised):
        """计算质量提升度"""
        original_score = self.evaluate_content_quality(original)
        revised_score = self.evaluate_content_quality(revised)
        
        improvement = revised_score - original_score
        return max(0, improvement)  # 确保非负
```

### 2.7 PolishAgent（润色Agent）

#### 2.7.1 模块结构
```
polish_agent/
├── __init__.py
├── main.py
├── grammar_checker.py    # 语法检查模块
├── expression_optimizer.py # 表达优化模块
├── style_enhancer.py     # 风格强化模块
├── rhythm_adjuster.py    # 节奏调整模块
└── change_tracker.py     # 修改追踪模块
```

#### 2.7.2 核心算法实现
**分层润色机制**：
```python
class LayeredPolishing:
    def polish_content(self, content, style_parameters):
        """分层润色"""
        # 1. 语法检查层
        content = self.grammar_check_layer(content)
        
        # 2. 表达优化层
        content = self.expression_optimization_layer(content)
        
        # 3. 风格调整层
        content = self.style_adjustment_layer(content, style_parameters)
        
        # 4. 节奏优化层
        content = self.rhythm_optimization_layer(content)
        
        return content
    
    def grammar_check_layer(self, content):
        """基础语法错误修正"""
        # 使用语言模型或规则检查语法
        corrected = self.correct_grammar_errors(content)
        return corrected
    
    def style_adjustment_layer(self, content, style_params):
        """强化风格特征一致性"""
        adjusted = content
        
        # 调整语言复杂度
        if style_params["language_complexity"] > 7:
            adjusted = self.increase_complexity(adjusted)
        elif style_params["language_complexity"] < 4:
            adjusted = self.simplify_language(adjusted)
        
        # 调整对话占比
        current_ratio = self.calculate_dialogue_ratio(adjusted)
        target_ratio = style_params["dialogue_ratio"]
        
        if abs(current_ratio - target_ratio) > 0.05:  # 5%偏差
            adjusted = self.adjust_dialogue_ratio(adjusted, target_ratio)
        
        return adjusted
```

## 3. 数据存储设计

### 3.1 任务目录结构
```
backend/data/tasks/
├── {task_id}/                    # 任务根目录
│   ├── meta.json                # 任务元数据
│   ├── config.json              # 任务配置
│   ├── progress/                # 进度目录
│   │   ├── TrendAgent.json      # TrendAgent进度
│   │   ├── StyleAgent.json      # StyleAgent进度
│   │   ├── PlannerAgent.json    # PlannerAgent进度
│   │   ├── WriterAgent.json     # WriterAgent进度
│   │   ├── PolishAgent.json     # PolishAgent进度
│   │   ├── AuditorAgent.json    # AuditorAgent进度
│   │   └── ReviserAgent.json    # ReviserAgent进度
│   ├── output/                  # 输出目录
│   │   ├── trend/               # TrendAgent输出
│   │   │   ├── trend_analysis.json
│   │   │   └── genre_library.db
│   │   ├── style/               # StyleAgent输出
│   │   │   └── style_parameters.json
│   │   ├── planner/             # PlannerAgent输出
│   │   │   ├── 策划案.md
│   │   │   ├── 故事总纲.md
│   │   │   └── 章节大纲.md
│   │   ├── writer/              # WriterAgent输出
│   │   │   ├── ch_01_raw.md
│   │   │   ├── ch_02_raw.md
│   │   │   └── ...
│   │   ├── polish/              # PolishAgent输出
│   │   │   ├── ch_01_polished.md
│   │   │   ├── ch_02_polished.md
│   │   │   └── polish_report.json
│   │   ├── audit/               # AuditorAgent输出
│   │   │   └── audit_report.json
│   │   └── revise/              # ReviserAgent输出
│   │       └── revision_report.json
│   └── logs/                    # 日志目录
│       ├── TrendAgent.jsonl
│       ├── StyleAgent.jsonl
│       ├── PlannerAgent.jsonl
│       ├── WriterAgent.jsonl
│       ├── PolishAgent.jsonl
│       ├── AuditorAgent.jsonl
│       └── ReviserAgent.jsonl
```

### 3.2 数据格式规范

#### 3.2.1 任务元数据 (meta.json)
```json
{
  "task_id": "6f14e72e",
  "title": "修复验证测试-5章",
  "status": "running",  // pending, running, completed, failed, stopped
  "created_at": "2026-03-26T14:30:00",
  "started_at": "2026-03-26T14:31:00",
  "completed_at": null,
  "total_chapters": 5,
  "current_chapter": 3,
  "current_agent": "WriterAgent",
  "progress_percentage": 60,
  "error_message": null,
  "config": {
    "test_mode": true,
    "max_retries": 12,
    "llm_provider": "deepseek",
    "mock_llm": false
  }
}
```

#### 3.2.2 Agent进度文件格式
```json
{
  "agent": "PlannerAgent",
  "status": "completed",  // pending, running, completed, failed
  "start_time": "2026-03-26T14:31:00",
  "end_time": "2026-03-26T14:38:00",
  "duration_seconds": 420,
  "output_files": [
    "策划案.md",
    "故事总纲.md",
    "章节大纲.md"
  ],
  "metrics": {
    "review_cycles": 2,
    "total_revisions": 3,
    "final_score": 85,
    "dimension_scores": {
      "structure": 88,
      "character": 92,
      "market": 78,
      "feasibility": 82,
      "style": 85
    }
  },
  "errors": []
}
```

## 4. 系统集成设计

### 4.1 Agent间通信机制

#### 4.1.1 数据传递方式
```python
class AgentPipeline:
    def __init__(self, task_id):
        self.task_id = task_id
        self.task_dir = f"backend/data/tasks/{task_id}"
        self.current_agent_index = 0
        self.agents = [
            TrendAgent(),
            StyleAgent(),
            PlannerAgent(),
            WriterAgent(),
            PolishAgent(),
            AuditorAgent(),
            ReviserAgent()
        ]
    
    def execute(self):
        """顺序执行所有Agent"""
        for agent in self.agents:
            # 1. 检查前置Agent输出
            if not self.check_prerequisites(agent):
                raise Exception(f"前置条件不满足: {agent.name}")
            
            # 2. 执行当前Agent
            result = agent.execute(self.task_dir)
            
            # 3. 保存结果
            self.save_agent_result(agent, result)
            
            # 4. 更新进度
            self.update_progress(agent)
            
            # 5. 检查停止请求
            if self.check_stop_request():
                break
    
    def check_prerequisites(self, agent):
        """检查前置Agent是否完成"""
        agent_dependencies = {
            "StyleAgent": ["TrendAgent"],
            "PlannerAgent": ["TrendAgent", "StyleAgent"],
            "WriterAgent": ["PlannerAgent"],
            "PolishAgent": ["WriterAgent"],
            "AuditorAgent": ["PolishAgent"],
            "ReviserAgent": ["AuditorAgent"]
        }
        
        deps = agent_dependencies.get(agent.name, [])
        for dep in deps:
            dep_progress = self.load_progress(dep)
            if dep_progress["status"] != "completed":
                return False
        
        return True
```

### 4.2 状态管理设计

#### 4.2.1 中央状态管理器
```python
class StateManager:
    def __init__(self):
        self.current_task_id = None
        self.task_states = {}  # 内存中的任务状态
        self.agent_states = {} # Agent执行状态
    
    def set_current_task(self, task_id):
        """设置当前任务"""
        self.current_task_id = task_id
        self.save_to_file("current_task.txt", task_id)
    
    def update_task_progress(self, task_id, progress_data):
        """更新任务进度"""
        if task_id not in self.task_states:
            self.task_states[task_id] = {}
        
        self.task_states[task_id].update(progress_data)
        
        # 持久化到文件
        self.save_task_state(task_id)
    
    def save_task_state(self, task_id):
        """保存任务状态到文件"""
        state_file = f"backend/data/tasks/{task_id}/meta.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(self.task_states[task_id], f, ensure_ascii=False, indent=2)
```

### 4.3 错误处理与恢复

#### 4.3.1 错误分类与处理策略
```python
class ErrorHandler:
    ERROR_CATEGORIES = {
        "llm_failure": {
            "retry_strategy": "exponential_backoff",
            "max_retries": 3,
            "fallback": "use_mock_data"
        },
        "network_error": {
            "retry_strategy": "linear_backoff",
            "max_retries": 5,
            "fallback": "use_cached_data"
        },
        "data_validation_error": {
            "retry_strategy": "immediate",
            "max_retries": 2,
            "fallback": "skip_and_continue"
        },
        "resource_exhaustion": {
            "retry_strategy": "wait_and_retry",
            "max_retries": 1,
            "fallback": "pause_and_resume"
        }
    }
    
    def handle_error(self, error_type, context):
        """处理错误"""
        strategy = self.ERROR_CATEGORIES.get(error_type)
        if not strategy:
            return self.handle_unknown_error(context)
        
        for attempt in range(strategy["max_retries"]):
            try:
                # 尝试恢复
                if self.try_recovery(strategy, context):
                    return True
            except Exception as e:
                # 等待后重试
                wait_time = self.calculate_wait_time(strategy, attempt)
                time.sleep(wait_time)
        
        # 所有重试失败，执行降级策略
        return self.execute_fallback(strategy["fallback"], context)
```

## 5. 部署架构设计

### 5.1 服务器环境配置
```
服务器: 104.244.90.202:9000
部署目录: /opt/ai-novel-agent/
运行用户: root 或专用用户
Python环境: Python 3.9+ 虚拟环境
服务管理: systemd (ai-novel-agent.service)
```

### 5.2 服务启动配置
```ini
# /etc/systemd/system/ai-novel-agent.service
[Unit]
Description=AI Novel Agent Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ai-novel-agent
Environment="PATH=/opt/ai-novel-agent/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=/opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5.3 目录权限设置
```bash
# 创建目录结构
mkdir -p /opt/ai-novel-agent/{backend,data/tasks,logs,static}

# 设置权限
chown -R root:root /opt/ai-novel-agent
chmod -R 755 /opt/ai-novel-agent

# 数据目录可写
chmod -R 777 /opt/ai-novel-agent/data
```

## 6. 监控与日志

### 6.1 日志系统设计
```python
class AgentLogger:
    def __init__(self, task_id, agent_name):
        self.log_file = f"backend/data/tasks/{task_id}/logs/{agent_name}.jsonl"
    
    def log(self, level, message, data=None):
        """记录结构化日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,  # DEBUG, INFO, WARNING, ERROR
            "agent": self.agent_name,
            "task_id": self.task_id,
            "message": message,
            "data": data
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
```

### 6.2 健康检查端点
```python
@app.get("/api/health")
async def health_check():
    """系统健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "llm_api": check_llm_connection(),
            "database": check_database_connection(),
            "file_system": check_disk_space(),
            "memory_usage": get_memory_usage()
        }
    }
```

## 7. 安全设计

### 7.1 API安全
- **CORS配置**：允许前端跨域访问
- **请求限流**：防止API滥用
- **输入验证**：所有API参数验证
- **错误信息脱敏**：不泄露内部细节

### 7.2 数据安全
- **任务隔离**：不同任务数据完全隔离
- **文件权限**：严格的文件访问控制
- **敏感信息**：API密钥等加密存储
- **日志脱敏**：不记录敏感数据

---

**文档版本**: 1.0  
**创建日期**: 2026-03-26  
**更新说明**: 基于需求文档和现有项目实现的概要设计

**关键设计原则**：
1. **与需求文档对齐**：严格按照需求文档的功能要求设计
2. **现有项目兼容**：基于当前项目结构进行扩展
3. **模块化设计**：7个Agent独立可替换
4. **错误恢复能力**：完善的错误处理和降级策略
5. **状态持久化**：所有中间状态可恢复
6. **量化控制**：所有审核和修订都有量化指标