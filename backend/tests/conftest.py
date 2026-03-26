# -*- coding: utf-8 -*-
"""共享 fixtures：隔离 data_dir，避免污染真实 data/。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_in_memory_auth():
    """各测试间清空书架 / 小说站 token 缓存。"""
    import app.api.routes as api_routes
    import app.novel_platform.router as novel_router

    api_routes._BOOKSHELF_TOKENS.clear()
    novel_router._TOKENS.clear()
    yield
    api_routes._BOOKSHELF_TOKENS.clear()
    novel_router._TOKENS.clear()


@pytest.fixture
def client(monkeypatch, tmp_path):
    """FastAPI TestClient，数据目录指向临时路径。"""
    from app.core import config

    d = tmp_path / "data"
    m = tmp_path / "memory"
    d.mkdir(parents=True)
    m.mkdir(parents=True)
    monkeypatch.setattr(config.settings, "data_dir", d)
    monkeypatch.setattr(config.settings, "memory_dir", m)
    monkeypatch.setattr(config.settings, "web_password", "")
    monkeypatch.setattr(config.settings, "mock_llm", True)

    from app.main import app

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
