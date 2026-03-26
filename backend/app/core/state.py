# -*- coding: utf-8 -*-
"""任务状态、进度、日志的存储与查询，供网页端调用"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional
from enum import Enum
import threading

from app.core.config import settings


class AgentStatus(str, Enum):
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _state_dir() -> Path:
    d = settings.data_dir / "state"
    _ensure_dir(d)
    return d


def _task_dir(task_id: str) -> Path:
    d = settings.data_dir / "tasks" / task_id
    _ensure_dir(d)
    return d


_lock = threading.Lock()
# 由 pipeline 在加载时注册，供 Agent 长循环中检查是否被用户请求停止
_stop_flag_ref: Optional[threading.Event] = None


def register_stop_flag(flag: threading.Event) -> None:
    global _stop_flag_ref
    _stop_flag_ref = flag


def is_stop_requested() -> bool:
    """是否已请求停止当前流水线（供 Agent 在长循环中检查）"""
    return _stop_flag_ref is not None and _stop_flag_ref.is_set()


def get_current_task_id() -> Optional[str]:
    """获取当前运行中的任务 ID"""
    f = _state_dir() / "current_task.txt"
    if not f.exists():
        return None
    return f.read_text(encoding="utf-8").strip() or None


def set_current_task_id(task_id: Optional[str]) -> None:
    with _lock:
        f = _state_dir() / "current_task.txt"
        f.write_text(task_id or "", encoding="utf-8")


def get_auto_run() -> bool:
    """是否开启自动连续生成（当前任务结束后自动创建并启动下一本）。"""
    f = _state_dir() / "auto_run.txt"
    if not f.exists():
        return False
    return f.read_text(encoding="utf-8").strip() == "1"


def set_auto_run(enabled: bool) -> None:
    with _lock:
        f = _state_dir() / "auto_run.txt"
        f.write_text("1" if enabled else "0", encoding="utf-8")


def get_run_mode() -> str:
    """获取运行模式：test=测试(6章) / prod=正式(按配置)"""
    f = _state_dir() / "run_mode.txt"
    if not f.exists():
        return "prod"
    mode = f.read_text(encoding="utf-8").strip().lower()
    return "test" if mode == "test" else "prod"


def set_run_mode(mode: str) -> str:
    """设置运行模式，返回生效模式。"""
    m = (mode or "").strip().lower()
    final = "test" if m == "test" else "prod"
    with _lock:
        f = _state_dir() / "run_mode.txt"
        f.write_text(final, encoding="utf-8")
    return final


def get_test_mode_chapters(default_value: int = 6) -> int:
    """获取测试模式当前章节数（默认 6）。"""
    f = _state_dir() / "test_mode_chapters.txt"
    if not f.exists():
        return max(1, int(default_value))
    try:
        v = int(f.read_text(encoding="utf-8").strip())
        return max(1, v)
    except Exception:
        return max(1, int(default_value))


def set_test_mode_chapters(chapters: int) -> int:
    """设置测试模式章节数，返回生效值。"""
    v = max(1, int(chapters))
    with _lock:
        f = _state_dir() / "test_mode_chapters.txt"
        f.write_text(str(v), encoding="utf-8")
    return v


def list_tasks() -> list[dict]:
    """列出所有任务"""
    purge_old_completed_tasks()
    tasks_dir = settings.data_dir / "tasks"
    if not tasks_dir.exists():
        return []
    out = []
    for p in tasks_dir.iterdir():
        if not p.is_dir():
            continue
        meta_file = p / "meta.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            meta["task_id"] = p.name
            out.append(meta)
        except Exception:
            pass
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return out


def delete_task(task_id: str) -> bool:
    """删除指定任务（目录及 meta）。若该任务正在运行则不允许删除，返回 False。"""
    import shutil
    if get_current_task_id() == task_id:
        # 如果用户已请求停止，则允许删除“正在停止中的任务”（避免 UI 反复 409 Conflict）
        try:
            if is_stop_requested():
                return True
        except Exception:
            pass
        return False
    task_d = settings.data_dir / "tasks" / task_id
    if not task_d.exists() or not task_d.is_dir():
        return False
    shutil.rmtree(task_d, ignore_errors=True)
    return True


def clear_all_tasks() -> list[str]:
    """清空所有任务（含已跑通），返回被删除的 task_id 列表。用于重新测试。"""
    import shutil
    tasks_dir = settings.data_dir / "tasks"
    state_dir = settings.data_dir / "state"
    current_task_file = state_dir / "current_task.txt"
    removed: list[str] = []
    if tasks_dir.exists():
        for p in tasks_dir.iterdir():
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed.append(p.name)
    if current_task_file.exists():
        current_task_file.write_text("", encoding="utf-8")
    return removed


def create_task(name: str = "新小说任务") -> str:
    """创建新任务，返回 task_id"""
    import uuid
    purge_old_completed_tasks()
    task_id = str(uuid.uuid4())[:8]
    task_d = _task_dir(task_id)
    meta = {
        "task_id": task_id,
        "name": name,
        "status": TaskStatus.DRAFT.value,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    (task_d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return task_id


def get_task_meta(task_id: str) -> Optional[dict]:
    meta_file = settings.data_dir / "tasks" / task_id / "meta.json"
    if not meta_file.exists():
        return None
    return json.loads(meta_file.read_text(encoding="utf-8"))


def update_task_meta(task_id: str, **kwargs: Any) -> None:
    meta = get_task_meta(task_id) or {}
    meta.update(kwargs)
    meta["updated_at"] = datetime.now().isoformat()
    task_d = _task_dir(task_id)
    (task_d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def get_agent_progress(task_id: str, agent_name: str) -> dict:
    """获取某任务下某 Agent 的进度（供网页展示）"""
    f = _task_dir(task_id) / "progress" / f"{agent_name}.json"
    if not f.exists():
        return {"status": AgentStatus.READY.value, "progress_percent": 0, "message": "就绪"}
    return json.loads(f.read_text(encoding="utf-8"))


def set_agent_progress(task_id: str, agent_name: str, status: str, progress_percent: float = 0, message: str = "", extra: Optional[dict] = None) -> None:
    """写入 Agent 进度"""
    d = _task_dir(task_id) / "progress"
    _ensure_dir(d)
    data = {
        "agent": agent_name,
        "status": status,
        "progress_percent": progress_percent,
        "message": message,
        "updated_at": datetime.now().isoformat(),
    }
    if extra:
        data.update(extra)
    with _lock:
        (d / f"{agent_name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_agent_logs(task_id: str, agent_name: str, limit: int = 200) -> list[dict]:
    """获取某 Agent 的日志列表"""
    f = _task_dir(task_id) / "logs" / f"{agent_name}.jsonl"
    if not f.exists():
        return []
    lines = f.read_text(encoding="utf-8").strip().split("\n")
    out = []
    for line in reversed(lines[-limit:]):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    out.reverse()
    return out


def append_agent_log(task_id: str, agent_name: str, level: str, message: str, detail: Optional[dict] = None) -> None:
    """追加一条日志"""
    d = _task_dir(task_id) / "logs"
    _ensure_dir(d)
    record = {
        "time": datetime.now().isoformat(),
        "level": level,
        "message": message,
    }
    if detail:
        record["detail"] = detail
    with _lock:
        with open(d / f"{agent_name}.jsonl", "a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_task_progress_summary(task_id: str) -> dict:
    """总进度：各 Agent 状态汇总（不包含 ScorerAgent 显示）"""
    agents = ["TrendAgent", "StyleAgent", "PlannerAgent", "WriterAgent", "PolishAgent", "AuditorAgent", "ReviserAgent"]
    summary = {}
    for name in agents:
        summary[name] = get_agent_progress(task_id, name)
    return summary


# Agent 与产出目录对应关系（用于“按 Agent 展示结果”，不包含 ScorerAgent）
AGENT_OUTPUT_PREFIXES = {
    "TrendAgent": "trend",
    "StyleAgent": "style",
    "PlannerAgent": "planner",
    "WriterAgent": "chapters",
    "PolishAgent": "chapters_polished",
    "AuditorAgent": "audit",
    "ReviserAgent": "final",
}


def list_output_files(task_id: str) -> list[dict]:
    """列出某任务下的产出文件（报告、正文、定稿等）"""
    task_d = _task_dir(task_id)
    files_d = task_d / "output"
    if not files_d.exists():
        return []
    out = []
    for f in files_d.rglob("*"):
        if f.is_file():
            rel = f.relative_to(files_d)
            out.append({
                "path": str(rel).replace("\\", "/"),
                "size": f.stat().st_size,
                "mtime": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return out


def list_output_files_by_agent(task_id: str) -> dict[str, list[dict]]:
    """按 Agent 分组返回产出文件，供前端“点击哪个 Agent 展示哪个结果”"""
    files = list_output_files(task_id)
    by_agent: dict[str, list[dict]] = {name: [] for name in AGENT_OUTPUT_PREFIXES}
    for f in files:
        path = f["path"]
        top = path.split("/")[0] if "/" in path else path.split("\\")[0]
        for agent_name, prefix in AGENT_OUTPUT_PREFIXES.items():
            if top == prefix:
                by_agent[agent_name].append(f)
                break
    return by_agent


def get_output_file_path(task_id: str, relative_path: str) -> Optional[Path]:
    """获取产出文件的真实路径（用于下载）"""
    task_d = _task_dir(task_id)
    full = (task_d / "output" / relative_path).resolve()
    if not str(full).startswith(str(task_d.resolve())):
        return None
    return full if full.is_file() else None


def get_used_character_names(exclude_task_id: str) -> list[str]:
    """从其他任务的策划案/人设中提取已用人物名，避免与本任务重复。"""
    import re
    tasks_dir = settings.data_dir / "tasks"
    if not tasks_dir.exists():
        return []
    used: list[str] = []
    for p in tasks_dir.iterdir():
        if not p.is_dir() or p.name == exclude_task_id:
            continue
        plan_file = p / "output" / "planner" / "策划案.md"
        if not plan_file.exists():
            continue
        try:
            text = plan_file.read_text(encoding="utf-8", errors="replace")
            for line in text.split("\n"):
                line = line.strip()
                if not line or len(line) > 200:
                    continue
                for m in re.finditer(r"[主角配角人物]?[：:]\s*([^\s，,、。；;：:\n]{2,4})", line):
                    name = m.group(1).strip()
                    if re.fullmatch(r"[\u4e00-\u9fff]+", name) and 2 <= len(name) <= 4:
                        used.append(name)
                for m in re.finditer(r"[\u4e00-\u9fff]{2,4}(?=\s*[：:]\s*身份|目标|关系)", line):
                    used.append(m.group(0))
        except Exception:
            pass
    return list(dict.fromkeys(used))


def list_bookshelf_tasks() -> list[dict]:
    """书架：优先展示已同步到小说平台的作品；任务被清理后仍可展示。"""
    out: list[dict] = []
    seen_task_ids: set[str] = set()
    try:
        from app.novel_platform import db as novel_db

        novel_db.init_db()
        conn = novel_db.get_conn()
        try:
            rows = conn.execute(
                "SELECT id, title, source_task_id, created_at FROM novels ORDER BY datetime(created_at) DESC, id DESC"
            ).fetchall()
            for r in rows:
                source_tid = (r["source_task_id"] or "").strip() if r["source_task_id"] else ""
                task_meta = get_task_meta(source_tid) if source_tid else {}
                genre_type = (task_meta or {}).get("genre_type") or "男频"
                ch_cnt_row = conn.execute(
                    "SELECT COUNT(*) AS c FROM chapters WHERE novel_id = ?",
                    (r["id"],),
                ).fetchone()
                chapter_count = int(ch_cnt_row["c"]) if ch_cnt_row else 0
                task_id = source_tid or f"novel:{r['id']}"
                seen_task_ids.add(task_id)
                out.append({
                    "task_id": task_id,
                    "name": (task_meta or {}).get("name") or task_id,
                    "title": r["title"] or (task_meta or {}).get("name") or task_id,
                    "chapter_count": chapter_count,
                    "created_at": r["created_at"] or "",
                    "genre_type": genre_type,
                })
        finally:
            conn.close()
    except Exception:
        pass

    # 兜底：平台未同步前，仍展示“已完结且有成书”的任务
    tasks = [t for t in list_tasks() if t.get("status") == TaskStatus.COMPLETED.value]
    for t in tasks:
        tid = t.get("task_id")
        if not tid or tid in seen_task_ids:
            continue
        fp = get_output_file_path(tid, "final/成书_含目录可跳转.md")
        if not fp or not fp.exists():
            continue
        toc_data = get_novel_toc_only(tid)
        if not toc_data:
            continue
        out.append({
            "task_id": tid,
            "name": t.get("name") or tid,
            "title": toc_data.get("title") or t.get("name") or tid,
            "chapter_count": len(toc_data.get("toc") or []),
            "created_at": t.get("created_at", ""),
            "genre_type": t.get("genre_type") or "男频",
        })
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return out


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def purge_old_completed_tasks(retention_hours: int = 24) -> list[str]:
    """自动清理已完成且超过保留期的任务；尽量先同步到小说平台。"""
    if retention_hours <= 0:
        return []
    tasks_dir = settings.data_dir / "tasks"
    if not tasks_dir.exists():
        return []
    now = datetime.now()
    cutoff = now - timedelta(hours=retention_hours)
    current_tid = get_current_task_id()
    removed: list[str] = []
    import shutil
    for p in tasks_dir.iterdir():
        if not p.is_dir():
            continue
        tid = p.name
        if tid == current_tid:
            continue
        meta_file = p / "meta.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if meta.get("status") != TaskStatus.COMPLETED.value:
            continue
        done_at = _parse_dt(meta.get("updated_at")) or _parse_dt(meta.get("created_at"))
        if not done_at or done_at > cutoff:
            continue
        # 删除前尽量同步到小说平台，确保“任务清理后书架仍可读”
        try:
            from app.novel_platform.db import publish_from_task

            publish_from_task(tid)
        except Exception:
            pass
        shutil.rmtree(p, ignore_errors=True)
        removed.append(tid)
    return removed


def sync_completed_tasks_to_platform(limit: int = 100) -> list[str]:
    """将已完成但尚未标记同步成功的任务补同步到小说平台。"""
    tasks_dir = settings.data_dir / "tasks"
    if not tasks_dir.exists():
        return []
    synced: list[str] = []
    checked = 0
    for p in tasks_dir.iterdir():
        if checked >= max(1, int(limit)):
            break
        if not p.is_dir():
            continue
        checked += 1
        tid = p.name
        meta = get_task_meta(tid) or {}
        if meta.get("status") != TaskStatus.COMPLETED.value:
            continue
        if meta.get("platform_sync_ok") is True:
            continue
        try:
            from app.novel_platform.db import publish_from_task

            pub = publish_from_task(tid)
            update_task_meta(
                tid,
                platform_sync_ok=True,
                platform_novel_id=pub.get("novel_id"),
                platform_slug=pub.get("slug"),
                platform_sync_message=pub.get("message") or "ok",
            )
            synced.append(tid)
        except Exception as e:
            update_task_meta(tid, platform_sync_ok=False, platform_sync_error=str(e))
    return synced


def get_novel_toc_only(task_id: str) -> Optional[dict]:
    """目录页：优先用 planner/outline.json 输出完整目录；标题优先取成书标题。"""
    task_d = _task_dir(task_id)

    # 标题：优先取成书标题，否则用任务名
    title = None
    fp = get_output_file_path(task_id, "final/成书_含目录可跳转.md")
    if fp and fp.exists():
        try:
            for line in fp.read_text(encoding="utf-8", errors="replace").split("\n")[:50]:
                s = line.strip()
                if s.startswith("# ") and not s.startswith("## "):
                    title = s[2:].strip()
                    break
        except Exception:
            pass
    if not title:
        meta = get_task_meta(task_id) or {}
        title = meta.get("name") or task_id

    # 目录：优先从 outline.json 读（支持 >200 且不依赖成书正文数量）
    outline_p = task_d / "output" / "planner" / "outline.json"
    toc: list[dict] = []
    if outline_p.exists():
        try:
            data = json.loads(outline_p.read_text(encoding="utf-8"))
            chs = data.get("chapters") or []
            if isinstance(chs, list):
                for i, ch in enumerate(chs):
                    label = ""
                    if isinstance(ch, dict):
                        label = ch.get("title") or ""
                    if not label:
                        label = f"第{i+1}章"
                    toc.append({"id": f"chapter-{i+1:02d}", "label": label})
        except Exception:
            toc = []

    # 兜底：若 outline 不存在且成书存在，则解析成书目录
    if not toc and fp and fp.exists():
        try:
            lines = fp.read_text(encoding="utf-8", errors="replace").split("\n")
            for i, line in enumerate(lines):
                s = line.strip()
                if s == "## 目录":
                    j = i + 1
                    while j < len(lines):
                        l = lines[j].strip()
                        if l.startswith("##"):
                            break
                        if l.startswith("- [") and "](#" in l:
                            try:
                                label = l[l.index("[") + 1 : l.index("]")]
                                anchor = l[l.index("(#") + 2 : l.index(")")]
                                toc.append({"id": anchor, "label": label})
                            except ValueError:
                                pass
                        j += 1
                    break
        except Exception:
            pass

    if toc:
        return {"title": title, "toc": toc, "chapter_count": len(toc)}

    # 任务已被清理时：回退到小说平台（source_task_id）
    try:
        from app.novel_platform import db as novel_db

        novel_db.init_db()
        conn = novel_db.get_conn()
        try:
            n = conn.execute(
                "SELECT id, title FROM novels WHERE source_task_id = ? ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
            if not n:
                return None
            chs = conn.execute(
                "SELECT chapter_no, title FROM chapters WHERE novel_id = ? ORDER BY chapter_no",
                (n["id"],),
            ).fetchall()
            toc = [{"id": f"chapter-{int(c['chapter_no']):02d}", "label": c["title"] or f"第{int(c['chapter_no'])}章"} for c in chs]
            return {"title": n["title"] or task_id, "toc": toc, "chapter_count": len(toc)}
        finally:
            conn.close()
    except Exception:
        return None


def get_chapter_content(task_id: str, chapter_index: int) -> Optional[dict]:
    """按章节下标（从 0 起）取单章内容，供书架阅读页；优先从 final/ch_XX.md 读取"""
    task_d = _task_dir(task_id)
    one_based = chapter_index + 1
    ch_path = task_d / "output" / "final" / f"ch_{one_based:02d}.md"
    if ch_path.exists():
        content = ch_path.read_text(encoding="utf-8", errors="replace")
        toc_data = get_novel_toc_only(task_id)
        toc = toc_data.get("toc") or []
        label = toc[chapter_index].get("label", f"第{one_based}章") if chapter_index < len(toc) else f"第{one_based}章"
        return {
            "title": label,
            "content": content,
            "index": chapter_index,
            "prev_index": chapter_index - 1 if chapter_index > 0 else None,
            "next_index": chapter_index + 1 if chapter_index < len(toc) - 1 else None,
            "total": len(toc),
        }
    # 若目录存在但该章正文未生成，返回空内容（前端会提示“暂不可用”）
    toc_data = get_novel_toc_only(task_id)
    toc = toc_data.get("toc") or []
    if chapter_index < len(toc):
        label = toc[chapter_index].get("label", f"第{one_based}章")
        return {
            "title": label,
            "content": "",
            "index": chapter_index,
            "prev_index": chapter_index - 1 if chapter_index > 0 else None,
            "next_index": chapter_index + 1 if chapter_index < len(toc) - 1 else None,
            "total": len(toc),
        }
    # 回退：从成书大文件中解析该章
    full = get_novel_toc_and_chapters(task_id)
    if not full or not full.get("chapters") or chapter_index >= len(full["chapters"]):
        # 再回退：任务已清理时，从小说平台按 source_task_id 读取
        try:
            from app.novel_platform import db as novel_db

            novel_db.init_db()
            conn = novel_db.get_conn()
            try:
                n = conn.execute(
                    "SELECT id, title FROM novels WHERE source_task_id = ? ORDER BY id DESC LIMIT 1",
                    (task_id,),
                ).fetchone()
                if not n:
                    return None
                one_based = chapter_index + 1
                ch = conn.execute(
                    "SELECT chapter_no, title, content FROM chapters WHERE novel_id = ? AND chapter_no = ?",
                    (n["id"], one_based),
                ).fetchone()
                if not ch:
                    return None
                total = conn.execute(
                    "SELECT COUNT(*) AS c FROM chapters WHERE novel_id = ?",
                    (n["id"],),
                ).fetchone()
                total_n = int(total["c"]) if total else 0
                return {
                    "title": ch["title"] or f"第{one_based}章",
                    "content": ch["content"] or "",
                    "index": chapter_index,
                    "prev_index": chapter_index - 1 if chapter_index > 0 else None,
                    "next_index": chapter_index + 1 if chapter_index < total_n - 1 else None,
                    "total": total_n,
                }
            finally:
                conn.close()
        except Exception:
            return None
    ch = full["chapters"][chapter_index]
    toc = full.get("toc") or []
    return {
        "title": ch.get("title", f"第{chapter_index+1}章"),
        "content": ch.get("content", ""),
        "index": chapter_index,
        "prev_index": chapter_index - 1 if chapter_index > 0 else None,
        "next_index": chapter_index + 1 if chapter_index < len(toc) - 1 else None,
        "total": len(toc),
    }


def get_novel_toc_and_chapters(task_id: str) -> Optional[dict]:
    """解析成书 Markdown，返回 { title, toc: [{id, label}], chapters: [{id, title, content}] }"""
    fp = get_output_file_path(task_id, "final/成书_含目录可跳转.md")
    if not fp or not fp.exists():
        return None
    text = fp.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    title = "自动生成小说"
    toc: list[dict] = []
    chapters: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            i += 1
            continue
        if line.strip() == "## 目录":
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith("##"):
                    break
                l = lines[i].strip()
                if l.startswith("- [") and "](#" in l:
                    try:
                        label = l[l.index("[") + 1 : l.index("]")]
                        anchor = l[l.index("(#") + 2 : l.index(")")]
                        toc.append({"id": anchor, "label": label})
                    except ValueError:
                        pass
                i += 1
            continue
        if line.strip() == "## 正文":
            i += 1
            break
        if line.strip().startswith("### ") and not line.strip().startswith("#### "):
            break
        i += 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("### ") and not line.startswith("#### "):
            chap_title = line[4:].strip()
            anchor = ""
            i += 1
            if i < len(lines) and "<a id=" in lines[i]:
                try:
                    a = lines[i]
                    start = a.index('id="') + 4
                    end = a.index('"', start)
                    anchor = a[start:end]
                except (ValueError, IndexError):
                    pass
                i += 1
            content_lines: list[str] = []
            while i < len(lines):
                if lines[i].startswith("### ") and not lines[i].startswith("#### "):
                    break
                content_lines.append(lines[i])
                i += 1
            content = "\n".join(content_lines).strip()
            chapters.append({"id": anchor or f"chapter-{len(chapters)+1:02d}", "title": chap_title, "content": content})
            continue
        i += 1
    return {"title": title, "toc": toc, "chapters": chapters}


def write_output_file(task_id: str, relative_path: str, content: str) -> Path:
    """写入产出文件"""
    task_d = _task_dir(task_id)
    out_d = task_d / "output"
    _ensure_dir(out_d)
    fp = out_d / relative_path
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")
    return fp


def append_output_file(task_id: str, relative_path: str, line: str) -> Path:
    """追加一行到产出文件（用于审核日志等，随任务消亡）"""
    task_d = _task_dir(task_id)
    out_d = task_d / "output"
    _ensure_dir(out_d)
    fp = out_d / relative_path
    fp.parent.mkdir(parents=True, exist_ok=True)
    with open(fp, "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")
    return fp
