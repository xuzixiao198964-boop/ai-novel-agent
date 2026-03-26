# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Optional

import secrets
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel

from app.novel_platform import db as novel_db

router = APIRouter(tags=["novel-platform"])

_TOKENS: dict[str, dict] = {}


def _auth_user(authorization: Optional[str]) -> Optional[dict]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    rec = _TOKENS.get(token)
    if not rec:
        return None
    if datetime.now() > rec.get("exp", datetime.min):
        _TOKENS.pop(token, None)
        return None
    return rec


class RegisterBody(BaseModel):
    username: str
    password: str


class LoginBody(BaseModel):
    username: str
    password: str


class ProgressBody(BaseModel):
    novel_id: int
    chapter_no: int
    scroll_offset: int = 0


@router.get("/categories")
def list_categories():
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, slug, name, sort_order FROM categories ORDER BY sort_order, id"
        ).fetchall()
        return {"categories": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/novels")
def list_novels(
    category: Optional[str] = None,
    sort: str = Query("hot", description="hot|update|words"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
):
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        where = "1=1"
        args: list = []
        if category:
            cat = conn.execute("SELECT id FROM categories WHERE slug = ?", (category,)).fetchone()
            if cat:
                where += " AND category_id = ?"
                args.append(cat["id"])
        order = "read_count DESC"
        if sort == "update":
            order = "datetime(COALESCE(chapter_updated_at, '1970-01-01')) DESC"
        elif sort == "words":
            order = "word_count DESC"
        off = (page - 1) * per_page
        sql = f"""SELECT n.*, c.name as category_name FROM novels n
        LEFT JOIN categories c ON c.id = n.category_id
        WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?"""
        args.extend([per_page, off])
        rows = conn.execute(sql, args).fetchall()
        total = conn.execute(f"SELECT COUNT(*) FROM novels WHERE {where}", args[:-2]).fetchone()[0]
        return {"total": total, "page": page, "per_page": per_page, "novels": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/novels/by-slug/{slug}")
def novel_detail(slug: str):
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        row = conn.execute(
            """SELECT n.*, c.name as category_name, c.slug as category_slug
            FROM novels n LEFT JOIN categories c ON c.id = n.category_id
            WHERE n.slug = ?""",
            (slug,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "小说不存在")
        n = dict(row)
        chs = conn.execute(
            "SELECT chapter_no, title, word_count, updated_at FROM chapters WHERE novel_id = ? ORDER BY chapter_no",
            (n["id"],),
        ).fetchall()
        n["chapters"] = [dict(r) for r in chs]
        return n
    finally:
        conn.close()


@router.get("/novels/by-slug/{slug}/chapter/{chapter_no:int}")
def read_chapter(slug: str, chapter_no: int):
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        n = conn.execute("SELECT id, title FROM novels WHERE slug = ?", (slug,)).fetchone()
        if not n:
            raise HTTPException(404, "小说不存在")
        conn.execute(
            "UPDATE novels SET read_count = read_count + 1 WHERE id = ?", (n["id"],)
        )
        ch = conn.execute(
            "SELECT * FROM chapters WHERE novel_id = ? AND chapter_no = ?",
            (n["id"], chapter_no),
        ).fetchone()
        if not ch:
            raise HTTPException(404, "章节不存在")
        conn.commit()
        prev_row = conn.execute(
            "SELECT chapter_no FROM chapters WHERE novel_id = ? AND chapter_no < ? ORDER BY chapter_no DESC LIMIT 1",
            (n["id"], chapter_no),
        ).fetchone()
        next_row = conn.execute(
            "SELECT chapter_no FROM chapters WHERE novel_id = ? AND chapter_no > ? ORDER BY chapter_no ASC LIMIT 1",
            (n["id"], chapter_no),
        ).fetchone()
        d = dict(ch)
        d["novel_id"] = n["id"]
        d["prev_chapter"] = prev_row["chapter_no"] if prev_row else None
        d["next_chapter"] = next_row["chapter_no"] if next_row else None
        d["novel_title"] = n["title"]
        return d
    finally:
        conn.close()


@router.get("/search")
def search(q: str = "", page: int = 1, per_page: int = 20):
    novel_db.init_db()
    if not q.strip():
        return {"total": 0, "novels": [], "message": "未找到相关小说"}
    conn = novel_db.get_conn()
    try:
        like = f"%{q.strip()}%"
        off = (page - 1) * per_page
        rows = conn.execute(
            """SELECT * FROM novels WHERE title LIKE ? OR author LIKE ? ORDER BY read_count DESC LIMIT ? OFFSET ?""",
            (like, like, per_page, off),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM novels WHERE title LIKE ? OR author LIKE ?",
            (like, like),
        ).fetchone()[0]
        if total == 0:
            return {"total": 0, "novels": [], "message": "未找到相关小说"}
        return {"total": total, "page": page, "novels": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("/auth/register")
def register(body: RegisterBody):
    ok, msg = novel_db.register_user(body.username, body.password)
    if not ok:
        raise HTTPException(400, msg)
    return {"ok": True, "message": "注册成功"}


@router.post("/auth/login")
def login(body: LoginBody):
    u = novel_db.verify_user(body.username, body.password)
    if not u:
        raise HTTPException(401, "用户名或密码错误")
    token = secrets.token_hex(24)
    _TOKENS[token] = {"user_id": u["id"], "username": u["username"], "exp": datetime.now() + timedelta(days=14)}
    return {"token": token, "user": u}


@router.get("/me")
def me(authorization: Optional[str] = Header(None)):
    rec = _auth_user(authorization)
    if not rec:
        raise HTTPException(401, "需要登录")
    return {"user": {"id": rec["user_id"], "username": rec["username"]}}


@router.post("/novels/{novel_id:int}/favorite")
def add_favorite(novel_id: int, authorization: Optional[str] = Header(None)):
    rec = _auth_user(authorization)
    if not rec:
        raise HTTPException(401, "需要登录")
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (user_id, novel_id, created_at) VALUES (?,?,?)",
            (rec["user_id"], novel_id, datetime.now().isoformat()),
        )
        conn.execute(
            "UPDATE novels SET favorite_count = favorite_count + 1 WHERE id = ? AND (SELECT changes()) = 1",
            (novel_id,),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/novels/{novel_id:int}/favorite")
def remove_favorite(novel_id: int, authorization: Optional[str] = Header(None)):
    rec = _auth_user(authorization)
    if not rec:
        raise HTTPException(401, "需要登录")
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        r = conn.execute(
            "DELETE FROM favorites WHERE user_id = ? AND novel_id = ?",
            (rec["user_id"], novel_id),
        ).rowcount
        if r:
            conn.execute(
                "UPDATE novels SET favorite_count = CASE WHEN favorite_count > 0 THEN favorite_count - 1 ELSE 0 END WHERE id = ?",
                (novel_id,),
            )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/me/favorites")
def my_favorites(authorization: Optional[str] = Header(None)):
    rec = _auth_user(authorization)
    if not rec:
        raise HTTPException(401, "需要登录")
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        rows = conn.execute(
            """SELECT n.* FROM novels n
            JOIN favorites f ON f.novel_id = n.id
            WHERE f.user_id = ? ORDER BY f.created_at DESC""",
            (rec["user_id"],),
        ).fetchall()
        return {"novels": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("/me/progress")
def save_progress(body: ProgressBody, authorization: Optional[str] = Header(None)):
    rec = _auth_user(authorization)
    if not rec:
        raise HTTPException(401, "需要登录")
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        conn.execute(
            """INSERT INTO reading_progress (user_id, novel_id, chapter_no, scroll_offset, updated_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(user_id, novel_id) DO UPDATE SET
            chapter_no=excluded.chapter_no, scroll_offset=excluded.scroll_offset, updated_at=excluded.updated_at""",
            (rec["user_id"], body.novel_id, body.chapter_no, body.scroll_offset, datetime.now().isoformat()),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/me/history")
def my_history(authorization: Optional[str] = Header(None)):
    rec = _auth_user(authorization)
    if not rec:
        raise HTTPException(401, "需要登录")
    novel_db.init_db()
    conn = novel_db.get_conn()
    try:
        rows = conn.execute(
            """SELECT n.*, p.chapter_no, p.scroll_offset, p.updated_at as read_at
            FROM reading_progress p JOIN novels n ON n.id = p.novel_id
            WHERE p.user_id = ? ORDER BY p.updated_at DESC LIMIT 50""",
            (rec["user_id"],),
        ).fetchall()
        return {"items": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("/publish/{task_id}")
def publish_task(task_id: str):
    try:
        return novel_db.publish_from_task(task_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
