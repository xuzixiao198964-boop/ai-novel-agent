# -*- coding: utf-8 -*-
import json
import sys
import time
import urllib.parse
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


def curl_json(c: paramiko.SSHClient, method: str, url: str, body: dict | None = None) -> dict:
    if body is None:
        cmd = f"curl -s -X {method} '{url}'"
    else:
        payload = json.dumps(body, ensure_ascii=False).replace("'", "'\\''")
        cmd = f"curl -s -X {method} '{url}' -H 'Content-Type: application/json' -d '{payload}'"
    out = run(c, cmd)
    return json.loads(out)


def wait_finish(c: paramiko.SSHClient, timeout_s: int = 1800) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        cur = curl_json(c, "GET", "http://127.0.0.1:9000/api/tasks/current")
        if not cur.get("running"):
            return
        time.sleep(2)
    raise TimeoutError("pipeline timeout")


def verify_task(c: paramiko.SSHClient, tid: str) -> dict:
    files = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/files")["files"]
    by_agent = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/files/by-agent")["by_agent"]
    novel = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/novel")
    meta = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}")
    prog = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/progress") or {}
    failed_agents = []
    for k, v in (prog or {}).items():
        if isinstance(v, dict) and v.get("status") == "failed":
            failed_agents.append({"agent": k, "message": v.get("message", "")})
    failed_agents.sort(key=lambda x: x.get("agent", ""))
    # 关键文件存在
    must = {
        "trend/热门风格分析报告.md",
        "trend/trend_analysis.json",
        "style/风格参数表.md",
        "style/style_params.json",
        "final/成书_含目录可跳转.md",
    }
    paths = {f["path"] for f in files}
    missing = sorted(list(must - paths))
    return {
        "files_count": len(files),
        "missing": missing,
        "novel_title": novel.get("title"),
        "toc_count": len(novel.get("toc", [])),
        "chapters_count": len(novel.get("chapters", [])),
        "trend_files": len(by_agent.get("TrendAgent", [])),
        "style_files": len(by_agent.get("StyleAgent", [])),
        "status": meta.get("status"),
        "failed_agents": failed_agents,
    }


def main() -> None:
    host, port, user, password = ssh_host(), ssh_port(), ssh_user(), require_ssh_password()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, port=port, username=user, password=password, timeout=20)

    health = run(c, "curl -s http://127.0.0.1:9000/api/health || true")
    print("health:", health)

    # 如果已有任务在跑，先请求停止并等待退出，避免 409 导致脚本卡住
    try:
        cur = curl_json(c, "GET", "http://127.0.0.1:9000/api/tasks/current")
        if cur.get("running"):
            print("found_running_task:", cur.get("task_id"))
            run(c, "curl -s -X POST http://127.0.0.1:9000/api/tasks/stop || true")
            wait_finish(c, timeout_s=300)
    except Exception:
        pass

    results = []
    for idx in [1, 2]:
        # 确保无运行中任务
        wait_finish(c, timeout_s=300)
        task = curl_json(c, "POST", "http://127.0.0.1:9000/api/tasks", {"name": f"自动生成小说-{idx}"})
        tid = task["task_id"]
        print("task_id:", tid)
        # 启动（若冲突则等待后重试一次）
        try:
            curl_json(c, "POST", f"http://127.0.0.1:9000/api/tasks/{tid}/start")
        except Exception:
            wait_finish(c, timeout_s=300)
            curl_json(c, "POST", f"http://127.0.0.1:9000/api/tasks/{tid}/start")
        # 给足时间：趋势/策划/大纲/写作/润色/审计/定稿全流程
        wait_finish(c, timeout_s=2400)
        v = verify_task(c, tid)
        v["task_id"] = tid
        results.append(v)
        print("verify:", json.dumps(v, ensure_ascii=False))

    c.close()
    print("DONE")


if __name__ == "__main__":
    main()

