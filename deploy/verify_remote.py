# -*- coding: utf-8 -*-
import time
import json
import urllib.request

BASE = "http://127.0.0.1:9000"

def req(path, method="GET", data=None):
    url = BASE + path
    if data is not None:
        data = json.dumps(data).encode("utf-8")
    r = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=10) as f:
        return json.loads(f.read().decode())

def main():
    # 1. 创建任务
    out = req("/api/tasks", "POST", {"name": "测试任务"})
    tid = out["task_id"]
    print("Created task:", tid)

    # 2. 启动
    req(f"/api/tasks/{tid}/start", "POST")
    print("Started.")

    # 3. 轮询
    for _ in range(90):
        time.sleep(2)
        cur = req("/api/tasks/current")
        if not cur.get("running"):
            print("Pipeline finished.")
            break
        prog = req(f"/api/tasks/{tid}/progress")
        done = sum(1 for v in prog.values() if v.get("status") == "completed")
        print("Progress:", done, "/ 7")
    else:
        print("Timeout")

    # 4. 文件
    files = req(f"/api/tasks/{tid}/files")
    print("Files count:", len(files.get("files", [])))
    for f in files.get("files", [])[:10]:
        print(" ", f["path"])
    print("OK")

if __name__ == "__main__":
    main()
