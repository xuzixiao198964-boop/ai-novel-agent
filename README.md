# AI小说生成 Agent 系统

多 Agent 协同的 AI 自动小说生成系统，支持「热门分析→风格解析→创作→质检→修订」全流程自动化，并通过网页端实时展示各 Agent 进度与日志。

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

## 服务器部署（Ubuntu）

已配置通过 SSH 自动部署（无需手动输入密码）：

```bash
pip install paramiko
python deploy/deploy_ssh.py
```

脚本会：连接服务器、上传代码、构建并启动 Docker 容器。部署完成后访问 http://104.244.90.202:9000

## 项目结构

- `backend/`：FastAPI 后端与 7 个 Agent（Trend / Style / Planner / Writer / Polish / Auditor / Reviser）
- `backend/static/`：网页端（总进度、Agent 详情、日志、文件管理、任务管理）
- `deploy/`：SSH 部署脚本与验证脚本
- `Dockerfile`、`docker-compose.yml`：容器化部署

## 使用流程

1. 打开网页 → 创建任务（输入任务名称后点「创建任务」）
2. 在任务列表中点击「选择」选中该任务，再点「启动」或列表中的「启动」
3. 总进度面板会显示 7 个 Agent 的状态（就绪/运行中/完成/失败）
4. 点击某个 Agent 卡片可查看该 Agent 详情与日志
5. 在「文件管理」中可下载风格报告、策划案、章节正文、审计报告、定稿等

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
