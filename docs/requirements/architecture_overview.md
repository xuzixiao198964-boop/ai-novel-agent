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
├── main.py              # 主执行逻辑
├── data_collector.py    # 数据采集模块
├── genre_analyzer.py    # 题材分析模块
├── trend_predictor.py   # 趋势预测模块
├── genre_library.py     # 题材库管理
├── cache_manager.py     # 缓存管理
└── output_formatter.py  # 输出格式化
```

#### 2.1.2 核心算法实现
1. **数据采集**：
   - 定时任务：每天00:00执行
   - 多平台并行采集：起点、晋江、番茄等
   - 防反爬策略：随机延迟、User-Agent轮换
   - 数据验证：完整性校验、去重清洗

2. **题材库管理**：
   - SQLite数据库存储：`genre_library.db`
   - 相似度计算：Sentence-BERT向量化 + 余弦相似度
   - 热度衰减：`热度 = 初始热度 × e^(-0.05×天数)`
   - 淘汰机制：30天无热度更新移入历史库

3. **趋势分析**：
   - 综合热度计算：`0.4×阅读量 + 0.3×讨论量 + 0.2×收藏量 + 0.1×分享量`
   - 移动平均线：7日、30日、90日趋势
   - 增长潜力评估：日增长率、加速度、稳定性

#### 2.1.3 输出格式
```json
{
  "timestamp": "2026-03-26T00:00:00",
  "hot_genres": [
    {
      "name": "都市现实",
      "heat_index": 95.2,
      "daily_growth": 12.5,
      "reader_profile": {
        "age_distribution": {"18-25": 35, "26-35": 45, "36+": 20},
        "gender_ratio": {"male": 40, "female": 60},
        "reading_habits": {"weekday": 65, "weekend": 35}
      }
    }
  ],
  "emerging_genres": [...],
  "chapter_recommendation": {"min": 12, "recommended": 18, "max": 30},
  "market_analysis": {...}
}
```

### 2.2 StyleAgent（风格解析Agent）

#### 2.2.1 模块结构
```
style_agent/
├── __init__.py
├── main.py
├── text_analyzer.py     # 文本特征提取
├── style_quantifier.py  # 风格量化
├── pattern_matcher.py   # 模式匹配
└── output_formatter.py
```

#### 2.2.2 核心算法
1. **语言特征提取**：
   - 句子长度分布：平均长度、标准差
   - 词汇复杂度：独特词汇占比、专业术语密度
   - 修辞手法：比喻、排比、夸张等频率统计

2. **叙事节奏分析**：
   - 场景切换频率：每千字场景数
   - 情节推进速度：关键事件间隔
   - 情感强度曲线：情感词密度变化

3. **风格参数化**：
   - 10维风格向量：[语言复杂度, 叙事节奏, 对话占比, ...]
   - 相似度匹配：与预定义风格模板对比
   - 异常检测：识别风格突变点

#### 2.2.3 输出格式
```json
{
  "style_parameters": {
    "language_complexity": 7.2,
    "narrative_pace": 6.8,
    "dialogue_ratio": 0.35,
    "description_detail": 8.1,
    "emotional_intensity": 6.5,
    "rhetorical_frequency": 0.12
  },
  "characteristics": {
    "sentence_length": {"mean": 25.3, "std": 8.7},
    "vocabulary_richness": 0.18,
    "scene_switch_freq": 2.3
  },
  "recommendations": [...]
}
```

### 2.3 PlannerAgent（策划Agent）- 3章周期审核机制

#### 2.3.1 模块结构
```
planner_agent/
├── __init__.py
├── main.py
├── genre_selector.py    # 题材选择器
├── story_outliner.py    # 故事总纲生成
├── chapter_planner.py   # 章节大纲生成
├── review_controller.py # 审核控制器
├── fix_generator.py     # 修订生成器
└── state_manager.py     # 状态管理器
```

#### 2.3.2 3章周期审核流程
```python
class ThreeChapterCycle:
    def __init__(self):
        self.batch_size = 3
        self.current_batch = 1
        self.fixed_settings = {}  # 固化设定
    
    def process(self, total_chapters):
        # 第1-3章：生成并深度审核
        chapters_1_3 = self.generate_chapters(1, 3)
        review_result = self.deep_review(chapters_1_3)
        
        if review_result["pass"]:
            # 固化设定
            self.fixed_settings = self.extract_fixed_settings(chapters_1_3)
            # 继续生成4-6章
            chapters_4_6 = self.generate_chapters(4, 6, self.fixed_settings)
            # 继续滚动生成...
        else:
            # 修订循环
            return self.revision_cycle(chapters_1_3, review_result)
```

#### 2.3.3 题材选择算法
```python
def weighted_random_selection(genres, recent_creations):
    """加权随机选择题材"""
    probabilities = []
    for genre in genres:
        # 热度权重
        heat_weight = normalize(genre.heat_index) * time_decay(genre.last_update)
        
        # 创新系数
        if genre.rank <= 10:
            innovation_coef = 0.7  # 热门题材
        elif genre in top_5_growing:
            innovation_coef = 1.5  # 新兴题材
        else:
            innovation_coef = 1.0  # 稳定题材
        
        # 回避系数
        if genre.name in recent_creations[0:7]:  # 7天内创作过
            avoidance_coef = 0.3
        elif genre.name in recent_creations[8:30]:  # 8-30天前创作过
            avoidance_coef = 0.7
        else:
            avoidance_coef = 1.2  # 长期未创作
        
        probability = heat_weight * innovation_coef * avoidance_coef
        probabilities.append(probability)
    
    # 归一化并随机选择
    total = sum(probabilities)
    normalized = [p/total for p in probabilities]
    return random.choices(genres, weights=normalized)[0]
```

#### 2.3.4 审核量化标准实现
```python
class ReviewMetrics:
    def calculate_score(self, outline_batch):
        """计算3章批次审核分数"""
        scores = {
            "structure_integrity": self.check_structure(outline_batch),
            "character_consistency": self.check_characters(outline_batch),
            "market_fit": self.check_market_fit(outline_batch),
            "technical_feasibility": self.check_feasibility(outline_batch),
            "style_compliance": self.check_style(outline_batch)
        }
        
        # 加权计算总分
        weights = {"structure": 0.3, "character": 0.25, "market": 0.2, 
                  "technical": 0.15, "style": 0.1}
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        return {
            "total_score": total_score,
            "dimension_scores": scores,
            "pass": total_score >= 80 and all(s >= 60 for s in scores.values())
        }
```

### 2.4 WriterAgent（写作Agent）- 3章批次生成机制

#### 2.4.1 模块结构
```
writer_agent/
├── __init__.py
├── main.py
├── batch_writer.py      # 批次写作器
├── context_manager.py   # 上下文管理
├── consistency_checker.py # 一致性检查
├── quality_evaluator.py # 质量评估
└── output_formatter.py
```

#### 2.4.2 3章批次生成流程
```python
class BatchWriter:
    def __init__(self, batch_size=3):
        self.batch_size = batch_size
        self.context_window = []  # 保持最近3章上下文
    
    def write_batch(self, start_chapter, outlines):
        """生成3章批次"""
        chapters = []
        
        # 并行生成3章初稿
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i in range(self.batch_size):
                chapter_num = start_chapter + i
                future = executor.submit(self.write_chapter, chapter_num, outlines[i])
                futures.append(future)
            
            # 收集结果
            for future in futures:
                chapters.append(future.result())
        
        # 批次内审核
        batch_review = self.review_batch(chapters)
        
        if batch_review["pass"]:
            # 固化内容，清理上下文
            self.context_window = chapters[-self.batch_size:]
            return chapters
        else:
            # 批次内修订
            return self.revise_batch(chapters, batch_review)
```

#### 2.4.3 上下文管理
```python
class ContextManager:
    def __init__(self):
        self.recent_chapters = []  # 最近章节内容
        self.character_states = {} # 人物状态快照
        self.plot_progress = {}    # 情节进展
    
    def update_context(self, new_chapters):
        """更新上下文窗口"""
        # 保留最近3章
        self.recent_chapters = (self.recent_chapters + new_chapters)[-3:]
        
        # 更新人物状态
        for chapter in new_chapters:
            self._extract_character_states(chapter)
        
        # 更新情节进展
        self._update_plot_progress(new_chapters)
    
    def get_context_prompt(self):
        """生成上下文提示"""
        return {
            "recent_chapters": self.recent_chapters,
            "character_states": self.character_states,
            "plot_progress": self.plot_progress,
            "next_requirements": self._generate_next_requirements()
        }
```

### 2.5 PolishAgent（润色Agent）

#### 2.5.1 模块结构
```
polish_agent/
├── __init__.py
├── main.py
├── grammar_checker.py   # 语法检查
├── expression_optimizer.py # 表达优化
├── style_enforcer.py    # 风格强化
├── rhythm_adjuster.py   # 节奏调整
└── change_tracker.py    # 修改追踪
```

#### 2.5.2 四层润色机制
```python
class FourLayerPolishing:
    def polish(self, original_text):
        # 第1层：语法检查
        layer1 = self.grammar_check(original_text)
        
        # 第2层：表达优化
        layer2 = self.expression_optimize(layer1)
        
        # 第3层：风格强化
        layer3 = self.style_enforce(layer2)
        
        # 第4层：节奏调整
        final = self.rhythm_adjust(layer3)
        
        # 记录修改
        changes = self.track_changes(original_text, final)
        
        return {
            "polished_text": final,
            "change_report": changes,
            "quality_improvement": self.calculate_improvement(original_text, final)
        }
```

### 2.6 AuditorAgent（审计Agent）

#### 2.6.1 模块结构
```
auditor_agent/
├── __init__.py
├── main.py
├── plot_auditor.py      # 情节审计
├── character_auditor.py # 人物审计
├── logic_auditor.py     # 逻辑审计
├── style_auditor.py     # 风格审计
├── language_auditor.py  # 语言审计
└── metrics_calculator.py # 指标计算
```

#### 2.6.2 量化指标计算实现
```python
class AuditMetricsCalculator:
    def calculate_precision(self, identified_issues, actual_issues):
        """计算准确率"""
        true_positives = len(set(identified_issues) & set(actual_issues))
        total_identified = len(identified_issues)
        
        if total_identified == 0:
            return 1.0  # 没有识别问题，视为准确
        
        precision = true_positives / total_identified
        return precision
    
    def calculate_recall(self, identified_issues, actual_issues):
        """计算召回率"""
        true_positives = len(set(identified_issues) & set(actual_issues))
        total_actual = len(actual_issues)
        
        if total_actual == 0:
            return 1.0  # 没有实际问题，视为全召回
        
        recall = true_positives / total_actual
        return recall
    
    def calculate_f1(self, precision, recall):
        """计算F1分数"""
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * (precision * recall) / (precision + recall)
        return f1
    
    def calculate_confidence(self, issue):
        """计算问题置信度"""
        factors = {
            "severity": issue.get("severity", 0.5),
            "evidence_strength": issue.get("evidence", 0.5),
            "consistency": issue.get("consistency", 0.5)
        }
        
        confidence = sum(factors.values()) / len(factors)
        
        if confidence >= 0.9:
            return "high"
        elif confidence >= 0.7:
            return "medium"
        else:
            return "low"
```

### 2.7 ReviserAgent（修订Agent）

#### 2.7.1 模块结构
```
reviser_agent/
├── __init__.py
├── main.py
├── issue_analyzer.py    # 问题分析
├── strategy_selector.py # 策略选择
├── revision_generator.py # 修订生成
├── impact_assessor.py   # 影响评估
└── quality_validator.py # 质量验证
```

#### 2.7.2 修订策略体系
```python
class RevisionStrategy:
    def __init__(self):
        self.strategies = {
            "plot_hole": self.fix_plot_hole,
            "character_inconsistency": self.fix_character,
            "style_deviation": self.adjust_style,
            "logic_error": self.correct_logic,
            "language_issue": self.improve_language
        }
    
    def revise(self, text, issues):
        """执行修订"""
        revisions = []
        
        for issue in issues:
            issue_type = issue["type"]
            strategy = self.strategies.get(issue_type, self.default_revision)
            
            # 应用修订策略
            revised_text, changes = strategy(text, issue)
            
            revisions.append({
                "issue": issue,
                "revised_text": revised_text,
                "changes": changes,
                "strategy_used": issue_type
            })
        
        # 合并所有修订
        final_text = self.merge_revisions(text, revisions)
        
        return {
            "final_text": final_text,
            "revisions": revisions,
            "metrics": self.calculate_revision_metrics(revisions)
        }
```

## 3. 系统集成设计

### 3.1 任务流水线控制器
```python
class PipelineController:
    def __init__(self):
        self.agents = {
            "trend": TrendAgent(),
            "style": StyleAgent(),
            "planner": PlannerAgent(),
            "writer": WriterAgent(),
            "polish": PolishAgent(),
            "auditor": AuditorAgent(),
            "reviser": ReviserAgent()
        }
        self.state_manager = StateManager()
    
    def execute_pipeline(self, task_id, novel_title):
        """执行完整流水线"""
        try:
            # 1. 趋势分析
            trend_result = self.agents["trend"].execute(task_id)
            self.state_manager.update(task_id, "trend", "completed", trend_result)
            
            # 2. 风格解析
            style_result = self.agents["style"].execute(task_id)
            self.state_manager.update(task_id, "style", "completed", style_result)
            
            # 3. 策划（3章周期审核）
            planner_result = self.agents["planner"].execute(
                task_id, trend_result, style_result
            )
            self.state_manager.update(task_id, "planner", "completed", planner_result)
            
            # 4. 写作（3章批次生成）
            writer_result = self.agents["writer"].execute(
                task_id, planner_result["outlines"]
            )
            self.state_manager.update(task_id, "writer", "completed", writer_result)
            
            # 5. 润色
            polish_result = self.agents["polish"].execute(
                task_id, writer_result["chapters"]
            )
            self.state_manager.update(task_id, "polish", "completed", polish_result)
            
            # 6. 审计
            audit_result = self.agents["auditor"].execute(
                task_id, polish_result["polished_chapters"]
            )
            self.state_manager.update(task_id, "auditor", "completed", audit_result)
            
            # 7. 修订（如果需要）
            if audit_result["needs_revision"]:
                revision_result = self.agents["reviser"].execute(
                    task_id, audit_result["issues"]
                )
                self.state_manager.update(task_id, "reviser", "completed", revision_result)
            
            # 标记任务完成
            self.state_manager.complete_task(task_id)
            
            return {"status": "success", "task_id": task_id}
            
        except Exception as e:
            self.state_manager.fail_task(task_id, str(e))
            return {"status": "failed", "error": str(e)}
```

### 3.2 状态管理系统
```python
class StateManager:
    def __init__(self, data_dir="backend/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def create_task(self, task_id, novel_title):
        """创建新任务目录结构"""
        task_dir = self.data_dir / "tasks" / task_id
        task_dir.mkdir(parents=True)
        
        # 创建子目录
        (task_dir / "output").mkdir()
        (task_dir / "progress").mkdir()
        (task_dir / "logs").mkdir()
        (task_dir / "memory").mkdir()
        
        # 初始化元数据
        meta = {
            "task_id": task_id,
            "novel_title": novel_title,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "agents": {}
        }
        
        self._write_json(task_dir / "meta.json", meta)
        return task_dir
    
    def update(self, task_id, agent_name, status, result=None):
        """更新Agent状态"""
        task_dir = self.data_dir / "tasks" / task_id
        meta = self._read_json(task_dir / "meta.json")
        
        meta["agents"][agent_name] = {
            "status": status,
            "completed_at": datetime.now().isoformat() if status == "completed" else None,
            "result_summary": self._summarize_result(result) if result else None
        }
        
        # 计算整体进度
        meta["overall_progress"] = self._calculate_progress(meta["agents"])
        
        self._write_json(task_dir / "meta.json", meta)
        
        # 保存详细结果
        if result:
            output_file = task_dir / "output" / f"{agent_name}_result.json"
            self._write_json(output_file, result)
```

### 3.3 数据存储设计

#### 3.3.1 目录结构
```
backend/data/
├── tasks/
│   ├── {task_id}/
│   │   ├── meta.json                    # 任务元数据
│   │   ├── output/                      # Agent输出文件
│   │   │   ├── trend_analysis.json
│   │   │   ├── style_parameters.json
│   │   │   ├── planner/
│   │   │   │   ├── 策划案.md
│   │   │   │   ├── 故事总纲.md
│   │   │   │   └── 章节大纲.md
│   │   │   ├── writer/
│   │   │   │   ├── ch_01_raw.md
│   │   │   │   ├── ch_02_raw.md
│   │   │   │   └── ...
│   │   │   ├── polish/
│   │   │   │   ├── ch_01_polished.md
│   │   │   │   └── ...
│   │   │   ├── audit_report.json
│   │   │   └── revision_report.json
│   │   ├── progress/                    # 进度文件
│   │   │   ├── TrendAgent.json
│   │   │   ├── PlannerAgent.json
│   │   │   └── ...
│   │   ├── logs/                        # 日志文件
│   │   │   ├── TrendAgent.jsonl
│   │   │   ├── PlannerAgent.jsonl
│   │   │   └── ...
│   │   └── memory/                      # 长期记忆
│   │       ├── 7_truths_trend.md
│   │       ├── 7_truths_style.md
│   │       └── ...
├── genre_library.db                     # 题材库数据库
└── system/
    ├── config.json                      # 系统配置
    └── cache/                           # 缓存数据
```

#### 3.3.2 文件格式规范
1. **JSON文件**：所有结构化数据使用JSON格式
2. **Markdown文件**：文本内容使用Markdown格式
3. **日志文件**：JSON Lines格式，每行一个日志记录
4. **进度文件**：实时更新的JSON状态文件

### 3.4 错误处理与恢复

#### 3.4.1 错误分类
```python
class ErrorHandler:
    ERROR_TYPES = {
        "llm_timeout": {"retry": 3, "backoff": 2.0},
        "network_error": {"retry": 5, "backoff": 1.5},
        "parse_error": {"retry": 2, "backoff": 1.0},
        "validation_error": {"retry": 1, "backoff": 1.0},
        "resource_error": {"retry": 0, "backoff": 0.0}  # 需要人工干预
    }
    
    def handle_error(self, error_type, context):
        """处理错误并决定恢复策略"""
        strategy = self.ERROR_TYPES.get(error_type, {"retry": 1, "backoff": 1.0})
        
        if strategy["retry"] > 0:
            return {
                "action": "retry",
                "max_retries": strategy["retry"],
                "backoff_factor": strategy["backoff"]
            }
        else:
            return {
                "action": "escalate",
                "requires_human": True,
                "error_context": context
            }
```

#### 3.4.2 状态恢复机制
```python
class StateRecovery:
    def recover_task(self, task_id):
        """恢复中断的任务"""
        task_dir = self.data_dir / "tasks" / task_id
        meta = self._read_json(task_dir / "meta.json")
        
        # 找出最后一个完成的Agent
        last_completed = None
        for agent, info in meta["agents"].items():
            if info["status"] == "completed":
                last_completed = agent
        
        if last_completed:
            # 从最后一个完成的Agent继续
            next_agent = self._get_next_agent(last_completed)
            return {
                "recovery_point": last_completed,
                "next_agent": next_agent,
                "resume_data": self._load_agent_output(task_dir, last_completed)
            }
        else:
            # 从头开始
            return {"recovery_point": "start", "next_agent": "trend"}
```

## 4. 与现有项目的集成

### 4.1 现有代码分析
基于对现有项目的分析，需要以下调整：

#### 4.1.1 需要增强的模块
1. **TrendAgent**：
   - 添加题材库数据库管理
   - 实现每日自动更新机制
   - 增加相似度计算和热度衰减

2. **PlannerAgent**：
   - 实现3章周期审核机制
   - 添加加权随机题材选择算法
   - 完善审核量化标准计算

3. **WriterAgent**：
   - 实现3章批次生成机制
   - 添加批次内审核和一致性检查
   - 改进上下文管理

4. **AuditorAgent**：
   - 添加量化指标计算（准确率、召回率、F1）
   - 实现置信度评分系统
   - 完善问题类型覆盖

#### 4.1.2 需要新增的模块
1. **GenreLibrary**：题材库管理模块
2. **BatchController**：批次控制模块
3. **MetricsCalculator**：指标计算模块
4. **ContextManager**：上下文管理模块

### 4.2 部署架构

#### 4.2.1 服务器环境（裸机部署）
```
服务器：104.244.90.202:9000
部署目录：/opt/ai-novel-agent/
服务管理：systemd (ai-novel-agent.service)
Python环境：/opt/ai-novel-agent/venv/
数据库：SQLite (genre_library.db)
```

#### 4.2.2 服务配置
```ini
# systemd服务配置
[Unit]
Description=AI Novel Agent System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ai-novel-agent
Environment="PATH=/opt/ai-novel-agent/venv/bin"
ExecStart=/opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4.2.3 目录权限
```bash
# 目录结构
/opt/ai-novel-agent/
├── backend/          # 源代码
├── data/            # 数据目录（需要读写权限）
├── venv/           # Python虚拟环境
├── logs/           # 系统日志
└── config/         # 配置文件

# 权限设置
chown -R root:root /opt/ai-novel-agent
chmod 755 /opt/ai-novel-agent
chmod -R 755 /opt/ai-novel-agent/backend
chmod -R 777 /opt/ai-novel-agent/data  # 数据目录需要写权限
```

### 4.3 监控与维护

#### 4.3.1 健康检查
```python
class HealthMonitor:
    def check_system_health(self):
        checks = {
            "disk_space": self.check_disk_space(),
            "memory_usage": self.check_memory(),
            "llm_connectivity": self.check_llm(),
            "database_health": self.check_database(),
            "agent_status": self.check_agents()
        }
        
        overall = all(check["healthy"] for check in checks.values())
        
        return {
            "overall_health": overall,
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        }
```

#### 4.3.2 日志系统
```python
class LogSystem:
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
    
    def log_agent(self, agent_name, level, message, data=None):
        """记录Agent日志"""
        log_file = self.log_dir / f"{agent_name}.jsonl"
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "level": level,
            "message": message,
            "data": data
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
```

## 5. 实施计划

### 5.1 第一阶段：核心机制实现
1. **题材库管理系统** (3天)
   - 实现GenreLibrary模块
   - 添加每日更新定时任务
   - 实现相似度计算和热度衰减

2. **3章周期审核机制** (5天)
   - 修改PlannerAgent支持批次审核
   - 实现固化设定机制
   - 添加审核量化标准计算

3. **3章批次生成机制** (4天)
   - 修改WriterAgent支持批次生成
   - 实现批次内审核
   - 添加上下文管理

### 5.2 第二阶段：量化指标系统
1. **审计量化指标** (3天)
   - 实现准确率、召回率计算
   - 添加置信度评分
   - 完善问题类型覆盖

2. **性能监控系统** (2天)
   - 添加健康检查
   - 实现日志系统
   - 添加错误统计

### 5.3 第三阶段：系统集成与测试
1. **系统集成测试** (3天)
   - 端到端流水线测试
   - 错误恢复测试
   - 性能压力测试

2. **部署与优化** (2天)
   - 生产环境部署
   - 性能调优
   - 监控配置

## 6. 总结

本概要设计基于需求文档，结合现有项目实现，提出了完整的系统架构方案。重点包括：

1. **7个Agent的详细设计**：每个Agent都有明确的模块结构和算法实现
2. **3章周期审核机制**：核心创新点，确保质量的同时提高效率
3. **量化指标系统**：使审核和修订过程可衡量、可优化
4. **健壮性设计**：完善的错误处理和状态恢复机制
5. **与现有项目集成**：基于现有代码，最小化改动，最大化价值

所有设计都考虑了实际部署环境（裸机服务器），确保可实施性和可维护性。── main.py              # 主执行入口
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