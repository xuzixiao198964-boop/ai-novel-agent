# -*- coding: utf-8 -*-
"""跑 >200（201）章故事大纲并只生成前 20 章正文。需在 backend 目录执行，且 .env 已配置 LLM。"""
import os
import sys

os.environ["TOTAL_CHAPTERS"] = "0"
os.environ["MAX_CHAPTERS_TO_WRITE"] = "20"
os.environ.setdefault("CHAPTER_RANGE_MIN", "201")
os.environ.setdefault("CHAPTER_RANGE_MAX", "201")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.state import create_task, get_task_meta
from app.core.pipeline import _run_pipeline

def main():
    task_id = create_task("长篇201章大纲+前20章正文")
    print("task_id:", task_id)
    print("配置: 201 章故事大纲，仅写前 20 章正文。开始运行流水线（同步）...")
    try:
        _run_pipeline(task_id)
    except Exception as e:
        import traceback
        print("流水线异常:", e)
        traceback.print_exc()
        return 1
    meta = get_task_meta(task_id)
    print("任务状态:", meta.get("status") if meta else "?")
    return 0 if (meta and meta.get("status") == "completed") else 1

if __name__ == "__main__":
    sys.exit(main())
