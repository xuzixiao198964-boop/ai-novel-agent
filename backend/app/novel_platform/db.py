# -*- coding: utf-8 -*-
import hashlib
import sqlite3
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings


def _db_path() -> Path:
    p = settings.data_dir / "novel_platform.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS novels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                author TEXT DEFAULT '',
                intro TEXT DEFAULT '',
                cover_url TEXT DEFAULT '',
                category_id INTEGER,
                word_count INTEGER DEFAULT 0,
                status TEXT DEFAULT '连载',
                read_count INTEGER DEFAULT 0,
                favorite_count INTEGER DEFAULT 0,
                chapter_updated_at TEXT,
                source_task_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id INTEGER NOT NULL,
                chapter_no INTEGER NOT NULL,
                title TEXT DEFAULT '',
                content TEXT NOT NULL,
                word_count INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(novel_id, chapter_no)
            );
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                novel_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (user_id, novel_id)
            );
            CREATE TABLE IF NOT EXISTS reading_progress (
                user_id INTEGER NOT NULL,
                novel_id INTEGER NOT NULL,
                chapter_no INTEGER NOT NULL,
                scroll_offset INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, novel_id)
            );
            CREATE INDEX IF NOT EXISTS idx_novels_cat ON novels(category_id);
            CREATE INDEX IF NOT EXISTS idx_novels_read ON novels(read_count);
            CREATE INDEX IF NOT EXISTS idx_novels_upd ON novels(chapter_updated_at);
            """
        )
        cur = conn.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            cats = [
                ("xuanhuan", "玄幻", 1),
                ("yanqing", "言情", 2),
                ("dushi", "都市", 3),
                ("xuanyi", "悬疑", 4),
                ("kehuan", "科幻", 5),
            ]
            for slug, name, so in cats:
                conn.execute(
                    "INSERT INTO categories (slug, name, sort_order) VALUES (?,?,?)",
                    (slug, name, so),
                )
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()


def register_user(username: str, password: str) -> tuple[bool, str]:
    init_db()
    u = username.strip()
    if len(u) < 2 or len(u) > 32:
        return False, "用户名长度 2–32"
    if len(password) < 6:
        return False, "密码至少 6 位"
    salt = secrets.token_hex(16)
    ph = hash_password(password, salt)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?,?,?,?)",
            (u, ph, salt, datetime.now().isoformat()),
        )
        conn.commit()
        return True, "ok"
    except sqlite3.IntegrityError:
        return False, "用户名已存在"
    finally:
        conn.close()


def verify_user(username: str, password: str) -> Optional[dict]:
    init_db()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        if hash_password(password, d["salt"]) != d["password_hash"]:
            return None
        return {"id": d["id"], "username": d["username"]}
    finally:
        conn.close()


def _slugify(title: str, nid: int) -> str:
    import re

    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title.strip())[:40] or "novel"
    return f"{s}-{nid}"


def markdown_to_plain(text: str) -> str:
    import re

    t = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    t = re.sub(r"\*\*?|__|`", "", t)
    return t.strip()


def publish_from_task(task_id: str) -> dict[str, Any]:
    """从已完成任务的 output 导入小说站。"""
    from app.core.state import _task_dir, get_task_meta, get_output_file_path
    import json

    init_db()
    meta = get_task_meta(task_id)
    if not meta:
        raise ValueError("任务不存在")

    task_d = _task_dir(task_id)
    outline_p = task_d / "output" / "planner" / "outline.json"
    if not outline_p.exists():
        raise ValueError("无大纲，无法发布")

    data = json.loads(outline_p.read_text(encoding="utf-8"))
    chapters_outline = data.get("chapters") or []
    if not chapters_outline:
        raise ValueError("大纲无章节，无法发布")
    title = (meta.get("name") or "").strip() or "未命名"
    name_file = task_d / "output" / "planner" / "小说名.txt"
    if name_file.exists():
        t2 = name_file.read_text(encoding="utf-8", errors="replace").strip()
        if t2:
            title = t2

    conn = get_conn()
    try:
        ex = conn.execute("SELECT id, slug FROM novels WHERE source_task_id = ?", (task_id,)).fetchone()
        if ex:
            return {"ok": True, "novel_id": ex["id"], "slug": ex["slug"], "chapters": 0, "message": "该任务已发布过"}

        tmp_slug = f"import-{task_id[:12]}-{secrets.token_hex(3)}"
        conn.execute(
            """INSERT INTO novels (slug, title, author, intro, cover_url, category_id, word_count, status,
            read_count, favorite_count, chapter_updated_at, source_task_id, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tmp_slug,
                title,
                "本站作者",
                "",
                "",
                1,
                0,
                "完结",
                0,
                0,
                datetime.now().isoformat(),
                task_id,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        nid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        slug = _slugify(title, nid)
        conn.execute("UPDATE novels SET slug = ? WHERE id = ?", (slug, nid))

        total_words = 0
        now = datetime.now().isoformat()
        for i, ch in enumerate(chapters_outline, start=1):
            fp = get_output_file_path(task_id, f"final/ch_{i:02d}.md")
            if not fp or not fp.exists():
                fp2 = task_d / "output" / "final" / f"ch_{i:02d}.md"
                content = fp2.read_text(encoding="utf-8", errors="replace") if fp2.exists() else ""
            else:
                content = fp.read_text(encoding="utf-8", errors="replace")
            plain = markdown_to_plain(content) if content else "（本章暂无正文）"
            wc = len(plain)
            total_words += wc
            ct = (ch.get("title") if isinstance(ch, dict) else None) or f"第{i}章"
            conn.execute(
                """INSERT INTO chapters (novel_id, chapter_no, title, content, word_count, updated_at)
                VALUES (?,?,?,?,?,?)""",
                (nid, i, str(ct)[:200], plain, wc, now),
            )
        conn.execute(
            "UPDATE novels SET word_count = ?, chapter_updated_at = ? WHERE id = ?",
            (total_words, now, nid),
        )
        conn.commit()
        return {"ok": True, "novel_id": nid, "slug": slug, "chapters": len(chapters_outline)}
    finally:
        conn.close()
