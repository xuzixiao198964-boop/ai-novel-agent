# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import paramiko

_DEPLOY = Path(__file__).resolve().parent
if str(_DEPLOY) not in sys.path:
    sys.path.insert(0, str(_DEPLOY))
from ssh_env import require_ssh_password, ssh_host, ssh_port, ssh_user


def main() -> None:
    host, port, user, password = ssh_host(), ssh_port(), ssh_user(), require_ssh_password()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    last_err = None
    for _ in range(3):
        try:
            c.connect(host, port=port, username=user, password=password, timeout=60)
            last_err = None
            break
        except Exception as e:
            last_err = e
            import time
            time.sleep(5)
    if last_err:
        raise last_err

    # 请求停止流水线（如果正在跑）
    c.exec_command("curl -s -X POST http://127.0.0.1:9000/api/tasks/stop || true")
    # 清空历史数据（容器内卷 /app/data 与 /app/memory）
    c.exec_command(
        "docker exec ai-novel-agent-app-1 sh -lc 'rm -rf /app/data/tasks /app/data/state/* /app/memory/* || true; mkdir -p /app/data/state; : > /app/data/state/current_task.txt' || true"
    )
    # 重启服务（刷新容器文件系统）
    c.exec_command("cd /opt/ai-novel-agent && docker compose restart || true")

    stdin, stdout, stderr = c.exec_command("curl -s http://127.0.0.1:9000/api/tasks/current || true")
    print(stdout.read().decode("utf-8", errors="replace").strip())
    c.close()


if __name__ == "__main__":
    main()

