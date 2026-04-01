# MEMORY.md - 长期记忆库

## 项目概况

### AI小说生成Agent系统
- **项目路径**: `e:\work\ai-novel-agent`
- **类型**: 多Agent协同的AI自动小说生成系统
- **技术栈**: FastAPI + Python + DeepSeek LLM
- **服务器**: 104.244.90.202:9000

### 7个核心Agent（执行顺序）
1. **TrendAgent** - 热门趋势分析，选择题材，生成章节/字数建议
2. **StyleAgent** - 风格解析，生成风格参数
3. **PlannerAgent** - 策划案 → 故事总纲 → 章节大纲（含多轮审核）
4. **WriterAgent** - 逐章正文创作（含前两章引子上下文）
5. **PolishAgent** - 章节润色
6. **AuditorAgent** - 质量审核打分，每 3 章一次区间审计
7. **ReviserAgent** - 根据审核意见修订

## 服务器信息
- **IP**: 104.244.90.202
- **SSH**: 端口 22, 用户 root, 密码 v9wSxMxg92dp
- **应用端口**: 9000
- **部署路径**: /opt/ai-novel-agent/backend
- **DeepSeek API Key**: sk-9fcc8f6d0ce94fdbbe66b152b7d3e485
- **LLM Model**: deepseek-chat
- **Systemd服务**: ai-novel-agent

## 关键代码文件
| 文件 | 职责 |
|------|------|
| `app/agents/writer.py` | WriterAgent，含前两章引子、上章衔接 |
| `app/agents/planner_agent.py` | PlannerAgent，策划案+总纲+大纲生成与审核 |
| `app/agents/trend_agent.py` | TrendAgent，趋势分析+动态章节数 |
| `app/core/pipeline.py` | 管线编排，测试模式逻辑 |
| `app/core/state.py` | 状态管理，run_mode/test_chapters |
| `app/api/routes.py` | API路由 |
| `static/app.js` / `static/index.html` | 前端 |

## 已完成的功能改进

### 内容质量
- WriterAgent 引用上一章后半段原文 + 故事总纲对应段落
- **前两章引子**：从第 3 章起，每次写作都传入第 1、2 章全文作为上下文
- 角色名严格按策划案人设矩阵，不自行编造

### 趋势与多样性
- 18 种题材类型（含儿童/校园、科幻/未来等）
- 每种题材有独立的章节范围和字数范围（如言情 200-500 章，儿童 30-80 章）
- 主题去重（3 次内不重复）
- 手动选择主题 API

### 名字多样化
- PlannerAgent prompt 要求混用不同姓氏、字数、风格
- 跨任务名字去重

### Pipeline 稳定性
- `_start_lock` 防止并发启动
- 测试模式下 PlannerAgent 章节数=test_chapters
- 大纲审核强制放行阈值=2，禁止回退

## 经验教训

### PlannerAgent 是瓶颈
- 大纲审核最耗时：每批 3 章，需 LLM 审核质量
- 162 章 = 54 批，每批平均 2 轮审核 = ~108 轮 LLM 调用
- BATCH_FORCE_PASS_LIMIT=2 + 无回退 = 最优平衡

### 测试模式陷阱
- 必须在 PlannerAgent 中覆盖 chapter_min/max 为 test_ch
- 趋势报告中的章节建议也要替换，否则 LLM 看到矛盾信息

### DeepSeek API
- 充值后可能更换 Key
- 遇到 401 先检查 Key 是否变更
- 遇到 402 是余额不足

## 测试进度

### 已完成
- 6 章测试：通过
- 18 章测试：通过
- 54 章测试（任务 `0b6a1da1`）：通过，约 5 小时完成

### 进行中
- 162 章测试（任务 `48fe4606`）：PlannerAgent 大纲阶段 ~69%

### 目标
- 从 6 章开始，每次 3 倍递增（6→18→54→162），全部通过即完成

## 更新记录
- **2026-03-30**: 54章测试通过；前两章引子功能；大纲审核优化；API Key更换；162章测试启动
- **2026-03-29**: 首次部署测试；修复并发、趋势、名字等问题
- **2026-03-28**: 项目首次接触，创建记忆系统
