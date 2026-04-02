# -*- coding: utf-8 -*-
"""
验证「测试模式」在整本书成功完成后：test_chapters 从 6 递增为 18（×3）。

步骤：
  1)（可选 SSH）在服务器 /opt/ai-novel-agent/.env 写入 MOCK_LLM=1 与间隔为 0，并 restart ai-novel-agent
  2) HTTP：停止当前流水线、测试模式 reset 为 6 章、关闭 auto_run（避免第二本抢跑）
  3) 创建任务并启动
  4) **前台**持续打印，直到控制台出现「★ test_chapters 变化: 6 → 18」且 test_chapters>=18、无运行任务

推荐顺序（满足「先在控制台监听到 6 章 ×3 切到 18 章」，再考虑后台）：
  A) **先前台跑通链路**（MOCK，约数十秒～数分钟，必出现 6→18）：
     set DEPLOY_SSH_PASSWORD=你的root密码
     python scripts/verify_increment_6_to_18.py --base http://YOUR_HOST:9000 --ssh --poll 5

  B) 确认 A 通过后，再用真实 DeepSeek **长时间**验证（勿加 --ssh；整本跑完才递增，仅当 A 已证明服务端逻辑无误）：
     python scripts/verify_increment_6_to_18.py --base http://YOUR_HOST:9000 --timeout 86400 --poll 20
     （可 nohup / 任务计划放后台，但应先完成 A，避免未监听到 6→18 就盲跑。）

用法简写：
  # 快速验证递增（SSH 写 MOCK_LLM=1、间隔 0）
  python scripts/verify_increment_6_to_18.py --base http://104.244.90.202:9000 --ssh
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _utf8_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def http_json(base: str, method: str, path: str, body: dict | None = None, timeout: float = 120.0):
    url = base.rstrip("/") + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"detail": raw}


def ssh_apply_mock_fast(host: str, password: str) -> None:
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, 22, "root", password, timeout=45)
    try:
        cmds = [
            "touch /opt/ai-novel-agent/.env",
            "sed -i '/^MOCK_LLM=/d;/^AGENT_INTERVAL_SECONDS=/d;/^STEP_INTERVAL_SECONDS=/d' /opt/ai-novel-agent/.env",
            "echo MOCK_LLM=1 >> /opt/ai-novel-agent/.env",
            "echo AGENT_INTERVAL_SECONDS=0 >> /opt/ai-novel-agent/.env",
            "echo STEP_INTERVAL_SECONDS=0 >> /opt/ai-novel-agent/.env",
            "systemctl restart ai-novel-agent",
            "sleep 4",
            "curl -s http://127.0.0.1:9000/api/health",
        ]
        for c in cmds:
            stdin, stdout, stderr = client.exec_command(c, timeout=120)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            if c.startswith("curl"):
                print(out, flush=True)
            if err.strip():
                print(err, flush=True)
        if "ok" not in out.lower() and '{"status"' not in out:
            raise RuntimeError(f"health check unclear: last_out={out!r}")
    finally:
        client.close()


def main() -> int:
    _utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:9000")
    ap.add_argument("--host", default="104.244.90.202", help="SSH 主机（--ssh 时用）")
    ap.add_argument("--ssh", action="store_true", help="SSH 写 MOCK_LLM=1 并重启服务")
    ap.add_argument("--poll", type=float, default=15.0, help="轮询秒数")
    ap.add_argument("--timeout", type=float, default=3600.0, help="最长等待秒数（默认 1h）")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    pw = os.environ.get("DEPLOY_SSH_PASSWORD", "").strip() or os.environ.get("SSH_PASSWORD", "").strip()
    if args.ssh and not pw:
        pw = "v9wSxMxg92dp"  # 与 deploy_systemd_ssh 一致；生产请用环境变量覆盖

    if args.ssh:
        print(">>> [SSH] 写入 MOCK_LLM=1、间隔=0 并重启 ai-novel-agent …", flush=True)
        ssh_apply_mock_fast(args.host, pw)

    def log(msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

    # 停跑、关自动、测试档 6；并等待无「僵尸运行中」状态
    for _ in range(30):
        http_json(base, "POST", "/api/tasks/stop", {})
        st, cur = http_json(base, "GET", "/api/tasks/current")
        if st == 200 and not cur.get("running"):
            break
        log("等待上一任务释放…")
        time.sleep(2)
    else:
        log("警告: 仍显示运行中，将依赖本次部署的「启动清空 current_task」修复。")

    http_json(base, "POST", "/api/tasks/auto-run", {"auto_run": False})
    st, rm = http_json(base, "POST", "/api/run-mode", {"mode": "test", "test_chapters": 6})
    if st != 200:
        log(f"设置测试模式失败: {st} {rm}")
        return 1
    log(f"run-mode 初始: test_chapters={rm.get('test_chapters')} cap={rm.get('normal_target_chapters')}")

    st, t = http_json(base, "POST", "/api/tasks", {"name": "验证6→18递增"})
    if st != 200:
        log(f"创建任务失败 {st} {t}")
        return 1
    tid = t["task_id"]
    log(f"已创建任务 task_id={tid}")

    st, s = http_json(base, "POST", f"/api/tasks/{tid}/start", {})
    log(f"启动流水线: st={st} body={s}")
    if st not in (200, 409):
        return 1

    t0 = time.time()
    last_tc = None
    while time.time() - t0 < args.timeout:
        st, rm = http_json(base, "GET", "/api/run-mode")
        tc = rm.get("test_chapters") if st == 200 else None
        st2, cur = http_json(base, "GET", "/api/tasks/current")
        running = cur.get("running") if st2 == 200 else None
        cid = cur.get("task_id") if st2 == 200 else None

        if tc != last_tc:
            log(f"★ test_chapters 变化: {last_tc} → {tc}  (cap={rm.get('normal_target_chapters') if st==200 else '?'})")
            last_tc = tc

        log(
            f"监听: test_chapters={tc} running={running} current_task={cid} "
            f"(距超时 {int(args.timeout - (time.time()-t0))}s)"
        )

        if tc is not None and tc >= 18 and not running:
            log(">>> 成功：test_chapters 已达 18（且当前无运行任务），验证 6→×3→18 通过。")
            return 0

        time.sleep(args.poll)

    log("超时未完成递增，请查服务器日志 journalctl -u ai-novel-agent -n 200")
    return 2


if __name__ == "__main__":
    sys.exit(main())
