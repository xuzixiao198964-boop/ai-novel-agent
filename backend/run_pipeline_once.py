# -*- coding: utf-8 -*-
"""本地同步跑通流水线一次（用于排查错误）。需配置 .env 的 LLM。"""
import os
import sys

# 短篇配置，确保能跑完
os.environ["TOTAL_CHAPTERS"] = "5"
os.environ["WORDS_PER_CHAPTER"] = "1500"

# 在 import app 之前设置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.state import create_task, _task_dir, update_task_meta, TaskStatus
from app.core.pipeline import _run_pipeline

def main():
    task_id = create_task("本地跑通测试")
    print("task_id:", task_id)
    print("开始运行流水线（同步）...")
    try:
        _run_pipeline(task_id)
    except Exception as e:
        import traceback
        print("流水线异常:", e)
        traceback.print_exc()
        return 1
    meta = __import__("app.core.state", fromlist=["get_task_meta"]).get_task_meta(task_id)
    print("任务状态:", meta.get("status") if meta else "?")
    return 0 if (meta and meta.get("status") == "completed") else 1

if __name__ == "__main__":
    sys.exit(main())
