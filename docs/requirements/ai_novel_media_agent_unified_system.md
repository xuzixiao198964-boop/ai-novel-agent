# AI Novel Media Agent 统一系统详细需求文档

## 文档信息
- **文档编号**: REQ-UNIFIED-DETAIL-001
- **文档标题**: AI小说生成与视频生成统一系统详细需求
- **项目名称**: AI Novel Media Agent
- **创建日期**: 2026-03-31
- **创建人**: AI Novel Agent Assistant
- **状态**: 📝 详细设计版
- **版本**: 1.0

## 1. 系统概述

### 1.1 项目目标
将AI Novel Agent（7个Agent的小说生成系统）与Media Agent（资讯转视频系统）深度整合，构建一个完整的AI内容创作平台，支持：
1. **AI自动生成小说** - 继承完整的7个Agent流水线
2. **小说转视频** - 将生成的小说转换为多种格式的视频
3. **资讯转视频** - 抓取最新资讯并生成视频
4. **多模式选择** - 用户可选择生成模式（仅配音/仅字幕/动画等）
5. **成本与时间测算** - 提供完整的成本和时间预估

### 1.2 核心价值
- **一站式创作**: 从创意到小说到视频的完整流程
- **多模式输出**: 满足不同平台和用户需求
- **智能优化**: 基于AI的内容优化和质量控制
- **成本透明**: 清晰的成本测算和优化建议

### 1.3 技术基础
- **现有服务器**: 104.244.90.202:9000（AI Novel Agent已部署）
- **AI模型**: DeepSeek Chat（已集成，API Key已配置）
- **视频处理**: FFmpeg + 阿里云百炼VideoRetalk
- **TTS服务**: 腾讯云TTS + Edge TTS + OpenAI TTS
- **数据库**: PostgreSQL + Redis

## 2. 详细功能需求

### 2.1 用户工作流

#### 2.1.1 完整创作流程
```
用户选择创作类型 → 配置参数 → 系统生成 → 预览调整 → 发布分享
      ↓
1. 小说创作流程：
   选择题材 → 设置篇幅 → AI生成小说 → 章节审核 → 下载/发布
   
2. 视频创作流程：
   选择来源（小说/资讯） → 选择模式 → 配置参数 → 生成视频 → 发布
   
3. 混合创作流程：
   生成小说 → 选择章节 → 转为视频 → 组合发布
```

#### 2.1.2 用户界面流程
```
主界面 → 创作中心 → 选择类型 → 参数配置 → 任务提交 → 进度监控 → 结果查看
      ↓
导航菜单：
- 首页：系统概览、快速开始
- 小说创作：新建小说、我的小说、小说库
- 视频创作：新建视频、我的视频、视频库
- 内容管理：素材库、模板库、抓取源
- 发布管理：发布任务、平台管理、数据统计
- 账户中心：个人信息、任务历史、成本统计
```

### 2.2 AI小说生成模块（继承AI Novel Agent）

#### 2.2.1 7个Agent详细功能

**1. TrendAgent（趋势分析Agent）**
- **数据源**:
  - 小说平台API：起点、晋江、纵横等
  - 网页爬虫：热门榜单、新书榜
  - 第三方数据：阅读趋势、读者画像
- **分析维度**:
  - 题材热度：实时排名和趋势
  - 读者偏好：年龄、性别、阅读习惯
  - 市场机会：蓝海题材识别
- **输出**:
  - 热门题材推荐（前20名）
  - 章节数建议范围
  - 字数分布建议
  - 创新题材识别

**2. StyleAgent（风格解析Agent）**
- **分析内容**:
  - 语言风格：文言、白话、网络用语
  - 叙事节奏：快节奏、慢节奏、起伏节奏
  - 描写特点：详细描写、简洁叙述
  - 情感表达：强烈、含蓄、多变
- **输出**:
  - 风格参数配置文件
  - 可量化的风格指标
  - 风格匹配度评分

**3. PlannerAgent（策划Agent）**
- **核心功能**:
  - 故事总纲生成：三幕式结构
  - 人物设定：主角、配角、反派
  - 世界观构建：时间、空间、规则
  - 章节大纲：详细章节规划
- **审核机制**:
  - 3章周期审核：前3章深度审核
  - 多轮优化：基于反馈迭代
  - 质量评分：结构、人物、情节评分

**4. WriterAgent（写作Agent）**
- **生成策略**:
  - 上下文引用：前两章引子+故事总纲
  - 风格保持：遵循StyleAgent参数
  - 质量控制：章节完整性检查
- **批量生成**:
  - 3章批次生成
  - 并行处理优化
  - 进度实时反馈

**5. PolishAgent（润色Agent）**
- **润色维度**:
  - 语言优化：词汇替换、句式调整
  - 逻辑检查：情节连贯性
  - 风格统一：保持整体风格
  - 错误修正：错别字、语法错误

**6. AuditorAgent（审核Agent）**
- **审核标准**:
  - 结构完整性：30%
  - 人物一致性：25%
  - 情节合理性：20%
  - 语言质量：15%
  - 创新性：10%
- **评分机制**:
  - 总分≥80分通过
  - 各维度≥60分
  - 详细评分报告

**7. ReviserAgent（修订Agent）**
- **修订策略**:
  - 问题定位：基于审核报告
  - 智能修订：AI辅助修改
  - 人工确认：关键修改确认
  - 版本管理：修订历史记录

#### 2.2.2 小说篇幅选择系统

**篇幅等级**:
1. **微型小说**: 1-3章，每章1000-2000字
   - 适合：短篇故事、试读章节
   - 时间：30分钟-1小时
   - 成本：¥0.5-1.0

2. **短篇小说**: 6-18章，每章2000-3000字
   - 适合：完整短篇、系列开头
   - 时间：1-3小时
   - 成本：¥1.5-3.0

3. **中篇小说**: 18-54章，每章2500-3500字
   - 适合：网络小说、连载作品
   - 时间：3-6小时
   - 成本：¥3.0-6.0

4. **长篇小说**: 54-162章，每章3000-4000字
   - 适合：长篇连载、出版作品
   - 时间：6-12小时
   - 成本：¥6.0-12.0

5. **超长篇小说**: 162+章，每章3500-4500字
   - 适合：史诗巨作、系列作品
   - 时间：12-24小时
   - 成本：¥12.0-24.0

**自定义设置**:
- 章节数：1-500章
- 每章字数：1000-5000字
- 更新频率：每日/每周/自定义
- 题材混合：支持多题材融合

#### 2.2.3 内容抓取扩展

**抓取源管理**:
```
小说平台：
- 起点中文网：玄幻、都市、科幻
- 晋江文学城：言情、耽美、穿越
- 纵横中文网：武侠、历史、军事
- 17K小说网：都市、玄幻、灵异
- 番茄小说：免费阅读、热门题材

资讯平台：
- 新闻媒体：人民日报、新华社、央视新闻
- 科技媒体：36氪、虎嗅、钛媒体
- 娱乐媒体：微博热搜、豆瓣话题
- 社交媒体：知乎、小红书、B站
```

**抓取策略**:
- 频率控制：避免触发反爬机制
- 内容过滤：质量评分和去重
- 实时更新：每日更新题材库
- 智能推荐：基于用户偏好推荐

### 2.3 视频生成模块（继承Media Agent）

#### 2.3.1 视频生成模式详细说明

**模式1：仅配音模式（快速经济）**
```
适用场景：
- 有声小说、广播剧
- 知识讲解、课程录制
- 快速内容制作

技术实现：
1. 文本转语音（TTS）
   - 腾讯云TTS（高质量）
   - Edge TTS（本地备选）
   - 多音色选择

2. 背景处理
   - 静态图片背景
   - 简单动画效果
   - 图片轮播

3. 输出配置
   - 分辨率：720P/1080P
   - 时长：跟随语音时长
   - 格式：MP4/H.264

成本估算：
- TTS：¥0.03/千字
- 处理：¥0.01/分钟
- 总计：约¥0.5-2.0/视频
```

**模式2：仅字幕模式（阅读友好）**
```
适用场景：
- 小说章节阅读
- 新闻资讯阅读
- 教育学习内容

技术实现：
1. 字幕生成
   - 语音识别（ASR）
   - 文案同步
   - 字级别时间对齐

2. 视觉设计
   - 可读性字体
   - 舒适配色
   - 背景虚化

3. 交互功能
   - 阅读进度控制
   - 字体大小调整
   - 背景切换

成本估算：
- 字幕生成：¥0.02/分钟
- 视觉处理：¥0.01/分钟
- 总计：约¥0.3-1.5/视频
```

**模式3：动画模式（生动有趣）**
```
适用场景：
- 儿童故事
- 奇幻小说
- 品牌宣传

技术实现：
1. 角色生成
   - AI生成角色形象
   - 表情动画
   - 动作设计

2. 场景生成
   - 背景生成
   - 特效添加
   - 转场动画

3. 口型同步
   - 阿里云百炼VideoRetalk
   - 实时口型匹配
   - 表情同步

成本估算：
- 角色生成：¥1.0-3.0/角色
- 动画处理：¥0.5-2.0/分钟
- 总计：约¥5.0-20.0/视频
```

**模式4：混合模式（完整体验）**
```
适用场景：
- 高质量内容制作
- 商业项目
- 重要发布

技术实现：
1. 完整流程
   - 配音 + 字幕 + 动画
   - 背景音乐 + 音效
   - 专业转场

2. 质量控制
   - 多轮审核
   - 人工调整
   - 最终优化

3. 输出选项
   - 多分辨率支持
   - 多格式输出
   - 平台适配

成本估算：
- 综合成本：¥10.0-50.0/视频
- 时间成本：30分钟-2小时
```

**模式5：资讯转视频模式（自动化）**
```
适用场景：
- 新闻摘要
- 行业报告
- 每日资讯

技术实现：
1. 资讯抓取
   - RSS源管理
   - 智能解析
   - 内容摘要

2. 自动生成
   - AI文案生成
   - TTS合成
   - 视频模板匹配

3. 定时发布
   - 计划任务
   - 多平台发布
   - 效果监控

成本估算：
- 批量处理：¥0.1-0.5/视频
- 自动化节省：70%人工成本
```

#### 2.3.2 视频处理技术栈

**核心组件**:
1. **FFmpeg** - 本地视频处理
   - 视频转码：H.264/H.265
   - 音频处理：AAC/MP3
   - 滤镜效果：缩放、裁剪、水印
   - 合成功能：多轨道合成

2. **阿里云百炼VideoRetalk** - 口型替换
   - 输入：视频 + 音频
   - 输出：口型同步视频
   - 分辨率：480P/720P/1080P
   - 异步处理：任务队列管理

3. **TTS服务** - 语音合成
   - 腾讯云TTS：高质量，支持音色克隆
   - Edge TTS：本地备选，无需API
   - OpenAI TTS：备选方案
   - 语音选择：基于语言自动选择

4. **字幕系统** - 字幕生成
   - 语音识别：Whisper模型
   - 时间对齐：动态时间规整
   - 样式设计：可配置字体样式
   - 格式支持：SRT、ASS、VTT

**模板系统**:
```
视频模板库：
1. 小说阅读模板
   - 竖屏布局
   - 翻页效果
   - 背景音乐

2. 新闻播报模板
   - 横屏布局
   - 主持人形象
   - 新闻字幕条

3. 儿童故事模板
   - 卡通风格
   - 角色动画
   - 互动元素

4. 知识讲解模板
   - 白板风格
   - 重点标注
   - 进度指示

模板配置：
- 尺寸：横屏(16:9)、竖屏(9:16)、方形(1:1)
- 风格：简约、华丽、卡通、商务
- 元素：标题、字幕、水印、Logo
- 动画：入场、转场、出场
```

### 2.4 成本测算系统

#### 2.4.1 成本构成分析

**1. AI API成本**
```
DeepSeek API：
- 模型：deepseek-chat
- 定价：约¥0.01/千Tokens
- 小说生成估算：
  * 微型小说：10K Tokens ≈ ¥0.10
  * 短篇小说：50K Tokens ≈ ¥0.50
  * 中篇小说：150K Tokens ≈ ¥1.50
  * 长篇小说：450K Tokens ≈ ¥4.50

TTS API成本：
- 腾讯云TTS：¥0.03/千字
- 小说配音估算：
  * 每章3000字：¥0.09
  * 短篇小说（6章）：¥0.54
  * 长篇小说（54章）：¥4.86

视频处理API：
- 阿里云百炼：¥0.5/分钟
- 10分钟视频：¥5.0
```

**2. 服务器成本**
```
基础成本：
- VPS租用：¥150/月（2核4G 50GB）
- 带宽：1TB/月 ≈ ¥50
- 存储扩展：每50GB ≈ ¥30/月

处理成本：
- CPU时间：按处理时间计算
- 内存使用：按峰值使用计算
- 存储IO：按读写量计算

优化策略：
- 资源复用：相同内容缓存
- 错峰处理：夜间处理大任务
- 批量优化：批量处理降低成本
```

**3. 人工成本（如需）**
```
审核成本：
- 自动审核：系统自动，成本可忽略
- 人工审核：按时间计费，¥50-100/小时
- 修改调整：根据修改范围计算

优化成本：
- 内容优化：基于反馈迭代
- 质量提升：额外处理成本
- 定制需求：特殊要求加价
```

#### 2.4.2 完整流程成本测算示例

**示例1：生成54章小说并转为动画视频**
```
1. 小说生成阶段：
   - DeepSeek API：450K Tokens ≈ ¥4.50
   - 服务器处理：3小时 ≈ ¥1.50
   - 小计：¥6.00

2. 视频生成阶段：
   - TTS合成：54章 × 3000字 ≈ ¥4.86
   - 动画生成：10分钟 ≈ ¥15.00
   - 口型同步：10分钟 ≈ ¥5.00
   - 服务器处理：2小时 ≈ ¥1.00
   - 小计：¥25.86

3. 总成本：¥31.86
4. 总时间：5-8小时
5. 产出：54章小说 + 10分钟动画视频
```

**示例2：资讯每日自动转视频**
```
每日处理10条资讯：
1. 资讯抓取：免费（RSS源）
2. AI摘要：10条 × 500 Tokens ≈ ¥0.05
3. TTS合成：10条 × 300字 ≈ ¥0.09
4. 视频合成：10条 × 1分钟 ≈ ¥5.00
5. 服务器处理：1小时 ≈ ¥0.50

每日成本：¥5.64
每月成本（30天）：¥169.20
产出：300条资讯视频/月
```

#### 2.4.3 成本优化策略

**技术优化**:
1. **缓存策略**:
   - 相同内容缓存复用
   - 模板缓存加速
   - 中间结果缓存

2. **批量处理**:
   - 批量API调用折扣
   - 批量任务优化调度
   - 资源集中使用

3. **算法优化**:
   - 高效算法减少计算量
   - 近似算法平衡质量成本
   - 预处理减少实时计算

**运营优化**:
1. **错峰处理**:
   - 夜间处理大任务
   - 利用空闲资源
   - 动态调整处理时间

2. **资源管理**:
   - 监控资源使用
   - 自动扩缩容
   - 成本预警机制

3. **用户教育**:
   - 成本透明展示
   - 优化建议提供
   - 最佳实践分享

### 2.5 发布管理系统

#### 2.5.1 发布平台支持

**小说发布平台**:
1. **起点中文网**（模拟发布）
   - 章节发布
   - 作品管理
   - 数据统计

2. **晋江文学城**（模拟发布）
   - 言情小说发布
   - 章节更新
   - 读者互动

3. **自有平台**（实际发布）
   - 网站展示
   - 移动端阅读
   - 付费订阅

**视频发布平台**:
1. **抖音**（核心平台）
   - 短视频发布（≤15分钟）
   - 话题标签
   - 位置信息
   - @好友功能

2. **小红书**（核心平台）
   - 图文笔记+短视频
   - 标签系统
   - 社区互动

3. **B站**（备选平台）
   - 中长视频
   - 弹幕互动
   - 专栏文章

4. **微信视频号**（备选平台）
   - 社交传播
   - 朋友圈分享
   - 公众号关联

#### 2.5.2 发布策略配置

**发布时机**:
1. **立即发布**: 生成完成后立即发布
2. **定时发布**: 指定具体时间发布
3. **计划发布**: 按计划自动发布
4. **条件发布**: 满足条件时发布

**发布频率**:
- 单个平台：每小时≤5个，每天≤50个
- 多平台：根据平台限制调整
- 批量发布：支持批量任务调度

**审核流程**:
```
发布前审核：
1. 内容合规检查
   - 敏感词过滤
   - 版权检查
   - 平台规范符合

2. 质量审核
   - 自动评分
   - 人工抽查
   - 修改建议

3. 平台适配
   - 格式转换
   - 元数据适配
   - 标签优化

发布后监控：
1. 状态跟踪
2. 效果分析
3. 异常处理
```

#### 2.5.3 发布效果分析

**关键指标**:
1. **发布成功率**:
   - 各平台成功率
   - 失败原因分析
   - 改进措施

2. **内容表现**:
   - 观看量/阅读量
   - 互动数据（点赞、评论、分享）
   - 完播率/阅读完成率

3. **用户增长**:
   - 粉丝增长
   - 用户留存
   - 付费转化

**分析报告**:
- 日报/周报/月报
- 平台对比分析
- 内容类型效果分析
- 优化建议生成

## 3. 技术架构设计

### 3.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户界面层 (Web前端)                      │
├─────────────────────────────────────────────────────────────┤
│ 小说创作 │ 视频创作 │ 内容管理 │ 发布管理 │ 数据统计 │ 用户中心 │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    API网关层 (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│ 认证授权 │ 请求路由 │ 限流控制 │ 日志记录 │ 监控上报 │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    业务逻辑层 (Python)                       │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ 小说生成模块 │ 视频生成模块 │ 内容抓取模块 │ 发布管理模块 │
│ 7个Agent流水 │ 5种生成模式  │ 多源抓取     │ 多平台发布   │
└──────────────┴──────────────┴──────────────┴──────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    任务队列层 (Celery)                       │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ 高优先级队列 │ 普通优先级队 │ 低优先级队列 │ 定时任务队列 │
│ 用户交互任务 │ 内容生成任务 │ 后台处理任务 │ 计划任务     │
└──────────────┴──────────────┴──────────────┴──────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    数据存储层                                │
├──────────────┬──────────────┬──────────────┬──────────────┤
│ PostgreSQL   │ Redis缓存    │ 文件存储     │ 外部API      │
│ 结构化数据   │ 会话/缓存    │ 媒体文件     │ AI/云服务    │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

### 3.2 核心模块设计

#### 3.2.1 小说生成模块架构

```
小说生成控制器
    │
    ├── TrendAgent (趋势分析)
    │    ├── 数据采集器
    │    ├── 趋势分析器
    │    └── 推荐引擎
    │
    ├── StyleAgent (风格解析)
    │    ├── 风格分析器
    │    ├── 参数提取器
    │    └── 模板匹配器
    │
    ├── PlannerAgent (策划生成)
    │    ├── 故事生成器
    │    ├── 大纲构建器
    │    └── 审核控制器
    │
    ├── WriterAgent (正文写作)
    │    ├── 章节生成器
    │    ├── 上下文管理器
    │    └── 批量处理器
    │
    ├── PolishAgent (内容润色)
    │    ├── 语言优化器
    │    ├── 逻辑检查器
    │    └── 风格统一器
    │
    ├── AuditorAgent (质量审核)
    │    ├── 评分系统
    │    ├── 问题检测器
    │    └── 报告生成器
    │
    └── ReviserAgent (修订优化)
         ├── 问题定位器
         ├── 智能修订器
         └── 版本管理器
```

#### 3.2.2 视频生成模块架构

```
视频生成控制器
    │
    ├── 模式选择器
    │    ├── 仅配音模式
    │    ├── 仅字幕模式
    │    ├── 动画模式
    │    ├── 混合模式
    │    └── 资讯转视频模式
    │
    ├── 素材处理器
    │    ├── 文本处理器 (TTS)
    │    ├── 图像处理器
    │    ├── 音频处理器
    │    └── 视频处理器 (FFmpeg)
    │
    ├── 合成引擎
    │    ├── 时间轴管理器
    │    ├── 轨道合成器
    │    ├── 特效添加器
    │    └── 输出编码器
    │
    ├── 质量控制
    │    ├── 自动审核
    │    ├── 人工审核接口
    │    └── 优化建议
    │
    └── 成本计算器
         ├── API成本计算
         ├── 服务器成本计算
         ├── 时间成本计算
         └── 优化建议生成
```

#### 3.2.3 统一任务调度系统

```
任务调度中心
    │
    ├── 任务接收器
    │    ├── API接口
    │    ├── WebSocket推送
    │    └── 批量导入
    │
    ├── 任务分类器
    │    ├── 小说生成任务
    │    ├── 视频生成任务
    │    ├── 内容抓取任务
    │    └── 发布任务
    │
    ├── 优先级管理器
    │    ├── 紧急任务 (用户交互)
    │    ├── 高优先级 (付费用户)
    │    ├── 普通优先级 (免费用户)
    │    └── 低优先级 (后台任务)
    │
    ├── 资源调度器
    │    ├── CPU资源管理
    │    ├── 内存资源管理
    │    ├── 网络资源管理
    │    └── 存储资源管理
    │
    ├── 进度监控器
    │    ├── 实时进度更新
    │    ├── 预估时间计算
    │    ├── 异常检测
    │    └── 自动恢复
    │
    └── 结果处理器
         ├── 成功处理
         ├── 失败处理
         ├── 重试机制
         └── 通知发送
```

### 3.3 数据库设计

#### 3.3.1 核心数据表

**用户相关表**:
```sql
-- 用户表 (继承Media Agent)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    display_name VARCHAR(50),
    avatar_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户偏好表
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    novel_preferences JSONB,  -- 小说偏好
    video_preferences JSONB,  -- 视频偏好
    notification_settings JSONB,  -- 通知设置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**小说相关表**:
```sql
-- 小说作品表
CREATE TABLE novels (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    genre VARCHAR(50),  -- 题材
    total_chapters INTEGER,  -- 总章节数
    total_words INTEGER,  -- 总字数
    status VARCHAR(20),  -- 状态: drafting, generating, completed, published
    style_parameters JSONB,  -- 风格参数
    outline JSONB,  -- 故事大纲
    cost_estimation JSONB,  -- 成本估算
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 小说章节表
CREATE TABLE novel_chapters (
    id SERIAL PRIMARY KEY,
    novel_id INTEGER REFERENCES novels(id),
    chapter_number INTEGER NOT NULL,
    title VARCHAR(200),
    content TEXT,
    word_count INTEGER,
    quality_score INTEGER,  -- 质量评分
    review_status VARCHAR(20),  -- 审核状态
    generated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**视频相关表**:
```sql
-- 视频作品表
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    source_type VARCHAR(20),  -- 来源类型: novel, article, custom
    source_id INTEGER,  -- 来源ID
    generation_mode VARCHAR(20),  -- 生成模式
    duration INTEGER,  -- 时长(秒)
    resolution VARCHAR(20),  -- 分辨率
    file_path VARCHAR(500),  -- 文件路径
    cost_estimation JSONB,  -- 成本估算
    status VARCHAR(20),  -- 状态
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 视频生成任务表
CREATE TABLE video_generation_tasks (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    task_type VARCHAR(50),  -- 任务类型: tts, animation, synthesis
    parameters JSONB,  -- 任务参数
    status VARCHAR(20),  -- 状态
    progress INTEGER,  -- 进度(0-100)
    result JSONB,  -- 结果数据
    error_message TEXT,  -- 错误信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**任务相关表**:
```sql
-- 统一任务表
CREATE TABLE unified_tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    task_type VARCHAR(50),  -- 任务类型: novel_generation, video_generation
    parameters JSONB,  -- 任务参数
    priority INTEGER DEFAULT 0,  -- 优先级
    status VARCHAR(20),  -- 状态: pending, running, completed, failed
    progress INTEGER DEFAULT 0,  -- 进度
    estimated_time INTEGER,  -- 预估时间(秒)
    actual_time INTEGER,  -- 实际时间(秒)
    cost_estimation JSONB,  -- 成本估算
    actual_cost JSONB,  -- 实际成本
    result JSONB,  -- 结果数据
    error_message TEXT,  -- 错误信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 任务队列表
CREATE TABLE task_queue (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES unified_tasks(id),
    queue_name VARCHAR(50),  -- 队列名称
    position INTEGER,  -- 在队列中的位置
    scheduled_time TIMESTAMP,  -- 计划执行时间
    assigned_worker VARCHAR(100),  -- 分配的worker
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**发布相关表**:
```sql
-- 发布平台表
CREATE TABLE publish_platforms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,  -- 平台名称
    platform_type VARCHAR(20),  -- 平台类型: novel, video
    api_config JSONB,  -- API配置
    limits JSONB,  -- 限制条件
    status VARCHAR(20),  -- 状态
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 发布任务表
CREATE TABLE publish_tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    content_type VARCHAR(20),  -- 内容类型: novel, video
    content_id INTEGER,  -- 内容ID
    platform_id INTEGER REFERENCES publish_platforms(id),
    publish_time TIMESTAMP,  -- 发布时间
    status VARCHAR(20),  -- 状态
    result JSONB,  -- 发布结果
    metrics JSONB,  -- 效果指标
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.3.2 数据关系图

```
users
  │
  ├── novels (1:n) - 用户的小说作品
  │     └── novel_chapters (1:n) - 小说的章节
  │
  ├── videos (1:n) - 用户的视频作品
  │     └── video_generation_tasks (1:n) - 视频生成任务
  │
  ├── unified_tasks (1:n) - 用户的任务
  │     └── task_queue (1:1) - 任务队列位置
  │
  └── publish_tasks (1:n) - 用户的发布任务
        └── publish_platforms (n:1) - 发布平台
```

### 3.4 API接口设计

#### 3.4.1 核心API端点

**用户认证API**:
```http
POST /api/auth/register     # 用户注册
POST /api/auth/login        # 用户登录
POST /api/auth/logout       # 用户登出
POST /api/auth/refresh      # 刷新令牌
GET  /api/auth/profile      # 获取用户信息
PUT  /api/auth/profile      # 更新用户信息
```

**小说生成API**:
```http
POST /api/novels            # 创建小说生成任务
GET  /api/novels            # 获取小说列表
GET  /api/novels/{id}       # 获取小说详情
GET  /api/novels/{id}/chapters  # 获取小说章节
POST /api/novels/{id}/generate  # 继续生成章节
PUT  /api/novels/{id}       # 更新小说信息
DELETE /api/novels/{id}     # 删除小说
```

**视频生成API**:
```http
POST /api/videos            # 创建视频生成任务
GET  /api/videos            # 获取视频列表
GET  /api/videos/{id}       # 获取视频详情
GET  /api/videos/{id}/preview  # 获取视频预览
POST /api/videos/{id}/regenerate  # 重新生成视频
PUT  /api/videos/{id}       # 更新视频信息
DELETE /api/videos/{id}     # 删除视频
```

**任务管理API**:
```http
POST /api/tasks             # 提交任务
GET  /api/tasks             # 获取任务列表
GET  /api/tasks/{id}        # 获取任务详情
GET  /api/tasks/{id}/progress  # 获取任务进度
POST /api/tasks/{id}/cancel  # 取消任务
GET  /api/tasks/queue       # 获取任务队列状态
```

**发布管理API**:
```http
POST /api/publish           # 提交发布任务
GET  /api/publish           # 获取发布任务列表
GET  /api/publish/{id}      # 获取发布任务详情
POST /api/publish/{id}/retry  # 重试发布任务
DELETE /api/publish/{id}    # 取消发布任务

GET  /api/publish/platforms  # 获取发布平台列表
PUT  /api/publish/platforms/{id}  # 更新发布平台配置
```

**成本测算API**:
```http
POST /api/cost/estimate     # 成本估算
GET  /api/cost/history      # 成本历史记录
GET  /api/cost/statistics   # 成本统计
GET  /api/cost/optimization # 成本优化建议
```

#### 3.4.2 WebSocket接口

**实时通信**:
```javascript
// 连接WebSocket
const ws = new WebSocket('ws://104.244.90.202:9000/ws');

// 消息类型
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch(data.type) {
    case 'task_progress':  // 任务进度更新
      updateProgress(data.task_id, data.progress, data.message);
      break;
    case 'task_completed': // 任务完成
      showCompletion(data.task_id, data.result);
      break;
    case 'task_failed':    // 任务失败
      showError(data.task_id, data.error);
      break;
    case 'notification':   // 系统通知
      showNotification(data.message, data.level);
      break;
  }
};

// 发送消息
ws.send(JSON.stringify({
  type: 'subscribe_task',
  task_id: 'task_123'
}));
```

### 3.5 部署架构

#### 3.5.1 服务器配置

**现有服务器利用**:
```
服务器: 104.244.90.202 (远程VPS)
现有服务: AI Novel Agent (端口9000)
计划部署: AI Novel Media Agent 统一系统

端口分配:
- 主服务: 9000 (FastAPI)
- 前端: 8001 (Nginx代理)
- 数据库: 5432 (PostgreSQL)
- Redis: 6379
- 监控: 9091 (Prometheus)
```

**服务组件**:
```yaml
services:
  web:
    image: fastapi-app
    ports: ["9000:9000"]
    depends_on: [db, redis]
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/ai_novel_media
      - REDIS_URL=redis://redis:6379/0
      - DEEPSEEK_API_KEY=sk-9fcc8f6d0ce94fdbbe66b152b7d3e485
  
  db:
    image: postgres:15
    volumes: ["./data/db:/var/lib/postgresql/data"]
    environment:
      - POSTGRES_DB=ai_novel_media
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
  
  redis:
    image: redis:7-alpine
    volumes: ["./data/redis:/data"]
  
  celery:
    image: celery-worker
    depends_on: [redis, db]
    command: celery -A tasks worker --loglevel=info
  
  nginx:
    image: nginx:alpine
    ports: ["8001:80"]
    volumes: ["./nginx.conf:/etc/nginx/nginx.conf"]
    depends_on: [web]
```

#### 3.5.2 文件存储结构

```
/opt/ai-novel-media-agent/
├── backend/                    # 后端代码
│   ├── app/                   # 应用代码
│   │   ├── api/              # API接口
│   │   ├── core/             # 核心模块
│   │   ├── models/           # 数据模型
│   │   ├── services/         # 业务服务
│   │   └── tasks/            # 异步任务
│   ├── requirements.txt       # Python依赖
│   └── main.py               # 应用入口
├── frontend/                  # 前端代码
│   ├── public/               # 静态资源
│   └── src/                  # 源代码
├── data/                      # 数据存储
│   ├── db/                   # 数据库文件
│   ├── redis/                # Redis数据
│   ├── uploads/              # 上传文件
│   │   ├── novels/          # 小说文件
│   │   ├── videos/          # 视频文件
│   │   ├── images/          # 图片素材
│   │   └── temp/            # 临时文件
│   └── backups/              # 备份文件
├── config/                    # 配置文件
│   ├── .env                  # 环境变量
│   ├── nginx.conf            # Nginx配置
│   └── supervisor.conf       # 进程管理
├── logs/                      # 日志文件
│   ├── app.log               # 应用日志
│   ├── task.log              # 任务日志
│   └── error.log             # 错误日志
└── scripts/                   # 部署脚本
    ├── deploy.sh             # 部署脚本
    ├── backup.sh             # 备份脚本
    └── monitor.sh            # 监控脚本
```

#### 3.5.3 监控与运维

**监控指标**:
```yaml
系统监控:
  - CPU使用率: 阈值80%
  - 内存使用率: 阈值85%
  - 磁盘使用率: 阈值90%
  - 网络带宽: 实时监控

服务监控:
  - API响应时间: P95 < 500ms
  - 任务队列长度: 阈值100
  - 数据库连接数: 阈值50
  - Redis内存使用: 阈值80%

业务监控:
  - 任务成功率: 目标>95%
  - 用户活跃度: 日活用户
  - 内容生成量: 每日生成量
  - 成本控制: 实际vs预估
```

**告警规则**:
```python
# 告警配置示例
alerts:
  - name: "高CPU使用率"
    condition: "cpu_usage > 80% for 5m"
    severity: "warning"
    action: "发送邮件通知，自动扩容"
  
  - name: "任务队列积压"
    condition: "task_queue_length > 100"
    severity: "critical"
    action: "增加worker数量，通知管理员"
  
  - name: "API错误率升高"
    condition: "api_error_rate > 5% for 10m"
    severity: "warning"
    action: "重启服务，检查日志"
```

## 4. 开发实施计划

### 4.1 第一阶段：基础框架整合（1-2周）

**目标**: 建立统一的基础框架
```
第1周：
1. 环境准备和依赖安装
2. 数据库结构统一设计
3. 用户认证系统整合
4. 基础API框架搭建

第2周：
1. 任务队列系统实现
2. 文件存储结构设计
3. 基础监控系统部署
4. 开发环境测试
```

**交付物**:
- 统一数据库 schema
- 基础API接口
- 用户认证系统
- 开发环境部署文档

### 4.2 第二阶段：核心功能开发（2-3周）

**目标**: 实现核心业务功能
```
第3周：
1. 小说生成模块集成
   - TrendAgent集成
   - StyleAgent集成
   - PlannerAgent集成

第4周：
1. 小说生成模块集成（续）
   - WriterAgent集成
   - PolishAgent集成
   - AuditorAgent集成
   - ReviserAgent集成

第5周：
1. 视频生成模块集成
   - 模式选择系统
   - TTS集成
   - 视频处理集成
```

**交付物**:
- 完整的小说生成功能
- 基础视频生成功能
- 统一任务调度系统
- 用户界面原型

### 4.3 第三阶段：高级功能开发（2-3周）

**目标**: 完善高级功能和优化
```
第6周：
1. 成本测算系统开发
2. 发布管理系统开发
3. 内容抓取功能集成

第7周：
1. 多模式视频生成完善
2. 性能优化和测试
3. 用户体验优化

第8周：
1. 监控和运维系统完善
2. 安全加固
3. 文档编写
```

**交付物**:
- 完整的成本测算系统
- 多平台发布功能
- 性能优化报告
- 用户手册和API文档

### 4.4 第四阶段：测试和部署（1-2周）

**目标**: 系统测试和生产部署
```
第9周：
1. 单元测试和集成测试
2. 性能测试和压力测试
3. 安全测试

第10周：
1. 生产环境部署
2. 监控系统上线
3. 用户培训和支持
```

**交付物**:
- 测试报告
- 生产环境部署
- 运维手册
- 用户培训材料

## 5. 风险评估与应对

### 5.1 技术风险

**风险1: 服务器性能不足**
- **可能性**: 高
- **影响**: 系统响应慢，任务处理延迟
- **应对**:
  1. 实施串行任务处理策略
  2. 优化资源使用算法
  3. 准备服务器升级方案
  4. 实施负载监控和预警

**风险2: AI API成本超预期**
- **可能性**: 中
- **影响**: 运营成本增加，可能亏损
- **应对**:
  1. 实施精确的成本测算
  2. 设置使用限额和预警
  3. 优化AI调用策略
  4. 准备备用AI服务商

**风险3: 视频处理质量不稳定**
- **可能性**: 中
- **影响**: 用户体验差，投诉增加
- **应对**:
  1. 实施多级质量检查
  2. 提供预览和调整功能
  3. 建立用户反馈机制
  4. 持续优化处理算法

### 5.2 业务风险

**风险1: 用户接受度低**
- **可能性**: 中
- **影响**: 用户增长缓慢，收入不足
- **应对**:
  1. 提供免费试用和体验
  2. 收集用户反馈快速迭代
  3. 实施用户教育和培训
  4. 建立用户社区和激励机制

**风险2: 内容合规问题**
- **可能性**: 低
- **影响**: 法律风险，平台封禁
- **应对**:
  1. 实施严格的内容审核
  2. 建立敏感词过滤系统
  3. 提供用户责任声明
  4. 准备应急处理预案

**风险3: 竞争加剧**
- **可能性**: 高
- **影响**: 市场份额下降，价格压力
- **应对**:
  1. 持续技术创新和优化
  2. 建立差异化竞争优势
  3. 提供优质客户服务
  4. 探索新的应用场景

### 5.3 运营风险

**风险1: 系统稳定性问题**
- **可能性**: 中
- **影响**: 服务中断，用户流失
- **应对**:
  1. 实施完善的监控系统
  2. 建立快速响应机制
  3. 准备备份和恢复方案
  4. 定期进行压力测试

**风险2: 数据安全风险**
- **可能性**: 低
- **影响**: 数据泄露，信誉损失
- **应对**:
  1. 实施严格的安全措施
  2. 定期安全审计和测试
  3. 数据加密和备份
  4. 员工安全培训

## 6. 成功指标

### 6.1 技术指标

**系统性能**:
- API平均响应时间: <500ms
- 任务处理成功率: >95%
- 系统可用性: >99.5%
- 并发用户支持: >100

**资源使用**:
- CPU平均使用率: <70%
- 内存平均使用率: <75%
- 磁盘空间使用: <80%
- 网络带宽使用: <60%

### 6.2 业务指标

**用户增长**:
- 月活跃用户: >1000
- 用户留存率: >40%
- 付费转化率: >5%
- 用户满意度: >4.0/5.0

**内容生产**:
- 每月生成小说: >100部
- 每月生成视频: >500个
- 内容质量评分: >4.0/5.0
- 用户生成内容占比: >30%

**经济效益**:
- 月收入: >¥10,000
- 成本收入比: <70%
- 用户平均收入: >¥10
- 投资回报率: >150%

### 6.3 创新指标

**技术创新**:
- 专利/软著申请: >2项
- 技术论文/分享: >3次
- 开源贡献: 积极维护

**行业影响**:
- 媒体报道: >5次
- 行业奖项: >1项
- 合作伙伴: >3家
- 用户案例: >10个

## 7. 总结

### 7.1 项目价值

**对用户的价值**:
1. **创作效率提升**: 从创意到成品的完整自动化流程
2. **成本透明可控**: 清晰的成本测算和优化建议
3. **多格式输出**: 一次创作，多种形式发布
4. **质量保证**: AI辅助的质量控制和优化

**对开发者的价值**:
1. **技术积累**: 深度整合AI、视频处理、内容生成技术
2. **市场机会**: 切入快速增长的AI内容创作市场
3. **可扩展性**: 模块化设计支持快速迭代和扩展
4. **数据资产**: 积累用户数据和内容资产

**对行业的价值**:
1. **技术创新**: 推动AI在内容创作领域的应用
2. **效率革命**: 改变传统内容创作模式
3. **生态建设**: 构建AI内容创作生态系统
4. **标准制定**: 探索行业最佳实践和标准

### 7.2 实施建议

**短期重点**:
1. 快速完成基础框架整合
2. 确保核心功能的稳定性
3. 收集早期用户反馈
4. 优化用户体验

**中期规划**:
1. 扩展内容类型和生成模式
2. 深化AI能力应用
3. 建立合作伙伴生态
4. 探索商业化模式

**长期愿景**:
1. 成为AI内容创作领域的领导者
2. 构建完整的内容创作生态系统
3. 推动行业技术标准和规范
4. 探索AI创作的新可能性

### 7.3 下一步行动

**立即行动**:
1. 评审本需求文档，确认需求范围
2. 制定详细的技术实施方案
3. 分配开发资源和时间计划
4. 开始第一阶段开发工作

**后续计划**:
1. 每周进度汇报和评审
2. 每月功能发布和用户测试
3. 每季度战略评估和调整
4. 持续优化和改进

---

## 附录

### A. 术语表

| 术语 | 解释 |
|------|------|
| AI Novel Agent | AI小说生成系统，包含7个Agent流水线 |
| Media Agent | 资讯转视频系统，支持多种视频生成模式 |
| TrendAgent | 趋势分析Agent，分析热门题材和趋势 |
| StyleAgent | 风格解析Agent，提取和量化写作风格 |
| PlannerAgent | 策划Agent，生成故事大纲和章节规划 |
| WriterAgent | 写作Agent，生成章节正文 |
| PolishAgent | 润色Agent，优化语言和逻辑 |
| AuditorAgent | 审核Agent，质量评分和问题检测 |
| ReviserAgent | 修订Agent，基于审核结果优化内容 |
| TTS | 文本转语音，将文字转换为语音 |
| VideoRetalk | 视频口型替换，同步口型和语音 |
| FFmpeg | 开源视频处理工具 |
| DeepSeek | AI模型提供商，提供Chat模型API |

### B. 参考文档

1. **AI Novel Agent 需求文档**: `E:\work\ai-novel-agent\docs\requirements\functional_performance_requirements_fixed.md`
2. **Media Agent 需求文档**: `E:\work\media-agent\docs\Media-Agent-最终版需求说明书.md`
3. **Media Agent 详细设计**: `E:\work\media-agent\docs\Media-Agent-详细设计文档.md`
4. **服务器信息**: MEMORY.md 中的服务器配置和API Key
5. **现有代码**: AI Novel Agent 和 Media Agent 的源代码

### C. 版本历史

| 版本 | 日期 | 修改内容 | 修改人 |
|------|------|----------|--------|
| 1.0 | 2026-03-31 | 初始版本，完成详细需求文档 | AI Novel Agent Assistant |

---

**文档状态**: ✅ 已完成详细需求设计  
**下一步**: 技术方案评审和开发实施
