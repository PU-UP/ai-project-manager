"""Step 10 独立验收缺口的生产路径回归测试。"""

import json

from app.db import get_connection
from app.models import PROJECT_ALIASES
from app.schemas import ProjectCreation
from app.services.apply_control import apply_raw_json
from app.services.project_updater import create_project, list_projects, match_project


def _seed_ai_customer() -> None:
    conn = get_connection()
    try:
        create_project(
            conn,
            ProjectCreation(project_name="AI客服", latest_update="原始记录"),
            "2026-06-23 12:00:00",
        )
        conn.commit()
    finally:
        conn.close()


def test_similar_name_cannot_target_any_write_operation(temp_db):
    _seed_ai_customer()
    payload = {
        "project_updates": [{"project_name": "AI", "latest_update": "不应写入"}],
        "project_memory_updates": [{
            "project_name": "AI",
            "validated_facts": ["不应写入"],
            "_provenance": [{"source_type": "user", "confirmation": "confirmed"}],
        }],
        "project_events": [{
            "project_name": "AI", "event_type": "note", "summary": "不应写入"
        }],
        "project_deletions": [{"project_name": "AI", "mode": "archive"}],
        "document_adds": [{"project_name": "AI", "title": "不应登记"}],
    }
    result = apply_raw_json(
        json.dumps(payload, ensure_ascii=False), user_input="step10", source="test"
    )
    assert result["ok"] is True
    assert result["updated"] == []
    assert result["memory_updated"] == []
    assert result["events"] == []
    assert result["archived"] == []
    assert result["documents_added"] == []

    conn = get_connection()
    try:
        project = next(p for p in list_projects(conn) if p["name"] == "AI客服")
        assert project["latest_update"] == "原始记录"
        assert project["status"] == "observe"
        assert project["validated_facts"] == []
        assert conn.execute(
            "SELECT COUNT(*) FROM project_events WHERE project_name = 'AI客服'"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM project_documents WHERE project_id = ?",
            (project["id"],),
        ).fetchone()[0] == 0
    finally:
        conn.close()


def test_exact_name_and_explicit_alias_still_match(temp_db):
    _seed_ai_customer()
    conn = get_connection()
    try:
        projects = list_projects(conn)
        assert match_project("ai客服", projects)["name"] == "AI客服"
        PROJECT_ALIASES["客服"] = "AI客服"
        try:
            assert match_project("客服", projects)["name"] == "AI客服"
        finally:
            PROJECT_ALIASES.pop("客服", None)
    finally:
        conn.close()


def test_ambiguous_normalized_name_is_reported_as_invalid(temp_db):
    conn = get_connection()
    try:
        create_project(
            conn,
            ProjectCreation(project_name="CaseName", latest_update="A"),
            "2026-06-23 12:00:00",
        )
        create_project(
            conn,
            ProjectCreation(project_name="casename", latest_update="B"),
            "2026-06-23 12:00:00",
        )
        conn.commit()
    finally:
        conn.close()

    result = apply_raw_json(
        json.dumps({
            "project_events": [{
                "project_name": "CASENAME", "event_type": "note", "summary": "不应写入"
            }]
        }, ensure_ascii=False),
        user_input="step10",
        source="test",
    )
    assert result["ok"] is True
    assert result["events"] == []
    assert result["invalid"]
    assert "匹配不唯一" in result["invalid"][0]["error"]


def test_risk_writes_require_confirmed_provenance(temp_db):
    risk_note = apply_raw_json(
        json.dumps({
            "project_updates": [{"project_name": "已知项目", "risk_note": "Agent 推断风险"}]
        }, ensure_ascii=False),
        user_input="step10",
        source="test",
    )
    assert risk_note["ok"] is False

    missing = apply_raw_json(
        json.dumps({
            "project_memory_updates": [{
                "project_name": "已知项目", "known_risks": ["Agent 推断风险"]
            }]
        }, ensure_ascii=False),
        user_input="step10",
        source="test",
    )
    assert missing["ok"] is False

    confirmed = apply_raw_json(
        json.dumps({
            "project_memory_updates": [{
                "project_name": "已知项目",
                "known_risks": ["用户确认风险"],
                "_risk_provenance": [{
                    "source_type": "user", "confirmation": "confirmed"
                }],
            }]
        }, ensure_ascii=False),
        user_input="step10",
        source="test",
    )
    assert confirmed["ok"] is True
    conn = get_connection()
    try:
        risk = list_projects(conn)[0]["known_risks"][0]
        assert risk["text"] == "用户确认风险"
        assert risk["source_type"] == "user"
        assert risk["confirmation"] == "confirmed"
    finally:
        conn.close()
