# -*- coding: utf-8 -*-
"""清空所有任务（含已跑通），用于重新测试。需在 backend 目录执行。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import settings

def main():
    data_dir = Path(settings.data_dir)
    tasks_dir = data_dir / "tasks"
    state_dir = data_dir / "state"
    current_task_file = state_dir / "current_task.txt"
    removed = []
    if tasks_dir.exists():
        for p in tasks_dir.iterdir():
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed.append(p.name)
    if current_task_file.exists():
        current_task_file.write_text("", encoding="utf-8")
        removed.append("current_task.txt")
    print("已清空任务:", removed if removed else "（无）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
