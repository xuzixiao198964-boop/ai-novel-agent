# -*- coding: utf-8 -*-
"""仅小说阅读站：默认端口 8001。用法: python novel_server.py 或 uvicorn novel_server:app --host 0.0.0.0 --port 8001"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.novel_platform.db import init_db
from app.novel_platform.router import router as novel_platform_router

init_db()

app = FastAPI(title="小说阅读站", description="免费小说浏览与阅读")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(novel_platform_router, prefix="/novel-api")

static_dir = Path(__file__).resolve().parent / "static" / "novel"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="novel_root")


def main():
    import uvicorn

    port = int(os.environ.get("NOVEL_PORT", "8001"))
    uvicorn.run("novel_server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
