import json
import os
import time
import urllib.error
import urllib.request

import paramiko

BASE = "http://104.244.90.202:9000"
HOST = "104.244.90.202"
PW = os.environ.get("DEPLOY_SSH_PASSWORD", "v9wSxMxg92dp")


def req(method, path, body=None, timeout=120):
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            t = resp.read().decode("utf-8")
            return resp.status, json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        t = e.read().decode("utf-8", "replace")
        try:
            j = json.loads(t)
        except Exception:
            j = {"detail": t}
        return e.code, j


def ssh_cmds(cmds):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, 22, "root", PW, timeout=60)
    try:
        out_all = []
        for cmd in cmds:
            _, so, se = c.exec_command(cmd, timeout=180)
            out = so.read().decode("utf-8", "replace")
            err = se.read().decode("utf-8", "replace")
            if err.strip():
                raise RuntimeError(f"{cmd}\n{err}")
            out_all.append(out.strip())
        return out_all
    finally:
        c.close()


def main():
    result = {}

    # 1) 书架免登录
    st, b = req("GET", "/api/bookshelf")
    assert st == 200 and "books" in b, (st, b)
    result["bookshelf_public"] = True

    # 2) 连续模式启动不冲掉旧任务（返回 queued）
    req("POST", "/api/tasks/auto-run", {"auto_run": True})
    st, t = req("POST", "/api/tasks", {"name": "自测-连续队列A"})
    assert st == 200, (st, t)
    tid = t["task_id"]
    st, s1 = req("POST", f"/api/tasks/{tid}/start", {})
    assert st == 200 and s1.get("ok"), (st, s1)
    st, s2 = req("POST", f"/api/tasks/{tid}/start", {})
    assert st == 200 and s2.get("queued") is True and s2.get("queued_task_id"), (st, s2)
    result["queue_new_task"] = {"current": tid, "queued": s2.get("queued_task_id")}

    # 3) 验证真实 DeepSeek 可调用（直接在服务器内调用 llm.chat）
    py = (
        "set -a; . /opt/ai-novel-agent/.env; set +a; "
        "cd /opt/ai-novel-agent/backend && "
        "/opt/ai-novel-agent/venv/bin/python -c "
        "\"from app.core import llm; "
        "r=llm.chat([{'role':'system','content':'你是助手'},{'role':'user','content':'只回复OK'}],max_tokens=16,timeout_s=60,retries=1); "
        "print(r[:80])\""
    )
    out = ssh_cmds([py])[0]
    assert out.strip(), out
    result["deepseek_call_output"] = out.strip()

    # 4) 构造“已完成任务”并触发自动同步到小说平台
    st, t2 = req("POST", "/api/tasks", {"name": "自测-平台同步清理"})
    assert st == 200, (st, t2)
    tid2 = t2["task_id"]
    ssh_py = (
        "python3 - <<'PY'\n"
        "import json, pathlib\n"
        f"tid='{tid2}'\n"
        "base=pathlib.Path('/opt/ai-novel-agent/backend/data/tasks')/tid\n"
        "(base/'output/planner').mkdir(parents=True,exist_ok=True)\n"
        "(base/'output/final').mkdir(parents=True,exist_ok=True)\n"
        "meta=json.load(open(base/'meta.json','r',encoding='utf-8'))\n"
        "meta['status']='completed'\n"
        "meta['updated_at']='2026-03-23T00:00:00'\n"
        "json.dump(meta,open(base/'meta.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)\n"
        "outline={'chapters':[{'title':'第1章 开场'}]}\n"
        "json.dump(outline,open(base/'output/planner/outline.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)\n"
        "open(base/'output/final/ch_01.md','w',encoding='utf-8').write('# 第1章\\n\\n测试正文')\n"
        "open(base/'output/final/成书_含目录可跳转.md','w',encoding='utf-8').write('# 自测小说\\n\\n## 目录\\n- [第1章 开场](#chapter-01)\\n\\n## 正文\\n### 第1章 开场\\n<a id=\\\"chapter-01\\\"></a>\\n\\n测试正文')\n"
        "PY"
    )
    ssh_cmds([ssh_py])
    # 触发 sync
    req("GET", "/api/tasks")
    st, novel_list = req("GET", "/novel-api/novels?page=1&per_page=50")
    assert st == 200, (st, novel_list)
    assert any(str(n.get("source_task_id") or "") == tid2 for n in (novel_list.get("novels") or [])), novel_list
    result["platform_sync"] = {"task_id": tid2, "synced": True}

    # 5) 模拟超过1天，触发清理后仍可在书架读取目录
    old_meta_cmd = (
        "python3 - <<'PY'\n"
        "import json\n"
        f"p='/opt/ai-novel-agent/backend/data/tasks/{tid2}/meta.json'\n"
        "m=json.load(open(p,'r',encoding='utf-8'))\n"
        "m['status']='completed'\n"
        "m['updated_at']='2020-01-01T00:00:00'\n"
        "json.dump(m,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=2)\n"
        "PY"
    )
    ssh_cmds([old_meta_cmd])
    req("GET", "/api/tasks")
    st, _ = req("GET", f"/api/tasks/{tid2}")
    assert st == 404, st
    st, toc = req("GET", f"/api/tasks/{tid2}/novel/toc")
    assert st == 200 and int(toc.get("chapter_count") or 0) >= 1, (st, toc)
    result["purge_keep_bookshelf"] = {"task_id": tid2, "chapter_count": toc.get("chapter_count")}

    # 清理：关闭连续模式，停止当前任务
    req("POST", "/api/tasks/auto-run", {"auto_run": False})
    req("POST", "/api/tasks/stop", {})
    result["done"] = True
    print("SELFTEST_FAST_OK")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
