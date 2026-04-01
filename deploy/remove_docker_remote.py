# -*- coding: utf-8 -*-
"""
按用户要求：删除服务器上的容器相关资源以释放空间。
会执行：
- docker compose down（若存在）
- docker stop/rm 所有容器
- docker system prune -a --volumes
- 可选删除 /opt/ai-novel-agent 中的 docker 文件（不删代码目录）
"""

import sys
from pathlib import Path

import paramiko

_DEPLOY = Path(__file__).resolve().parent
if str(_DEPLOY) not in sys.path:
    sys.path.insert(0, str(_DEPLOY))
from ssh_env import require_ssh_password, ssh_host, ssh_port, ssh_user


def run(c: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + err).strip()


def main() -> None:
    host, port, user, password = ssh_host(), ssh_port(), ssh_user(), require_ssh_password()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, port=port, username=user, password=password, timeout=60)

    cmds = [
        "cd /opt/ai-novel-agent 2>/dev/null && (docker compose down -v || docker-compose down -v || true) || true",
        "docker ps -aq | xargs -r docker stop || true",
        "docker ps -aq | xargs -r docker rm -f || true",
        "docker system prune -a --volumes -f || true",
        # 清理可能残留的 compose 网络
        "docker network prune -f || true",
        # 删除项目目录下容器相关文件（按要求释放空间）
        "rm -f /opt/ai-novel-agent/Dockerfile /opt/ai-novel-agent/docker-compose.yml 2>/dev/null || true",
        "df -h || true",
        "docker system df || true",
    ]
    for cmd in cmds:
        print("\n$", cmd)
        print(run(c, cmd))

    c.close()


if __name__ == "__main__":
    main()

