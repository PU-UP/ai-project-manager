"""项目文档索引 CRUD / 关联 / 归档测试。"""

import json

from app.db import get_connection, init_db
from app.services.apply_control import apply_raw_json
from app.services.control_parser import parse_control_response
from app.services.document_index import assess_source_uri, list_documents


def _document_add_payload(title: str = "测试文档", source_uri: str = "") -> dict:
    return {
        "document_adds": [
            {
                "project_name": "已知项目",
                "title": title,
                "document_type": "meeting_notes",
                "source_uri": source_uri,
                "source_kind": "file",
                "summary": "2026-06-20 会议：预算上限 5 万。",
                "tags": ["会议纪要"],
                "version_or_date": "2026-06-20",
            }
        ]
    }


def test_document_table_created_on_init_db(temp_db):
    conn = get_connection()
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "project_documents" in tables
    finally:
        conn.close()


def test_document_add_apply_and_list(temp_db):
    raw = json.dumps(_document_add_payload(), ensure_ascii=False)
    result = apply_raw_json(raw, user_input="测试", source="test")
    assert result["ok"] is True
    assert len(result["documents_added"]) == 1

    conn = get_connection()
    try:
        docs = list_documents(conn, project_id=1)
        assert len(docs) == 1
        assert docs[0]["title"] == "测试文档"
        assert docs[0]["summary"].startswith("2026-06-20")
        assert docs[0]["status"] == "unknown"
    finally:
        conn.close()


def test_document_add_with_existing_file(temp_db, tmp_path):
    doc_file = tmp_path / "notes.md"
    doc_file.write_text("# notes", encoding="utf-8")
    raw = json.dumps(
        _document_add_payload(source_uri=str(doc_file)),
        ensure_ascii=False,
    )
    result = apply_raw_json(raw, user_input="测试", source="test")
    assert result["ok"] is True

    conn = get_connection()
    try:
        docs = list_documents(conn, project_id=1)
        assert docs[0]["status"] == "current"
    finally:
        conn.close()


def test_document_metadata_update(temp_db):
    apply_raw_json(
        json.dumps(_document_add_payload(), ensure_ascii=False),
        user_input="测试",
        source="test",
    )
    raw = json.dumps(
        {
            "document_metadata_updates": [
                {
                    "project_name": "已知项目",
                    "document_id": 1,
                    "summary": "更新后摘要",
                    "status": "stale",
                }
            ]
        },
        ensure_ascii=False,
    )
    result = apply_raw_json(raw, user_input="测试", source="test")
    assert result["ok"] is True

    conn = get_connection()
    try:
        doc = list_documents(conn, project_id=1)[0]
        assert doc["summary"] == "更新后摘要"
        assert doc["status"] == "stale"
    finally:
        conn.close()


def test_document_link_marks_unknown_uri(temp_db):
    apply_raw_json(
        json.dumps(
            _document_add_payload(source_uri=str("/nonexistent/path/doc.md")),
            ensure_ascii=False,
        ),
        user_input="测试",
        source="test",
    )
    raw = json.dumps(
        {
            "document_links": [
                {
                    "project_name": "已知项目",
                    "document_id": 1,
                    "link_ref": "event:12",
                    "source_uri": "/still/missing.md",
                }
            ]
        },
        ensure_ascii=False,
    )
    result = apply_raw_json(raw, user_input="测试", source="test")
    assert result["ok"] is True

    conn = get_connection()
    try:
        doc = list_documents(conn, project_id=1)[0]
        assert doc["status"] == "unknown"
        assert "link:event:12" in doc["tags"]
    finally:
        conn.close()


def test_document_archive(temp_db):
    apply_raw_json(
        json.dumps(_document_add_payload(), ensure_ascii=False),
        user_input="测试",
        source="test",
    )
    raw = json.dumps(
        {
            "document_archives": [
                {"project_name": "已知项目", "document_id": 1, "reason": "新版本替代"}
            ]
        },
        ensure_ascii=False,
    )
    result = apply_raw_json(raw, user_input="测试", source="test")
    assert result["ok"] is True

    conn = get_connection()
    try:
        doc = list_documents(conn, project_id=1)[0]
        assert doc["status"] == "superseded"
    finally:
        conn.close()


def test_record_guard_rejects_document_rewrite():
    from app.contracts.record_guard import validate_record_payload

    violations = validate_record_payload(
        {"document_rewrites": [{"project_name": "X", "content": "new body"}]}
    )
    assert any(v.code == "forbidden_document_rewrite" for v in violations)


def test_init_db_idempotent_with_documents_table(temp_db):
    conn = get_connection()
    try:
        init_db(conn)
        init_db(conn)
        count = conn.execute("SELECT COUNT(*) FROM project_documents").fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_document_add_schema_validation():
    parsed, err = parse_control_response(
        json.dumps({"document_adds": [{"project_name": "X", "title": ""}]})
    )
    assert parsed is None
    assert err is not None


def test_assess_source_uri():
    assert assess_source_uri("https://example.com") == "current"
    assert assess_source_uri("/no/such/file") == "unknown"
    assert assess_source_uri("") == "unknown"
