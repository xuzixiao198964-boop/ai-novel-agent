# 测试说明（AI 小说生成 Agent 系统）

## 后端 API（pytest）

| 文件 | 覆盖范围 |
|------|----------|
| `tests/test_health_and_static.py` | `/api/health`、根路径 HTML、`/app.js`、`/novel/index.html` |
| `tests/test_tasks_api.py` | 任务 CRUD、`/api/config`、`/api/run-mode`、自动连续生成、停止/暂停 409、`start`（mock 流水线）、管理员清空任务与 `WEB_PASSWORD` |
| `tests/test_bookshelf_api.py` | `/api/bookshelf/login`、书架列表需 Bearer |
| `tests/test_novel_platform_api.py` | `/novel-api/categories`、`/novel-api/novels`、搜索、注册/登录/`/me`、404 |
| `tests/test_memory_and_outline.py` | 记忆库列表、无大纲 404、无成书 404 |

**约定**：`conftest.py` 将 `data_dir` / `memory_dir` 指到临时目录，并清空书架与小说站内存 token。

**不覆盖**（需 E2E 或手工）：真实 Agent 流水线长跑、`POST /novel-api/publish/{task_id}` 依赖磁盘成书。

---

## 前端（静态契约）

目录：`tests/frontend/`

1. **`run_static_checks.mjs`**（零依赖，Node 18+）：  
   `node tests/frontend/run_static_checks.mjs`  
   校验 `index.html` 关键 `id`、`app.js` 的 `/api` 前缀、`novel/app.js` 的 `/novel-api`。

2. **Vitest**（`npm install` 后）：`npm test`  
   与上逻辑类似，便于本地 watch。

**说明**：此为**契约/回归**测试，非浏览器 E2E。若需 Playwright，可另行增加 `e2e/`。

---

## 用例清单（与实现对齐）

| 编号 | 类型 | 场景 |
|------|------|------|
| TC-B01 | API | `GET /api/health` → `{"status":"ok"}` |
| TC-B02 | API | 创建任务 → `GET /api/tasks/{id}` 元数据一致 |
| TC-B03 | API | 空闲时 `POST /api/tasks/stop` → 409 |
| TC-B04 | API | `start_pipeline` mock 后 `POST .../start` → 200 |
| TC-B05 | API | 配置 `WEB_PASSWORD` 时清空任务需 Bearer |
| TC-B06 | API | 书架管理员登录 → `GET /api/bookshelf` |
| TC-N01 | API | `/novel-api` 分类与列表、注册登录 |
| TC-F01 | 静态 | 首页含 `taskList`、`btnCreateTask` 等 |
| TC-F02 | 静态 | `app.js` 中 `API = "/api"` |

---

*接口变更时请同步更新测试与本文档。*
