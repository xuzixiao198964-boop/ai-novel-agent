# -*- coding: utf-8 -*-
"""部署验证：创建任务并启动流水线，轮询直至完成或失败，返回退出码与简要信息。"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://127.0.0.1:9000/api"
POLL_INTERVAL = 15
MAX_WAIT_SECONDS = 3600 * 2


def req(path: str, method: str = "GET", body: str | None = None) -> dict:
    url = API_BASE + path
    headers = {"Content-Type": "application/json"}
    data = body.encode("utf-8") if body else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            b = e.read().decode("utf-8")
            return {"_error": str(e), "_body": b}
        except Exception:
            return {"_error": str(e)}
    except Exception as e:
        return {"_error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-start", action="store_true", help="创建任务并启动（自动生成小说）")
    parser.add_argument("--task-id", type=str, default="", help="已有任务 ID，仅启动")
    parser.add_argument("--run-label", type=str, default="1", help="第几次运行，用于任务名")
    parser.add_argument("--poll-only", type=str, default="", help="仅轮询该 task_id 直至结束")
    args = parser.parse_args()

    if args.poll_only:
        task_id = args.poll_only
        print(f"轮询任务 {task_id} 直至完成或失败...")
        start = time.time()
        while time.time() - start < MAX_WAIT_SECONDS:
            cur = req("/tasks/current")
            if cur.get("_error"):
                print("当前任务接口错误:", cur.get("_error"))
                sys.exit(2)
            if not cur.get("running") and not cur.get("task_id"):
                meta = req(f"/tasks/{task_id}")
                if meta.get("_error"):
                    print("获取任务 meta 失败:", meta.get("_error"))
                    sys.exit(2)
                status = meta.get("status", "")
                print(f"任务已结束，状态: {status}")
                if status == "completed":
                    print("SUCCESS")
                    sys.exit(0)
                if status == "failed":
                    summary = req(f"/tasks/{task_id}/progress")
                    for name, p in (summary or {}).items():
                        if isinstance(p, dict) and p.get("status") == "failed":
                            print(f"  {name}: {p.get('message', '')}")
                    sys.exit(1)
                sys.exit(0)
            prog = req(f"/tasks/{task_id}/progress")
            if not prog.get("_error"):
                running = [k for k, v in prog.items() if isinstance(v, dict) and v.get("status") == "running"]
                msg = running[0] if running else "等待中"
                print(f"  运行中: {msg} ({int(time.time() - start)}s)")
            time.sleep(POLL_INTERVAL)
        print("超时")
        sys.exit(3)

    if args.create_start:
        name = f"自动生成小说{args.run_label}"
        r = req("/tasks", method="POST", body=json.dumps({"name": name}))
        if r.get("_error"):
            print("创建任务失败:", r.get("_error"))
            sys.exit(2)
        task_id = r.get("task_id")
        if not task_id:
            print("创建任务未返回 task_id:", r)
            sys.exit(2)
        print(f"已创建任务: {task_id} ({name})")
        r2 = req(f"/tasks/{task_id}/start", method="POST")
        if r2.get("_error"):
            print("启动失败:", r2.get("_error"), r2.get("_body", ""))
            sys.exit(2)
        print("已启动流水线")
        start = time.time()
        while time.time() - start < MAX_WAIT_SECONDS:
            cur = req("/tasks/current")
            if cur.get("_error"):
                print("当前任务接口错误:", cur.get("_error"))
                sys.exit(2)
            if not cur.get("running"):
                meta = req(f"/tasks/{task_id}")
                status = meta.get("status", "")
                print(f"任务已结束，状态: {status}")
                if status == "completed":
                    print("SUCCESS")
                    sys.exit(0)
                if status == "failed":
                    summary = req(f"/tasks/{task_id}/progress")
                    for name, p in (summary or {}).items():
                        if isinstance(p, dict) and p.get("status") == "failed":
                            print(f"  失败 Agent: {name} -> {p.get('message', '')}")
                    sys.exit(1)
                sys.exit(0)
            prog = req(f"/tasks/{task_id}/progress")
            if not prog.get("_error"):
                running = [k for k, v in prog.items() if isinstance(v, dict) and v.get("status") == "running"]
                msg = running[0] if running else "等待中"
                print(f"  运行中: {msg} ({int(time.time() - start)}s)")
            time.sleep(POLL_INTERVAL)
        print("超时")
        sys.exit(3)

    if args.task_id:
        r = req(f"/tasks/{args.task_id}/start", method="POST")
        if r.get("_error"):
            print("启动失败:", r.get("_error"))
            sys.exit(2)
        print("已启动，请使用 --poll-only", args.task_id, "轮询")
        sys.exit(0)

    print("请使用 --create-start 或 --task-id ID 或 --poll-only ID")
    sys.exit(0)


if __name__ == "__main__":
    main()
