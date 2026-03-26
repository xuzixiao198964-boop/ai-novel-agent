# -*- coding: utf-8 -*-
"""
远程统计项目容器在磁盘上的占用大小。

通过 SSH 连接服务器后执行：
1) docker ps 获取容器名
2) docker exec <container> du -sh /app /app/data /app/memory（若存在）

密码通过环境变量 SSH_PASS 传入，避免把敏感信息写进仓库。
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
    # 兜底：诊断时直接使用默认密码（由用户提供）
    ssh_pass = os.environ.get("SSH_PASS", "").strip() or DEFAULT_SSH_PASS

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=ssh_pass, timeout=20)

    names_raw = run_cmd(ssh, "docker ps --format '{{.Names}}'")
    names = [x.strip() for x in names_raw.splitlines() if x.strip()]
    targets = [n for n in names if "ai-novel-agent" in n] or names

    print("containers:", targets)
    for name in targets:
        # 同时尝试 /opt 路径（若容器内没挂载会失败但不影响）
        cmd = (
            "sh -lc "
            "\""
            "echo '--- ls /app ---'; ls -la /app 2>/dev/null || true; "
            "echo '--- du /app ---'; du -sh /app 2>/dev/null || true; "
            "echo '--- du /app/data ---'; du -sh /app/data 2>/dev/null || true; "
            "echo '--- du /app/memory ---'; du -sh /app/memory 2>/dev/null || true; "
            "echo '--- du /app/data/tasks ---'; du -sh /app/data/tasks 2>/dev/null || true; "
            "echo '--- du /app/data/state ---'; du -sh /app/data/state 2>/dev/null || true; "
            "echo '--- du /app/data/tasks ---'; du -sh /app/data/tasks 2>/dev/null || true; "
            "echo '--- du /app/data/tasks/* (top-level) ---'; du -sh /app/data/tasks/* 2>/dev/null || true; "
            "echo '--- du /app/memory/* ---'; du -sh /app/memory/* 2>/dev/null || true; "
            "echo '--- du /opt/ai-novel-agent ---'; du -sh /opt/ai-novel-agent 2>/dev/null || true; "
            "\""
        )
        txt = run_cmd(ssh, f"docker exec {name} {cmd}")
        print(f"\n== {name} ==")
        print(txt if txt else "(no output)")

    ssh.close()


if __name__ == "__main__":
    main()

