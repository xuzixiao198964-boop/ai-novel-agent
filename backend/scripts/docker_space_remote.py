# -*- coding: utf-8 -*-
"""
远程查看 Docker / 磁盘占用情况（用于清理释放空间）。
默认使用用户提供的 SSH 密码连接服务器。
"""

import os
import paramiko

HOST = "104.244.90.202"
PORT = 22
USER = "root"
DEFAULT_SSH_PASS = "C66ffUMycDn2"


def run_cmd(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + err).strip()


def main() -> None:
    ssh_pass = os.environ.get("SSH_PASS", "").strip() or DEFAULT_SSH_PASS
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=ssh_pass, timeout=30)

    cmds = [
        "df -h || true",
        "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' || true",
        "docker system df || true",
        "docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}' || true",
        "docker volume ls || true",
        "docker network ls || true",
        "du -sh /opt/ai-novel-agent 2>/dev/null || true",
    ]
    for c in cmds:
        print("\n###", c)
        print(run_cmd(ssh, c))

    ssh.close()


if __name__ == "__main__":
    main()

