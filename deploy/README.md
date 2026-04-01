# 部署脚本说明

所有 SSH 与 LLM 密钥**禁止**写入仓库，运行前请在终端设置环境变量。

## 必需变量

| 变量 | 说明 |
|------|------|
| `DEPLOY_SSH_PASSWORD` | 服务器 SSH 密码 |
| `LLM_API_KEY` | DeepSeek（或兼容 OpenAI）API Key，用于写入远端 `.env` |

## 可选变量

| 变量 | 默认值 |
|------|--------|
| `DEPLOY_SSH_HOST` | `104.244.90.202` |
| `DEPLOY_SSH_PORT` | `22` |
| `DEPLOY_SSH_USER` | `root` |

## Windows（PowerShell）示例

```powershell
$env:DEPLOY_SSH_PASSWORD = "你的密码"
$env:LLM_API_KEY = "sk-..."
python deploy/deploy_systemd_ssh.py
```

## Linux / macOS

```bash
export DEPLOY_SSH_PASSWORD='你的密码'
export LLM_API_KEY='sk-...'
python deploy/deploy_systemd_ssh.py
```

## 脚本一览

- `deploy_systemd_ssh.py`：裸机 + systemd + venv（推荐，与当前架构一致）
- `deploy_ssh.py`：历史 Docker Compose 部署路径（若仍使用容器）
- `run_two_novels_paramiko.py` / `run_three_novels_paramiko.py`：远端 API 回归
- `verify_server_paramiko.py`：健康检查与短任务验证
- `cleanup_remote.py` / `remove_docker_remote.py`：远端清理（慎用）

实现见 `ssh_env.py`。
