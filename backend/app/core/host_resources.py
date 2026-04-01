# -*- coding: utf-8 -*-
"""宿主机资源探测（对齐架构：104 裸机、磁盘门禁，无 Redis 依赖）"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# 与 docs/TESTING.md TC-C11 一致：剩余 < 500MB 视为 critical，拒绝新建任务
MIN_FREE_BYTES_FOR_NEW_TASK = 500 * 1024 * 1024
WARN_FREE_BYTES = 1024 * 1024 * 1024  # 1GB 以下 warning


@dataclass
class DiskInfo:
    path: str
    free_bytes: int
    total_bytes: int
    used_percent: float
    status: str  # ok | warning | critical

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "free_mb": round(self.free_bytes / (1024 * 1024), 2),
            "total_mb": round(self.total_bytes / (1024 * 1024), 2),
            "used_percent": round(self.used_percent, 2),
            "status": self.status,
        }


def disk_info_for_path(path: Path) -> Optional[DiskInfo]:
    """返回 path 所在挂载点的磁盘信息；失败时返回 None。"""
    try:
        resolved = path.resolve()
        usage = shutil.disk_usage(resolved)
    except OSError:
        return None
    total = usage.total
    free = usage.free
    if total <= 0:
        return None
    used_pct = (total - free) / total * 100.0
    if free < MIN_FREE_BYTES_FOR_NEW_TASK:
        st = "critical"
    elif free < WARN_FREE_BYTES:
        st = "warning"
    else:
        st = "ok"
    return DiskInfo(
        path=str(resolved),
        free_bytes=free,
        total_bytes=total,
        used_percent=used_pct,
        status=st,
    )


def memory_info_process_rss_mb() -> Optional[float]:
    """当前进程 RSS（MB），不可用则 None。"""
    try:
        import psutil

        p = psutil.Process(os.getpid())
        return round(p.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        pass
    try:
        import resource

        if hasattr(resource, "RUSAGE_SELF"):
            ru = resource.getrusage(resource.RUSAGE_SELF)
            if os.name != "nt":
                return round(ru.ru_maxrss / 1024.0, 2)
    except Exception:
        pass
    return None


def disk_allows_new_task(data_dir: Path) -> tuple[bool, Optional[DiskInfo]]:
    """是否允许新建生成类任务。"""
    info = disk_info_for_path(data_dir)
    if info is None:
        return True, None
    if info.status == "critical":
        return False, info
    return True, info
