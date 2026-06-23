"""pytest 共享 fixture。"""

import sqlite3
from pathlib import Path

import pytest

from app.db import init_db
from app.schemas import ProjectCreation


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """隔离的临时 SQLite，避免触碰用户 data/。"""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("app.db.DB_PATH", db_path)
    monkeypatch.setattr("app.db.DATA_DIR", tmp_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    from app.services.project_updater import create_project

    now = "2026-06-23 12:00:00"
    create_project(
        conn,
        ProjectCreation(project_name="已知项目", latest_update="测试种子"),
        now,
    )
    conn.commit()
    conn.close()
    yield db_path
