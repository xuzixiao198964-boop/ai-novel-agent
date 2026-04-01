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


def main() -> None:
    host, port, user, password = ssh_host(), ssh_port(), ssh_user(), require_ssh_password()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, port=port, username=user, password=password, timeout=20)

    # 1) health（支持 JSON：status 为 ok 或 degraded）
    health_raw = run(c, "curl -s http://127.0.0.1:9000/api/health || true")
    print("health:", health_raw)
    try:
        h = json.loads(health_raw)
        st = h.get("status", "")
        if st not in ("ok", "degraded"):
            raise SystemExit("health check failed: bad status")
    except json.JSONDecodeError:
        if "ok" not in health_raw:
            raise SystemExit("health check failed")

    # 2) create + start
    task = curl_json(c, "POST", "http://127.0.0.1:9000/api/tasks", {"name": "验证任务-成书与预览"})
    tid = task["task_id"]
    print("task_id:", tid)
    curl_json(c, "POST", f"http://127.0.0.1:9000/api/tasks/{tid}/start")

    # 3) wait
    for _ in range(240):
        time.sleep(1)
        cur = curl_json(c, "GET", "http://127.0.0.1:9000/api/tasks/current")
        if not cur.get("running"):
            break
    print("pipeline_finished:", not cur.get("running"))

    # 4) outputs
    files = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/files")["files"]
    print("files_count:", len(files))
    novel_rel = "final/成书_含目录可跳转.md"
    novel_exists = any(f.get("path") == novel_rel for f in files)
    print("novel_exists:", "yes" if novel_exists else "no")

    # 5) view api (first 5 lines)
    q = urllib.parse.quote(novel_rel)
    view = run(c, f"curl -s 'http://127.0.0.1:9000/api/tasks/{tid}/files/view?path={q}'")
    head = "\n".join(view.splitlines()[:5])
    print("view_head:\n" + head)

    # 6) files by-agent
    by_agent = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/files/by-agent")["by_agent"]
    print("by_agent_keys:", list(by_agent.keys()))
    print("TrendAgent_files:", len(by_agent.get("TrendAgent", [])))

    # 7) novel TOC + chapters
    novel = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/novel")
    print("novel_title:", novel.get("title"))
    print("novel_toc_count:", len(novel.get("toc", [])))
    chapters = novel.get("chapters", []) or []
    print("novel_chapters_count:", len(chapters))

    # 期望：目录完整（>200章），正文仅前 20 章有内容，其余为空占位
    front_n = 20
    ok_first = True
    for i in range(min(front_n, len(chapters))):
        if not str(chapters[i].get("content", "")).strip():
            ok_first = False
            break
    ok_rest = True
    for i in range(front_n, len(chapters)):
        if str(chapters[i].get("content", "")).strip():
            ok_rest = False
            break
    print("content_first20_nonempty:", ok_first)
    print("content_rest_empty:", ok_rest)
    if not ok_first or not ok_rest:
        raise SystemExit("内容占位校验失败：目录可能不完整或正文生成数量不符合要求")

    c.close()


if __name__ == "__main__":
    main()

