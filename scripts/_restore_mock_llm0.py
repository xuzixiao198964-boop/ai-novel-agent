# -*- coding: utf-8 -*-
"""一次性：验证脚本 --ssh 会写 MOCK_LLM=1，跑完后可执行本脚本恢复 MOCK_LLM=0。"""
import paramiko

HOST = "104.244.90.202"
PASSWORD = "v9wSxMxg92dp"  # 与 deploy 一致；生产请改环境变量

def main() -> None:
    import os
    pw = os.environ.get("DEPLOY_SSH_PASSWORD", "").strip() or os.environ.get("SSH_PASSWORD", "").strip() or PASSWORD
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, "root", pw, timeout=60)
    try:
        cmds = [
            "sed -i '/^MOCK_LLM=/d' /opt/ai-novel-agent/.env",
            "echo MOCK_LLM=0 >> /opt/ai-novel-agent/.env",
            "systemctl restart ai-novel-agent",
            "sleep 4",
            "curl -s http://127.0.0.1:9000/api/health",
        ]
        for x in cmds:
            _, stdout, stderr = c.exec_command(x, timeout=120)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            if x.startswith("curl"):
                print(out.strip() or "(no body)", flush=True)
            if err.strip():
                print(err, flush=True)
    finally:
        c.close()
    print("DONE: MOCK_LLM=0, service restarted.", flush=True)

if __name__ == "__main__":
    main()
