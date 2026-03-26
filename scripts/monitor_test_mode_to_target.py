# -*- coding: utf-8 -*-
"""
持续监听测试模式章数，直到达到目标（默认 200）或手动 Ctrl+C。

用法（在项目根或 scripts 上级）:
  python scripts/monitor_test_mode_to_target.py --base http://104.244.90.202:9000 --target 200

逻辑:
  1. 切到测试模式，可选重置 test_chapters=6
  2. 开启「自动连续生成」
  3. 若无运行中任务则创建并启动一本
  4. 轮询 GET /api/run-mode、GET /api/tasks/current，打印 test_chapters / normal_target / 运行任务
  5. 当 test_chapters >= target 且当前无运行任务时退出 0

注意:
  - 递增量为「当前档 ×3」直至 cap（趋势建议章数，受 chapter_range 约束）。若 cap < target，无法达到 target。
  - 每次完整流水线耗时可很长，且消耗 LLM 额度；失败会回退到 6 章（见 pipeline finally）。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:9000", help="站点根，如 http://IP:9000")
    ap.add_argument("--target", type=int, default=200, help="目标测试章数（达到即退出）")
    ap.add_argument("--interval", type=float, default=60.0, help="轮询秒数")
    ap.add_argument("--reset", action="store_true", help="先将测试档重置为 6 章再开始")
    ap.add_argument("--no-start", action="store_true", help="只监听，不创建/启动任务")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    def log(msg: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line, flush=True)

    log(f"监听开始 base={base} target={args.target} 间隔={args.interval}s")

    # 测试模式 + 可选重置 6 章
    rm_body: dict = {"mode": "test"}
    if args.reset:
        rm_body["test_chapters"] = 6
    st, j = http_json(base, "POST", "/api/run-mode", rm_body)
    if st != 200:
        log(f"POST /api/run-mode 失败 st={st} {j}")
        return 1
    tc = j.get("test_chapters")
    cap = j.get("normal_target_chapters")
    log(f"run-mode: test_chapters={tc} normal_target_chapters={cap} mode={j.get('mode')}")
    if cap is not None and cap < args.target:
        log(f"警告: 趋势上限 cap={cap} < target={args.target}，API 侧无法超过 cap，请调大纲/趋势或 chapter_range。")

    st, j = http_json(base, "POST", "/api/tasks/auto-run", {"auto_run": True})
    if st != 200:
        log(f"开启自动连续生成失败 st={st} {j}")
        return 1
    log("已开启自动连续生成 auto_run=True")

    if not args.no_start:
        st, cur = http_json(base, "GET", "/api/tasks/current")
        if st == 200 and cur.get("running"):
            log(f"已有运行中任务 task_id={cur.get('task_id')}，不重复启动")
        else:
            st, t = http_json(base, "POST", "/api/tasks", {"name": "测试模式-递增至目标章数"})
            if st != 200:
                log(f"创建任务失败 st={st} {t}")
                return 1
            tid = t.get("task_id")
            log(f"已创建任务 task_id={tid}")
            st, s = http_json(base, "POST", f"/api/tasks/{tid}/start", {})
            if st != 200:
                log(f"启动失败 st={st} {s}（可能已有任务在跑，稍后将由 auto_run 接力）")
            else:
                log(f"已请求启动: {s}")

    last_tc = -1
    while True:
        st, rm = http_json(base, "GET", "/api/run-mode")
        if st != 200:
            log(f"GET /api/run-mode 失败 st={st}")
            time.sleep(args.interval)
            continue
        tc = rm.get("test_chapters")
        cap = rm.get("normal_target_chapters")
        mode = rm.get("mode")

        st2, cur = http_json(base, "GET", "/api/tasks/current")
        running = cur.get("running") if st2 == 200 else None
        tid = cur.get("task_id") if st2 == 200 else None

        if tc != last_tc:
            log(f"测试档变更: test_chapters={tc} (cap={cap}) mode={mode} running={running} current_task={tid}")
            last_tc = tc if tc is not None else last_tc

        if tc is not None and tc >= args.target and not running:
            log(f"达到目标: test_chapters={tc} >= {args.target}，且无运行中任务。结束。")
            return 0

        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中断", flush=True)
        sys.exit(130)
