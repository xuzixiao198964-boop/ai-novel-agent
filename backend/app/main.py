# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager
import threading
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.core.state import set_current_task_id, purge_old_completed_tasks, sync_completed_tasks_to_platform
from app.api.routes import router
from app.novel_platform.router import router as novel_platform_router
from app.novel_platform.db import init_db as init_novel_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.memory_dir.mkdir(parents=True, exist_ok=True)
    # systemd/uvicorn 重启后流水线线程已不存在，若仍保留 current_task.txt，
    # 会导致 /api/tasks/current 永远「运行中」且无法启动新任务。
    set_current_task_id(None)
    try:
        init_novel_db()
    except Exception:
        pass
    stop_evt = threading.Event()

    def _maintenance_loop() -> None:
        while not stop_evt.is_set():
            try:
                sync_completed_tasks_to_platform(limit=200)
                purge_old_completed_tasks(retention_hours=24)
            except Exception:
                pass
            stop_evt.wait(1800)  # 每 30 分钟执行一次

    th = threading.Thread(target=_maintenance_loop, daemon=True)
    th.start()
    yield
    stop_evt.set()


app = FastAPI(title="AI小说生成Agent系统", description="多Agent协同小说生成与进度可视化", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(novel_platform_router, prefix="/novel-api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 小说阅读站静态页（需在根路径 mount 之前注册）
static_dir = Path(__file__).resolve().parents[1] / "static"
novel_static = static_dir / "novel"
if novel_static.exists():
    app.mount("/novel", StaticFiles(directory=str(novel_static), html=True), name="novel_static")

# 静态网页（必须放在最后，否则会拦截 /api/*）
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def main():
    import uvicorn
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.memory_dir.mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
