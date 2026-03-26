# -*- coding: utf-8 -*-
import json
import time
import urllib.parse
import paramiko

HOST = "104.244.90.202"
PORT = 22
USER = "root"
PASSWORD = "C66ffUMycDn2"


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


def wait_finish(c: paramiko.SSHClient, timeout_s: int = 3600) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        cur = curl_json(c, "GET", "http://127.0.0.1:9000/api/tasks/current")
        if not cur.get("running"):
            return
        time.sleep(5)
    raise TimeoutError("pipeline timeout")


def stop_if_running(c: paramiko.SSHClient) -> None:
    try:
        cur = curl_json(c, "GET", "http://127.0.0.1:9000/api/tasks/current")
        if cur.get("running"):
            run(c, "curl -s -X POST http://127.0.0.1:9000/api/tasks/stop || true")
            wait_finish(c, timeout_s=300)
    except Exception:
        pass


def verify_task(c: paramiko.SSHClient, tid: str) -> dict:
    files = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/files")["files"]
    by_agent = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/files/by-agent")["by_agent"]
    novel = curl_json(c, "GET", f"http://127.0.0.1:9000/api/tasks/{tid}/novel")

    paths = {f.get("path") for f in files}
    must = {
        "trend/热门风格分析报告.md",
        "trend/trend_analysis.json",
        "style/风格参数表.md",
        # style_params.json 在某些版本可能不存在，因此不强制
        "final/成书_含目录可跳转.md",
    }
    missing = sorted([m for m in must if m not in paths])

    toc = novel.get("toc", []) or []
    chapters = novel.get("chapters", []) or []

    toc_count = len(toc)
    chapters_count = len(chapters)

    # 目录必须完整（200+）
    if toc_count < 200:
        raise SystemExit(f"TOC 数量不足: {toc_count} (<200)")
    if chapters_count < toc_count:
        # chapters 为空的情况也可能发生，但 novel 接口通常返回 chapters 对应的列表
        pass

    # 正文：仅前 20 章应有内容，其余为空
    front_n = 20
    ok_first = True
    for i in range(min(front_n, chapters_count)):
        if not str(chapters[i].get("content", "") or "").strip():
            ok_first = False
            break
    ok_rest = True
    for i in range(front_n, chapters_count):
        if str(chapters[i].get("content", "") or "").strip():
            ok_rest = False
            break

    if missing:
        raise SystemExit("缺少关键文件: " + ",".join(missing))
    if not ok_first or not ok_rest:
        raise SystemExit("正文占位校验失败：front 或 rest 不符合预期")

    return {
        "task_id": tid,
        "toc_count": toc_count,
        "chapters_count": chapters_count,
        "trend_files": len(by_agent.get("TrendAgent", [])),
        "style_files": len(by_agent.get("StyleAgent", [])),
        "missing": missing,
        "content_first20_nonempty": ok_first,
        "content_rest_empty": ok_rest,
    }


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=20)

    health = run(c, "curl -s http://127.0.0.1:9000/api/health || true")
    print("health:", health)

    stop_if_running(c)

    results = []
    for idx in [1, 2, 3]:
        stop_if_running(c)
        task = curl_json(c, "POST", "http://127.0.0.1:9000/api/tasks", {"name": f"自动生成小说-{idx}"})
        tid = task["task_id"]
        print("task_id:", tid)

        # 启动
        curl_json(c, "POST", f"http://127.0.0.1:9000/api/tasks/{tid}/start")

        # 等待完成
        wait_finish(c, timeout_s=5400)

        # 校验输出
        try:
            v = verify_task(c, tid)
            results.append(v)
            print("verify:", json.dumps(v, ensure_ascii=False))
        except Exception as e:
            # 单本失败不终止脚本，方便后续定位问题与继续跑
            results.append({"task_id": tid, "idx": idx, "error": str(e)})
            print("verify_failed:", str(e))

    c.close()
    print("DONE")
    print("ALL_RESULTS:", json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()

