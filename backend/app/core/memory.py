# -*- coding: utf-8 -*-
"""长期记忆库：7 个真相文件，所有 Agent 共享"""
from pathlib import Path
from app.core.config import settings


MEMORY_FILES = [
    "current_state.md",      # 世界当前状态
    "character_matrix.md",   # 人设与关系矩阵
    "pending_hooks.md",      # 未闭合伏笔
    "chapter_summaries.md",  # 章节摘要
    "subplot_board.md",      # 支线进度
    "emotional_arcs.md",     # 情感弧线
    "world_rules.md",       # 世界观规则
]


def get_memory_dir(task_id: str) -> Path:
    d = settings.data_dir / "tasks" / task_id / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_memory_path(task_id: str, filename: str) -> Path:
    if filename not in MEMORY_FILES:
        raise ValueError(f"Unknown memory file: {filename}")
    return get_memory_dir(task_id) / filename


def read_memory(task_id: str, filename: str) -> str:
    p = get_memory_path(task_id, filename)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_memory(task_id: str, filename: str, content: str) -> Path:
    p = get_memory_path(task_id, filename)
    p.write_text(content, encoding="utf-8")
    return p


def list_memory_files(task_id: str) -> list[dict]:
    d = get_memory_dir(task_id)
    out = []
    for name in MEMORY_FILES:
        p = d / name
        out.append({
            "name": name,
            "exists": p.exists(),
            "size": p.stat().st_size if p.exists() else 0,
        })
    return out


def init_memory_for_task(task_id: str) -> None:
    """为新任务初始化空的记忆文件"""
    d = get_memory_dir(task_id)
    for name in MEMORY_FILES:
        p = d / name
        if not p.exists():
            p.write_text(f"# {name}\n\n（待填写）\n", encoding="utf-8")
