# -*- coding: utf-8 -*-
"""
无容器部署：把 backend 代码上传到服务器，创建 venv 安装依赖，写入 .env，创建 systemd 服务并启动。
用法：python deploy/deploy_systemd_ssh.py
"""

import os
import time
from pathlib import Path

import paramiko

HOST = "104.244.90.202"
PORT = 22
USER = "root"
PASSWORD = "v9wSxMxg92dp"

REMOTE_DIR = "/opt/ai-novel-agent"
REMOTE_BACKEND = f"{REMOTE_DIR}/backend"
VENV_DIR = f"{REMOTE_DIR}/venv"

# DeepSeek（OpenAI 兼容）
LLM_API_BASE = "https://api.deepseek.com"
LLM_API_KEY = ""  # 允许从本机环境变量读取
LLM_MODEL = "deepseek-chat"


def run_ssh(c: paramiko.SSHClient, cmd: str, check: bool = True) -> str:
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    if check and rc != 0:
        raise RuntimeError(f"Exit {rc}\n{err or out}")
    return (out + err).strip()


def open_ssh() -> paramiko.SSHClient:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=60)
    return c


def sftp_put_dir(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    for fp in local.rglob("*"):
        if fp.is_dir():
            continue
        if "__pycache__" in fp.parts or fp.suffix == ".pyc":
            continue
        if "data" in fp.parts or "memory" in fp.parts:
            continue
        rel = fp.relative_to(local).as_posix()
        rp = f"{remote}/{rel}".replace("\\", "/")
        # mkdir -p 父目录（只创建 backend 下的路径）
        dir_parts = rel.split("/")[:-1]
        if dir_parts:
            parent = remote
            for seg in dir_parts:
                parent = f"{parent}/{seg}".replace("\\", "/")
                try:
                    sftp.stat(parent)
                except FileNotFoundError:
                    try:
                        sftp.mkdir(parent)
                    except Exception:
                        pass
        sftp.put(str(fp), rp)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    backend = root / "backend"
    req = backend / "requirements.txt"
    if not req.exists():
        raise RuntimeError("backend/requirements.txt 不存在")

    api_key = os.environ.get("LLM_API_KEY", "").strip() or LLM_API_KEY
    if not api_key:
        raise RuntimeError("缺少 LLM_API_KEY：请在本机环境变量 LLM_API_KEY 提供")

    def _env_int(name: str, default: int) -> int:
        v = os.environ.get(name, "")
        v = str(v).strip()
        if not v:
            return default
        try:
            return int(v)
        except Exception:
            return default

    # 允许用较小章节数在服务器侧快速验证流程。
    # - DEPLOY_TOTAL_CHAPTERS：Planner 阶段固定总章数（>0 才生效）
    # - DEPLOY_MAX_CHAPTERS_TO_WRITE：Writer 阶段最多写到前 N 章（>0 才生效）
    test_total_chapters = _env_int("DEPLOY_TOTAL_CHAPTERS", 0)
    test_max_chapters_to_write = _env_int("DEPLOY_MAX_CHAPTERS_TO_WRITE", 0)
    test_chapter_range_min = _env_int("DEPLOY_CHAPTER_RANGE_MIN", 100)
    test_chapter_range_max = _env_int("DEPLOY_CHAPTER_RANGE_MAX", 500)

    deploy_mock_llm_raw = str(os.environ.get("DEPLOY_MOCK_LLM", "")).strip().lower()
    deploy_mock_llm = 1 if deploy_mock_llm_raw in ("1", "true", "yes", "on") else 0

    c = open_ssh()
    try:
        # 删除服务器上容器相关资源以释放空间（忽略失败）
        for cmd in [
            "cd /opt/ai-novel-agent 2>/dev/null && (docker compose down -v || docker-compose down -v || true) || true",
            "docker ps -aq | xargs -r docker stop 2>/dev/null || true",
            "docker ps -aq | xargs -r docker rm -f 2>/dev/null || true",
            "docker system prune -a --volumes -f 2>/dev/null || true",
            "docker network prune -f 2>/dev/null || true",
            "rm -f /opt/ai-novel-agent/Dockerfile /opt/ai-novel-agent/docker-compose.yml 2>/dev/null || true",
        ]:
            run_ssh(c, cmd, check=False)

        run_ssh(c, f"mkdir -p {REMOTE_DIR}")

        # 上传 backend
        transport = c.get_transport()
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            # 先清理旧 backend（保留 data/memory）
            run_ssh(c, f"rm -rf {REMOTE_BACKEND} && mkdir -p {REMOTE_BACKEND}")
            sftp_put_dir(sftp, backend, REMOTE_BACKEND)
        finally:
            try:
                sftp.close()
            except Exception:
                pass

        env_lines = [
            "PORT=9000",
            f"LLM_API_BASE={LLM_API_BASE}",
            f"LLM_API_KEY={api_key}",
            f"LLM_MODEL={LLM_MODEL}",
            f"MOCK_LLM={deploy_mock_llm}",
            f"TOTAL_CHAPTERS={test_total_chapters}",
            f"MAX_CHAPTERS_TO_WRITE={test_max_chapters_to_write}",
            f"CHAPTER_RANGE_MIN={test_chapter_range_min}",
            f"CHAPTER_RANGE_MAX={test_chapter_range_max}",
        ]
        # 验证流水线/递增时可设 DEPLOY_FAST_VERIFY=1，缩短 Agent 间隔
        if str(os.environ.get("DEPLOY_FAST_VERIFY", "")).strip().lower() in ("1", "true", "yes", "on"):
            env_lines.extend(["AGENT_INTERVAL_SECONDS=0", "STEP_INTERVAL_SECONDS=0"])
        env_content = "\n".join(env_lines + ["", ""])
        run_ssh(c, f"cat > {REMOTE_DIR}/.env <<'EOF'\n{env_content}\nEOF")

        # 安装依赖
        run_ssh(
            c,
            "apt-get update -y && apt-get install -y python3-venv python3-pip",
            check=False,
        )
        run_ssh(c, f"python3 -m venv {VENV_DIR} || true")
        run_ssh(c, f"{VENV_DIR}/bin/pip install -U pip wheel setuptools")
        run_ssh(c, f"{VENV_DIR}/bin/pip install -r {REMOTE_BACKEND}/requirements.txt")

        # systemd service
        service = """[Unit]
Description=ai-novel-agent (FastAPI)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/ai-novel-agent/backend
EnvironmentFile=/opt/ai-novel-agent/.env
ExecStart=/opt/ai-novel-agent/venv/bin/python -m app.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
        run_ssh(c, "cat > /etc/systemd/system/ai-novel-agent.service <<'EOF'\n" + service + "\nEOF")
        run_ssh(c, "systemctl daemon-reload")
        run_ssh(c, "systemctl enable ai-novel-agent.service")
        # 避免旧进程占用 9000（例如手工 uvicorn 未随 systemd 退出）
        run_ssh(c, "systemctl stop ai-novel-agent.service 2>/dev/null || true", check=False)
        run_ssh(c, "fuser -k 9000/tcp 2>/dev/null || true; sleep 1", check=False)
        run_ssh(c, "systemctl start ai-novel-agent.service")
        time.sleep(2)
        print(run_ssh(c, "systemctl --no-pager status ai-novel-agent.service | head -n 20", check=False))
        print(run_ssh(c, "curl -s http://127.0.0.1:9000/api/health || true", check=False))
        print("DONE: http://%s:9000" % HOST)
    finally:
        c.close()


if __name__ == "__main__":
    main()

