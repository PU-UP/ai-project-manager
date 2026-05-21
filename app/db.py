"""SQLite 连接与建表。"""

import sqlite3
from pathlib import Path

from app.models import (
    CREATE_LOGS_TABLE,
    CREATE_PROJECT_EVENTS_TABLE,
    CREATE_PROJECTS_TABLE,
    PROJECT_MEMORY_COLUMNS,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "project_control_panel.db"
LOGS_DIR = ROOT_DIR / "logs"
INTERACTIONS_JSONL = LOGS_DIR / "interactions.jsonl"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def migrate_projects_table(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(projects)").fetchall()
    }
    for column, ddl in PROJECT_MEMORY_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE projects ADD COLUMN {column} {ddl}")


def init_db(conn: sqlite3.Connection | None = None) -> None:
    close = False
    if conn is None:
        conn = get_connection()
        close = True
    try:
        conn.executescript(
            CREATE_PROJECTS_TABLE + CREATE_LOGS_TABLE + CREATE_PROJECT_EVENTS_TABLE
        )
        migrate_projects_table(conn)
        conn.commit()
    finally:
        if close:
            conn.close()
