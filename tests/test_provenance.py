"""Provenance 迁移与持久化测试。"""

import json
import sqlite3

import pytest

from app.db import init_db
from app.provenance import legacy_fact_record, parse_validated_facts


@pytest.fixture
def legacy_facts_db(tmp_path, monkeypatch):
    """含字符串格式 validated_facts 的临时库。"""
    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr("app.db.DB_PATH", db_path)
    monkeypatch.setattr("app.db.DATA_DIR", tmp_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'observe',
            value_score INTEGER NOT NULL DEFAULT 3,
            risk_level TEXT NOT NULL DEFAULT 'medium',
            risk_note TEXT NOT NULL DEFAULT '',
            ai_delegation_level INTEGER NOT NULL DEFAULT 3,
            human_intervention_level INTEGER NOT NULL DEFAULT 3,
            control_action TEXT NOT NULL DEFAULT 'observe',
            control_action_note TEXT NOT NULL DEFAULT '',
            latest_update TEXT NOT NULL DEFAULT '',
            project_constraint TEXT NOT NULL DEFAULT '',
            origin TEXT NOT NULL DEFAULT '',
            current_goal TEXT NOT NULL DEFAULT '',
            progress_percent INTEGER NOT NULL DEFAULT 0,
            progress_note TEXT NOT NULL DEFAULT '',
            key_judgements TEXT NOT NULL DEFAULT '[]',
            validated_facts TEXT NOT NULL DEFAULT '[]',
            open_questions TEXT NOT NULL DEFAULT '[]',
            discussion_brief TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE project_events (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            project_name TEXT NOT NULL,
            event_type TEXT NOT NULL DEFAULT 'progress',
            summary TEXT NOT NULL,
            evidence TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL DEFAULT '',
            next_action TEXT NOT NULL DEFAULT '',
            happened_at TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE logs (
            id INTEGER PRIMARY KEY,
            user_input TEXT NOT NULL,
            ai_raw_output TEXT,
            parsed_summary TEXT,
            system_judgement TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        INSERT INTO projects (
            name, status, value_score, risk_level, validated_facts,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Legacy项目",
            "active",
            3,
            "medium",
            json.dumps(["旧事实 A", "旧事实 B"], ensure_ascii=False),
            "2026-01-01 00:00:00",
            "2026-06-01 00:00:00",
        ),
    )
    conn.execute(
        """
        INSERT INTO project_events (
            project_id, project_name, event_type, summary, decision, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (1, "Legacy项目", "decision", "历史决定", "继续观察", "2026-05-01 00:00:00"),
    )
    conn.commit()
    conn.close()
    return db_path


def test_init_db_migrates_legacy_string_facts_idempotent(legacy_facts_db):
    conn = sqlite3.connect(legacy_facts_db)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    row = conn.execute(
        "SELECT validated_facts FROM projects WHERE name = ?", ("Legacy项目",)
    ).fetchone()
    facts = parse_validated_facts(row["validated_facts"])
    assert len(facts) == 2
    assert all(f["confirmation"] == "legacy" for f in facts)
    assert facts[0]["text"] == "旧事实 A"
    assert facts[0]["recorded_at"] == "2026-06-01 00:00:00"

    init_db(conn)
    row2 = conn.execute(
        "SELECT validated_facts FROM projects WHERE name = ?", ("Legacy项目",)
    ).fetchone()
    facts2 = parse_validated_facts(row2["validated_facts"])
    assert facts2 == facts

    event = conn.execute(
        "SELECT decision_provenance FROM project_events WHERE decision != ''"
    ).fetchone()
    assert event["decision_provenance"]
    prov = json.loads(event["decision_provenance"])
    assert prov["confirmation"] == "legacy"

    init_db(conn)
    event2 = conn.execute(
        "SELECT decision_provenance FROM project_events WHERE decision != ''"
    ).fetchone()
    assert event2["decision_provenance"] == event["decision_provenance"]
    conn.close()


def test_parse_validated_facts_handles_structured_and_legacy():
    structured = [
        legacy_fact_record("x", "2026-06-01"),
        {"text": "y", "source_type": "user", "confirmation": "confirmed", "recorded_at": "t"},
    ]
    facts = parse_validated_facts(json.dumps(structured, ensure_ascii=False))
    assert len(facts) == 2
    assert facts[1]["source_type"] == "user"
