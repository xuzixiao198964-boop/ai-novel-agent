# -*- coding: utf-8 -*-
"""网页端与 Agent、任务、文件交互的 API"""
import os
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import secrets

from app.core.state import (
    list_tasks,
    create_task,
    delete_task,
    clear_all_tasks,
    get_task_meta,
    get_task_progress_summary,
    get_agent_logs,
    list_output_files,
    list_output_files_by_agent,
    get_output_file_path,
    get_current_task_id,
    get_auto_run,
    set_auto_run,
    get_run_mode,
    set_run_mode,
    get_test_mode_chapters,
    set_test_mode_chapters,
    get_novel_toc_and_chapters,
    list_bookshelf_tasks,
    get_novel_toc_only,
    get_chapter_content,
    _task_dir,
    purge_old_completed_tasks,
    sync_completed_tasks_to_platform,
)
from app.core.memory import list_memory_files, read_memory, write_memory, MEMORY_FILES
from app.core.pipeline import start_pipeline, stop_pipeline, pause_pipeline, resume_pipeline, is_pipeline_running, is_pipeline_paused
from app.core.config import settings
from app.core.trend_cap import get_trend_suggested_chapter_cap

router = APIRouter(prefix="/api", tags=["api"])
_BOOKSHELF_TOKENS: dict[str, dict] = {}


# ---------- 简单密码校验（可选） ----------
def check_password(req: Request) -> bool:
    if not settings.web_password:
        return True
    auth = req.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        return auth[7:] == settings.web_password
    return False


def _bookshelf_admin_password() -> str:
    return (settings.web_admin_password or settings.web_password or "admin123456").strip()


def _bookshelf_user_password() -> str:
    return (settings.web_user_password or "user123456").strip()


def _issue_bookshelf_token(role: str) -> str:
    token = secrets.token_hex(16)
    _BOOKSHELF_TOKENS[token] = {
        "role": role,
        "expire_at": datetime.now() + timedelta(hours=24),
    }
    return token


def _parse_bookshelf_auth(req: Request) -> Optional[dict]:
    auth = req.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    rec = _BOOKSHELF_TOKENS.get(token)
    if not rec:
        return None
    if datetime.now() > rec.get("expire_at", datetime.min):
        _BOOKSHELF_TOKENS.pop(token, None)
        return None
    return rec


class TaskCreate(BaseModel):
    name: str = "新小说任务"


class MemoryUpdate(BaseModel):
    content: str


class RunModeUpdate(BaseModel):
    mode: str
    test_chapters: Optional[int] = None


class BookshelfLoginBody(BaseModel):
    username: str
    password: str


# ---------- 任务 ----------
@router.get("/tasks")
def api_list_tasks():
    sync_completed_tasks_to_platform(limit=100)
    purge_old_completed_tasks()
    return {"tasks": list_tasks()}


@router.post("/tasks")
def api_create_task(body: TaskCreate):
    task_id = create_task(body.name)
    return {"task_id": task_id, "name": body.name}


@router.get("/tasks/current")
def api_current_task():
    tid = get_current_task_id()
    return {
        "task_id": tid,
        "running": tid is not None,
        "paused": is_pipeline_paused() if tid else False,
        "auto_run": get_auto_run(),
    }


@router.get("/tasks/auto-run")
def api_get_auto_run():
    return {"auto_run": get_auto_run()}


@router.post("/tasks/auto-run")
def api_set_auto_run(body: dict = None):
    enabled = bool(body.get("auto_run", False)) if body else False
    set_auto_run(enabled)
    return {"ok": True, "auto_run": enabled}


@router.get("/run-mode")
def api_get_run_mode():
    mode = get_run_mode()
    normal_target = get_trend_suggested_chapter_cap(None)
    test_chapters = min(get_test_mode_chapters(6), normal_target)
    return {
        "mode": mode,
        "label": (f"测试{test_chapters}章" if mode == "test" else "正式模式"),
        "test_chapters": test_chapters,
        "normal_target_chapters": normal_target,
    }


@router.post("/run-mode")
def api_set_run_mode(body: RunModeUpdate):
    mode = set_run_mode(body.mode)
    if body.test_chapters is not None:
        set_test_mode_chapters(body.test_chapters)
    normal_target = get_trend_suggested_chapter_cap(None)
    test_chapters = min(get_test_mode_chapters(6), normal_target)
    return {
        "ok": True,
        "mode": mode,
        "label": (f"测试{test_chapters}章" if mode == "test" else "正式模式"),
        "test_chapters": test_chapters,
        "normal_target_chapters": normal_target,
    }


@router.get("/tasks/{task_id}")
def api_get_task(task_id: str):
    meta = get_task_meta(task_id)
    if not meta:
        raise HTTPException(404, "任务不存在")
    return meta


@router.get("/tasks/{task_id}/progress")
def api_task_progress(task_id: str):
    return get_task_progress_summary(task_id)


@router.delete("/tasks/{task_id}")
def api_delete_task(task_id: str):
    """删除指定任务；若该任务正在运行则返回 409。"""
    if get_task_meta(task_id) is None:
        raise HTTPException(404, "任务不存在")
    # 若删除的是当前运行任务：先请求停止，再等待清空 running 状态，减少前端 409 Conflict
    if get_current_task_id() == task_id:
        from app.core.pipeline import stop_pipeline
        stop_pipeline()
        # 最多等待 60 秒，直到流水线退出
        import time as _time
        deadline = _time.time() + 60
        while _time.time() < deadline and get_current_task_id() == task_id:
            _time.sleep(0.3)
    if not delete_task(task_id):
        raise HTTPException(409, "无法删除正在运行的任务（请先停止或稍后重试）")
    return {"ok": True, "message": "已删除"}


@router.get("/tasks/{task_id}/logs/{agent_name}")
def api_agent_logs(task_id: str, agent_name: str, limit: int = Query(200, le=500)):
    return {"logs": get_agent_logs(task_id, agent_name, limit)}


@router.post("/tasks/{task_id}/start")
def api_start_task(task_id: str):
    if get_task_meta(task_id) is None:
        raise HTTPException(404, "任务不存在")
    purge_old_completed_tasks()
    # 若已有任务在运行：连续模式下不冲掉旧任务，改为新建任务
    if not start_pipeline(task_id):
        current = get_current_task_id()
        if current and get_auto_run():
            next_id = create_task("自动连续任务")
            return {
                "ok": True,
                "queued": True,
                "current_task_id": current,
                "queued_task_id": next_id,
                "message": "当前任务运行中（连续模式），已新建下一本任务，不会中断当前任务",
            }
        raise HTTPException(409, "已有任务在运行，请先停止或开启连续模式后再点启动")
    return {"ok": True, "message": "流水线已启动"}


@router.post("/tasks/stop")
def api_stop_task():
    if not stop_pipeline():
        raise HTTPException(409, "当前没有运行中的任务")
    return {"ok": True, "message": "已请求停止"}


@router.post("/tasks/pause")
def api_pause_task():
    if not pause_pipeline():
        raise HTTPException(409, "当前没有运行中的任务")
    return {"ok": True, "message": "已请求暂停"}


@router.post("/tasks/resume")
def api_resume_task():
    if not resume_pipeline():
        raise HTTPException(409, "当前没有运行中的任务")
    return {"ok": True, "message": "已继续"}


@router.post("/admin/clear_tasks")
def api_clear_all_tasks(req: Request):
    """清空所有任务（含已跑通）。若配置了 web_password 则需 Authorization: Bearer <password>。"""
    if not check_password(req):
        raise HTTPException(401, "需要认证")
    removed = clear_all_tasks()
    return {"ok": True, "message": "已清空全部任务", "removed": removed}


# ---------- 文件 ----------
@router.get("/tasks/{task_id}/files")
def api_list_files(task_id: str):
    return {"files": list_output_files(task_id)}


@router.get("/tasks/{task_id}/files/by-agent")
def api_list_files_by_agent(task_id: str):
    """按 Agent 分组的文件列表，供前端点击 Agent 展示对应结果"""
    return {"by_agent": list_output_files_by_agent(task_id)}


@router.get("/tasks/{task_id}/files/download")
def api_download_file(task_id: str, path: str):
    fp = get_output_file_path(task_id, path)
    if not fp or not fp.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(fp, filename=os.path.basename(fp))


@router.get("/tasks/{task_id}/novel")
def api_novel_toc_and_chapters(task_id: str):
    """小说目录与章节正文，供前端“只展示目录、点击弹正文+上下章”"""
    data = get_novel_toc_and_chapters(task_id)
    if not data:
        raise HTTPException(404, "成书文件不存在或未生成")
    return data


# ---------- 书架（已发布小说列表 + 目录 + 单章） ----------
@router.post("/bookshelf/login")
def api_bookshelf_login(body: BookshelfLoginBody):
    admin_pwd = _bookshelf_admin_password()
    user_pwd = _bookshelf_user_password()
    role = None
    if admin_pwd and body.password == admin_pwd and body.username.strip().lower() in {"admin", "管理员"}:
        role = "admin"
    elif user_pwd and body.password == user_pwd and body.username.strip().lower() in {"user", "普通用户", "reader"}:
        role = "user"
    elif admin_pwd and not user_pwd and body.password == admin_pwd:
        # 兼容旧配置：只有一个密码时仍可登录（admin）
        role = "admin"
    if not role:
        raise HTTPException(401, "用户名或密码错误")
    token = _issue_bookshelf_token(role)
    return {"token": token, "role": role}


def _require_bookshelf_login(req: Request) -> dict:
    rec = _parse_bookshelf_auth(req)
    if rec:
        return rec
    raise HTTPException(401, "需要登录")


@router.get("/bookshelf")
def api_bookshelf(req: Request):
    """书架：已完结且有成书的任务列表"""
    sync_completed_tasks_to_platform(limit=100)
    purge_old_completed_tasks()
    return {"books": list_bookshelf_tasks()}


@router.get("/tasks/{task_id}/novel/toc")
def api_novel_toc_only(task_id: str, req: Request):
    """仅返回成书标题与目录，供书架目录页"""
    data = get_novel_toc_only(task_id)
    if not data:
        raise HTTPException(404, "成书不存在或未生成")
    return data


@router.get("/tasks/{task_id}/novel/chapters/{chapter_index:int}")
def api_novel_chapter(task_id: str, chapter_index: int, req: Request):
    """按章节下标（从 0 起）返回单章内容，供书架阅读页"""
    if chapter_index < 0:
        raise HTTPException(400, "章节下标无效")
    data = get_chapter_content(task_id, chapter_index)
    if not data:
        raise HTTPException(404, "章节不存在")
    return data


@router.delete("/bookshelf/books/{task_id}")
def api_bookshelf_delete_book(task_id: str, req: Request):
    auth = _require_bookshelf_login(req)
    if auth.get("role") != "admin":
        raise HTTPException(403, "仅管理员可删除")
    if not delete_task(task_id):
        raise HTTPException(400, "删除失败（可能任务正在运行）")
    return {"ok": True}


@router.get("/tasks/{task_id}/outline")
def api_task_outline(task_id: str, page: int = Query(1, ge=1), per_page: int = Query(30, ge=1, le=100)):
    """故事大纲分页（每页最多 30 章），供前端大纲预览"""
    import json as _json
    task_d = _task_dir(task_id)
    outline_p = task_d / "output" / "planner" / "outline.json"
    if not outline_p.exists():
        raise HTTPException(404, "大纲不存在")
    try:
        data = _json.loads(outline_p.read_text(encoding="utf-8"))
        chapters = data.get("chapters") or []
    except Exception:
        raise HTTPException(500, "大纲解析失败")
    total = len(chapters)
    start = (page - 1) * per_page
    end = min(start + per_page, total)
    return {
        "chapters": chapters[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total else 0,
    }


@router.get("/tasks/{task_id}/files/view")
def api_view_file(task_id: str, path: str, max_kb: int = Query(512, ge=1, le=2048)):
    """网页端直接预览文件内容（默认最多 512KB）"""
    fp = get_output_file_path(task_id, path)
    if not fp or not fp.exists():
        raise HTTPException(404, "文件不存在")
    size = fp.stat().st_size
    if size > max_kb * 1024:
        raise HTTPException(413, f"文件过大（{size}B），请下载查看")
    return PlainTextResponse(fp.read_text(encoding="utf-8", errors="replace"))


# ---------- 记忆库 ----------
@router.get("/tasks/{task_id}/memory")
def api_list_memory(task_id: str):
    return {"files": list_memory_files(task_id)}


@router.get("/tasks/{task_id}/memory/{filename}")
def api_read_memory(task_id: str, filename: str):
    if filename not in MEMORY_FILES:
        raise HTTPException(404, "未知记忆文件")
    content = read_memory(task_id, filename)
    return {"filename": filename, "content": content}


@router.put("/tasks/{task_id}/memory/{filename}")
def api_write_memory(task_id: str, filename: str, body: MemoryUpdate):
    if filename not in MEMORY_FILES:
        raise HTTPException(404, "未知记忆文件")
    write_memory(task_id, filename, body.content)
    return {"ok": True}


# ---------- 配置（供前端刷新间隔等） ----------
@router.get("/config")
def api_config():
    return {
        "refresh_interval_seconds": settings.web_refresh_interval,
        "auth_required": bool(settings.web_password),
        "agent_interval_seconds": settings.agent_interval_seconds,
        "step_interval_seconds": settings.step_interval_seconds,
        "run_mode": get_run_mode(),
    }
