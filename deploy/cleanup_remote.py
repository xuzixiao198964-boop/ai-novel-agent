# -*- coding: utf-8 -*-
import paramiko

HOST = "104.244.90.202"
PORT = 22
USER = "root"
PASSWORD = "C66ffUMycDn2"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    last_err = None
    for _ in range(3):
        try:
            c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=60)
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

