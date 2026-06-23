"""SQLite 连接与建表。"""

import json
import sqlite3
from pathlib import Path

from app.models import (
    CREATE_LOGS_TABLE,
    CREATE_PROJECT_DOCUMENTS_TABLE,
    CREATE_PROJECT_EVENTS_TABLE,
    CREATE_PROJECTS_TABLE,
    EVENT_PROVENANCE_COLUMNS,
    PROJECT_MEMORY_COLUMNS,
)
from app.provenance import (
    legacy_decision_provenance,
    legacy_fact_record,
    parse_validated_facts,
    serialize_validated_facts,
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


def migrate_event_provenance_columns(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(project_events)").fetchall()
    }
    for column, ddl in EVENT_PROVENANCE_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE project_events ADD COLUMN {column} {ddl}")


def migrate_provenance_data(conn: sqlite3.Connection) -> None:
    """将历史字符串事实与决策标为 legacy；幂等可重复执行。"""
    for row in conn.execute(
        "SELECT id, validated_facts, updated_at FROM projects"
    ).fetchall():
        raw = row["validated_facts"] or "[]"
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            parsed = []
        if not isinstance(parsed, list) or not parsed:
            continue
        if all(isinstance(item, str) for item in parsed):
            migrated = [
                legacy_fact_record(str(item), row["updated_at"] or "")
                for item in parsed
                if str(item).strip()
            ]
            conn.execute(
                "UPDATE projects SET validated_facts = ? WHERE id = ?",
                (serialize_validated_facts(migrated), row["id"]),
            )

    for row in conn.execute(
        """
        SELECT id, decision, decision_provenance, created_at
        FROM project_events
        WHERE decision != '' AND (decision_provenance IS NULL OR decision_provenance = '')
        """
    ).fetchall():
        prov = legacy_decision_provenance(row["created_at"] or "")
        conn.execute(
            "UPDATE project_events SET decision_provenance = ? WHERE id = ?",
            (json.dumps(prov, ensure_ascii=False), row["id"]),
        )


def init_db(conn: sqlite3.Connection | None = None) -> None:
    close = False
    if conn is None:
        conn = get_connection()
        close = True
    try:
        conn.executescript(
            CREATE_PROJECTS_TABLE
            + CREATE_LOGS_TABLE
            + CREATE_PROJECT_EVENTS_TABLE
            + CREATE_PROJECT_DOCUMENTS_TABLE
        )
        migrate_projects_table(conn)
        migrate_event_provenance_columns(conn)
        migrate_provenance_data(conn)
        conn.commit()
    finally:
        if close:
            conn.close()
