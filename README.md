# AI Novel Media Agent 智能内容创作平台

## 🚀 平台概述

**AI Novel Media Agent** 是一个整合了 AI 小说自动生成与视频制作的智能内容创作平台。平台提供一站式"AI 内容创作 → 视频制作 → 多平台分发"的完整解决方案。

### ✨ 核心功能

1. **AI小说生成** - 7个Agent协同流水线，支持微/短/中/长篇小说
2. **AI视频制作** - 从小说、资讯生成短视频，支持多种画面模式
3. **商业化运营** - 套餐付费系统，支持支付宝/微信支付
4. **多平台分发** - 自动发布到抖音、小红书、番茄小说等平台
5. **开放接入** - 提供API与OpenClaw协议对接
6. **多端入口** - App、微信/抖音小程序、Web端全平台支持

### 🏗️ 系统架构

- **官方网站** (80端口) - 产品宣传、API文档、下载中心
- **后台管理系统** - 用户管理、作品审核、系统监控
- **用户Web应用** (9000端口) - 任务创建、进度查看、作品管理
- **移动端App** - iOS/Android原生应用，微信/抖音小程序

## 访问地址（已部署）

**http://104.244.90.202:9000**

- 在浏览器打开上述地址即可使用网页端。
- 功能：任务管理（创建/选择/启动/停止）、总进度与各 Agent 详情、日志查看、产出文件下载。

## 本地开发

```bash
cd backend
pip install -r requirements.txt
set PYTHONPATH=%CD%   # Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:9000

### 大模型配置（含 OpenClaw）

- 默认走 OpenAI 兼容接口，保留现有网页功能不变（任务、进度、日志、文件、阅读站都继续可用）。
- 环境变量新增 `LLM_PROVIDER`：
  - `openai_compatible`（默认）：优先请求 `/v1/chat/completions`
  - `openclaw`：优先 `/v1/chat/completions`，失败自动回退到 `/chat/completions`
- OpenClaw 示例：

```bash
cd backend
set LLM_PROVIDER=openclaw
set LLM_API_BASE=http://127.0.0.1:8001
set LLM_API_KEY=
set LLM_MODEL=openclaw-chat
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

### 小说阅读站（同机可另开端口）

- 与主站同端口时：浏览器打开 **`/novel/index.html`**（或首页「小说平台」链接）；API 前缀 **`/novel-api`**。
- 仅跑阅读站（默认 **8001** 端口）：

```bash
cd backend
set PYTHONPATH=%CD%
python novel_server.py
# 或: set NOVEL_PORT=8001 && python novel_server.py
```

- 将已完成任务的书稿发布到阅读站：`POST /novel-api/publish/{task_id}`（需任务含 `planner/outline.json` 与 `final/ch_XX.md`）。
- 测试模式成功后会按 **当前章数×3** 递增上限，直至达到 **`trend_analysis.json` 中的建议总章数**（与正式规模一致）；正式模式不写死 `total_chapters` 时由 **热门趋势分析** 给出建议章数。

## 🚀 快速部署

### 完整部署测试流程

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行完整部署测试流程
python deploy_and_test.py
```

### 手动部署到服务器

```bash
# 使用完整部署脚本
python deploy_full_system.py

# 或使用SSH部署
python deploy/ssh_env.py
```

### 服务器信息
- **地址**: 104.244.90.202:9000
- **SSH**: 端口22, 用户root, 密码v9wSxMxg92dp
- **部署路径**: /opt/ai-novel-agent/backend

## 🧪 测试验证

### 运行完整测试
```bash
python run_tests.py
```

### 测试覆盖率要求
- 单元测试覆盖率: 100%
- 集成测试覆盖率: 100%
- 系统测试覆盖率: 100%

### 测试策略
1. **单元测试** - 测试单个模块功能
2. **集成测试** - 测试模块间集成
3. **系统测试** - 测试完整工作流
4. **部署验证** - 验证部署后的系统功能

## 项目结构

- `backend/`：FastAPI 后端与 7 个 Agent（Trend / Style / Planner / Writer / Polish / Auditor / Reviser）
- `backend/static/`：网页端（总进度、Agent 详情、日志、文件管理、任务管理）
- `deploy/`：SSH 部署脚本与验证脚本
- `Dockerfile`、`docker-compose.yml`：容器化部署

## 📱 使用流程

### 1. 用户注册与登录
- 支持手机号/邮箱注册
- 支持微信/抖音OAuth登录
- 图形验证码保护

### 2. 套餐选择与充值
- **基础套餐** - 纯小说生成 (¥9.9/月)
- **进阶套餐** - 小说+视频生成 (¥29.9/月)
- **专业套餐** - 全功能+优先队列 (¥99.9/月)
- 支持支付宝/微信支付充值

### 3. 内容创作流程

#### 小说生成选项
```json
{
  "generation_type": "novel_only",
  "novel_options": {
    "length": "medium",  // micro, short, medium, long, random
    "genre": "male",     // children, male, female, random
    "subgenre": "fantasy" // 玄幻、军事、言情等
  }
}
```

#### 视频生成选项
```json
{
  "generation_type": "video_only",
  "video_options": {
    "source": "ai_novel",  // ai_novel, external_novel, news, random
    "mode": "text_to_video", // text_to_video, images_only, imported_media
    "background_music": true,
    "subtitles": true,
    "voice": true,
    "lip_sync": true
  }
}
```

### 4. 任务管理与监控
- **实时进度** - WebSocket实时更新进度
- **队列信息** - 显示排队位置和预估等待时间
- **时间预估** - 预估生成时间和剩余时间
- **详细日志** - 每个阶段的操作日志

### 5. 作品管理
- **小说分类** - 儿童/男频/女频三级分类
- **视频分类** - 小说类/资讯类分类
- **文件组织** - 按小说文件夹组织视频文件
- **作品下载** - 支持小说文本和视频文件下载

### 6. 多平台发布
- **抖音** - 自动发布短视频
- **小红书** - 自动发布图文内容
- **番茄小说** - 自动发布小说
- **起点** - 自动发布长篇小说

## 🔧 API接口

### 用户管理
- `POST /api/v1/user/register` - 用户注册
- `POST /api/v1/user/login` - 用户登录
- `GET /api/v1/user/me` - 获取用户信息

### 付费系统
- `GET /api/v1/payment/packages` - 获取套餐列表
- `POST /api/v1/payment/recharge` - 用户充值
- `GET /api/v1/payment/balance` - 查询余额
- `POST /api/v1/payment/calculate-cost` - 计算任务成本

### 任务管理
- `POST /api/v1/tasks/` - 创建任务
- `GET /api/v1/tasks/` - 获取任务列表
- `GET /api/v1/tasks/{task_id}` - 获取任务详情
- `GET /api/v1/tasks/queue/info` - 获取队列信息
- `WS /api/v1/tasks/ws/{client_id}` - WebSocket实时更新

## 📊 原型设计

查看完整原型设计：
```bash
# 打开原型设计网页
open docs/prototype/index.html
```

原型包含：
- 🌐 **产品官网** - 平台宣传、API文档、下载中心
- 💻 **用户端Web应用** - 任务创建、进度查看、作品管理
- ⚙️ **后台管理系统** - 用户管理、作品审核、系统配置
- 📱 **移动端App** - iOS/Android原生应用设计

## 测试（前后端）

- **后端（pytest）**：在 `backend/` 目录已安装主依赖后执行：
  ```bash
  pip install -r requirements-dev.txt
  pytest -v
  ```
  用例位于 `backend/tests/`，使用临时数据目录，不污染 `backend/data/`。详见 **[docs/TESTING.md](docs/TESTING.md)**。

- **前端（静态契约）**：
  - **无依赖**（推荐 CI）：`node tests/frontend/run_static_checks.mjs`
  - **Vitest**（需 Node）：`cd tests/frontend && npm install && npm test`

## 测试模式递增至目标章数（持续监听）

- 策略仍为：**成功跑通一本后，下一档测试章数 = min(当前档×3, 趋势建议上限)**，直至达到上限（README 上文「×3」说明）。
- 持续监听脚本（轮询 `/api/run-mode`，可选自动开「自动连续生成」并启动任务）：

```bash
python scripts/monitor_test_mode_to_target.py --base http://你的IP:9000 --target 200 --interval 45
# 从 6 章档重新计数可加 --reset
```

## 说明

- 当前 Agent 为演示逻辑（模拟耗时与产出）；接入真实大模型、爬虫、RAG 后即可用于正式生成。
- 长期记忆库（7 个真相文件）在任务目录下 `memory/` 中，可通过 API 查看与编辑。
- 可选：在 `.env` 或环境变量中设置 `WEB_PASSWORD` 启用网页端简单密码校验。
