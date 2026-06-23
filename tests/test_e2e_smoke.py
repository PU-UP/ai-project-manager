"""端到端 smoke：临时库完成创建、记录、文档、导出、归档。"""

import json
import sqlite3

import pytest

from app.db import get_connection, init_db
from app.services.apply_control import apply_raw_json, build_context
from app.services.document_index import list_documents
from app.services.project_updater import list_projects


@pytest.fixture
def e2e_db(tmp_path, monkeypatch):
    db_path = tmp_path / "e2e.db"
    monkeypatch.setattr("app.db.DB_PATH", db_path)
    monkeypatch.setattr("app.db.DATA_DIR", tmp_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    return db_path


def test_e2e_create_record_document_export_archive(e2e_db):
    create = json.dumps(
        {
            "project_creations": [
                {
                    "project_name": "E2E项目",
                    "status": "observe",
                    "latest_update": "端到端测试创建",
                }
            ]
        },
        ensure_ascii=False,
    )
    assert apply_raw_json(create, user_input="e2e", source="test")["ok"] is True

    event = json.dumps(
        {
            "project_events": [
                {
                    "project_name": "E2E项目",
                    "event_type": "note",
                    "summary": "首次进展记录",
                }
            ]
        },
        ensure_ascii=False,
    )
    assert apply_raw_json(event, user_input="e2e", source="test")["ok"] is True

    memory = json.dumps(
        {
            "project_memory_updates": [
                {
                    "project_name": "E2E项目",
                    "validated_facts": ["用户确认的目标已记录"],
                    "_provenance": [
                        {
                            "source_type": "user",
                            "confirmation": "confirmed",
                        }
                    ],
                }
            ],
            "document_adds": [
                {
                    "project_name": "E2E项目",
                    "title": "E2E 说明",
                    "summary": "事实性摘要",
                    "source_kind": "note",
                }
            ],
        },
        ensure_ascii=False,
    )
    result = apply_raw_json(memory, user_input="e2e", source="test")
    assert result["ok"] is True
    assert result["documents_added"]

    ctx = build_context()
    names = [p["name"] for p in ctx["projects"]]
    assert "E2E项目" in names
    e2e = next(p for p in ctx["projects"] if p["name"] == "E2E项目")
    assert e2e.get("validated_facts")
    assert "value_score" not in e2e

    conn = get_connection()
    try:
        project = next(p for p in list_projects(conn) if p["name"] == "E2E项目")
        docs = list_documents(conn, project_id=project["id"])
        doc_id = docs[0]["id"]
    finally:
        conn.close()

    archive_doc = json.dumps(
        {
            "document_archives": [
                {"project_name": "E2E项目", "document_id": doc_id, "reason": "e2e"}
            ]
        },
        ensure_ascii=False,
    )
    assert apply_raw_json(archive_doc, user_input="e2e", source="test")["ok"] is True

    archive_project = json.dumps(
        {
            "project_deletions": [
                {"project_name": "E2E项目", "mode": "archive", "reason": "e2e 完成"}
            ]
        },
        ensure_ascii=False,
    )
    assert apply_raw_json(archive_project, user_input="e2e", source="test")["ok"] is True

    conn = get_connection()
    try:
        project = next(p for p in list_projects(conn) if p["name"] == "E2E项目")
        assert project["status"] == "archived"
        doc = list_documents(conn, project_id=project["id"])[0]
        assert doc["status"] == "superseded"
    finally:
        conn.close()
