"""决策型 legacy 字段废弃测试（Step 8）。"""

import json
import sqlite3

import pytest

from app.agent_tools import _brief_context
from app.db import get_connection, init_db
from app.legacy_fields import project_for_core_export
from app.services.apply_control import build_context
from app.services.control_parser import parse_control_response
from app.services.project_updater import list_projects


def test_schema_rejects_value_score_in_project_update():
    raw = json.dumps(
        {
            "project_updates": [
                {
                    "project_name": "已知项目",
                    "value_score": 5,
                }
            ]
        },
        ensure_ascii=False,
    )
    parsed, err = parse_control_response(raw)
    assert parsed is None
    assert err is not None
    assert "value_score" in err


def test_schema_rejects_key_judgements_in_memory_update():
    raw = json.dumps(
        {
            "project_memory_updates": [
                {
                    "project_name": "已知项目",
                    "key_judgements": ["Agent 推断"],
                }
            ]
        },
        ensure_ascii=False,
    )
    parsed, err = parse_control_response(raw)
    assert parsed is None
    assert err is not None
    assert "key_judgements" in err


def test_schema_rejects_legacy_fields_in_project_creation():
    raw = json.dumps(
        {
            "project_creations": [
                {
                    "project_name": "新项目",
                    "control_action": "pause",
                }
            ]
        },
        ensure_ascii=False,
    )
    parsed, err = parse_control_response(raw)
    assert parsed is None
    assert "control_action" in (err or "")


def test_known_risks_memory_update_applies(temp_db):
    from app.services.apply_control import apply_raw_json

    raw = json.dumps(
        {
            "project_memory_updates": [
                {
                    "project_name": "已知项目",
                    "known_risks": ["用户确认：依赖外部 API 配额"],
                    "_risk_provenance": [
                        {"source_type": "user", "confirmation": "confirmed"}
                    ],
                }
            ]
        },
        ensure_ascii=False,
    )
    result = apply_raw_json(raw, user_input="测试", source="test")
    assert result["ok"] is True

    conn = get_connection()
    try:
        project = list_projects(conn)[0]
        assert project["known_risks"][0]["text"] == "用户确认：依赖外部 API 配额"
        assert project["known_risks"][0]["confirmation"] == "confirmed"
    finally:
        conn.close()


def test_brief_export_omits_decision_fields(temp_db):
    ctx = build_context()
    brief = _brief_context(ctx)
    project = brief["projects"][0]
    assert "value_score" not in project
    assert "control_action" not in project
    assert "risk_level" not in project
    memory = project.get("memory", {})
    assert "key_judgements" not in memory
    assert "progress_percent" not in memory


def test_brief_export_preserves_known_risk_provenance(temp_db):
    from app.services.apply_control import apply_raw_json

    result = apply_raw_json(
        json.dumps({
            "project_memory_updates": [{
                "project_name": "已知项目",
                "known_risks": ["外部 API 配额"],
                "_risk_provenance": [{
                    "source_type": "user",
                    "confirmation": "confirmed",
                    "source_ref": "用户原话",
                }],
            }]
        }, ensure_ascii=False),
        user_input="测试",
        source="test",
    )
    assert result["ok"] is True
    risk = _brief_context(build_context())["projects"][0]["memory"]["known_risks"][0]
    assert risk == {
        "text": "外部 API 配额",
        "source_type": "user",
        "confirmation": "confirmed",
        "source_ref": "用户原话",
    }


def test_core_export_preserves_legacy_block(temp_db):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE projects SET value_score = 2, control_action = 'pause' WHERE id = 1"
        )
        conn.commit()
        project = list_projects(conn)[0]
        core = project_for_core_export(project)
        assert core.get("value_score") is None
        assert core["legacy_decision_fields"]["value_score"] == 2
        assert core["legacy_decision_fields"]["control_action"] == "pause"
    finally:
        conn.close()


@pytest.fixture
def legacy_risk_db(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_risk.db"
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
            risk_note TEXT NOT NULL DEFAULT '历史风险说明',
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
        CREATE TABLE logs (id INTEGER PRIMARY KEY, user_input TEXT, created_at TEXT NOT NULL);
        CREATE TABLE project_events (
            id INTEGER PRIMARY KEY, project_name TEXT, summary TEXT, created_at TEXT
        );
        CREATE TABLE project_documents (
            id INTEGER PRIMARY KEY, project_id INTEGER, title TEXT, added_at TEXT, updated_at TEXT
        );
        """
    )
    conn.execute(
        """
        INSERT INTO projects (name, status, risk_note, created_at, updated_at)
        VALUES ('Legacy', 'active', '历史风险说明', '2026-01-01', '2026-01-01')
        """
    )
    conn.commit()
    conn.close()
    return db_path


def test_migrate_risk_note_to_known_risks_idempotent(legacy_risk_db):
    conn = sqlite3.connect(legacy_risk_db)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    row = conn.execute(
        "SELECT known_risks FROM projects WHERE name = 'Legacy'"
    ).fetchone()
    risks = json.loads(row["known_risks"])
    assert risks == [{
        "text": "历史风险说明",
        "source_type": "legacy",
        "source_ref": "",
        "confirmation": "legacy",
        "recorded_at": "",
    }]
    init_db(conn)
    row2 = conn.execute(
        "SELECT known_risks FROM projects WHERE name = 'Legacy'"
    ).fetchone()
    assert json.loads(row2["known_risks"]) == risks
    conn.close()
