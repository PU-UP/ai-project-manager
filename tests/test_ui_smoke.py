"""首页与详情页 UI / API smoke 测试。"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(temp_db):
    from app.main import app

    return TestClient(app)


def test_index_has_snapshot_not_judgement(client):
    response = client.get("/")
    assert response.status_code == 200
    text = response.text
    assert "组合快照" in text
    assert "首要建议" not in text
    assert "真推进" not in text
    assert "假性推进" not in text
    assert "可交给 AI" not in text
    assert "当前判断" not in text
    assert "validated_facts_or_open_questions" not in text
    assert "snapshot-list" in text


def test_api_snapshot_returns_counts(client):
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "status_counts" in data
    assert "total" in data
    assert data["total"] >= 1


def test_project_detail_page_loads(client):
    response = client.get("/project/1")
    assert response.status_code == 200
    text = response.text
    assert "项目简报" in text
    assert "档案备注" in text
    assert "相关文档" in text
    assert "当前控制" not in text


def test_project_detail_404(client):
    assert client.get("/project/99999").status_code == 404


def test_legacy_decision_and_next_action_are_labeled(client):
    import json

    from app.db import get_connection
    from app.services.apply_control import apply_raw_json

    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE projects SET known_risks = ? WHERE id = 1
            """,
            ('[{"text":"历史风险","source_type":"legacy","source_ref":"",'
             '"confirmation":"legacy","recorded_at":"2026-01-01"}]',),
        )
        conn.execute(
            """
            INSERT INTO project_events (
                project_id, project_name, event_type, summary, decision,
                decision_provenance, next_action, created_at
            ) VALUES (1, '已知项目', 'decision', '历史控制记录',
                      '建议调整为 active', '', '建议下一步', '2026-01-01 10:00:00')
            """
        )
        conn.commit()
    finally:
        conn.close()

    confirmed = apply_raw_json(
        json.dumps({
            "project_events": [{
                "project_name": "已知项目",
                "event_type": "note",
                "summary": "新行动记录",
                "next_action": "用户确认下一步",
                "next_action_provenance": {
                    "source_type": "user",
                    "confirmation": "confirmed",
                },
            }]
        }, ensure_ascii=False),
        user_input="ui smoke",
        source="test",
    )
    assert confirmed["ok"] is True

    index = client.get("/").text
    detail = client.get("/project/1").text
    assert "历史风险" in detail
    for text in (index, detail):
        assert "建议调整为 active" in text
        assert "历史存档" in text
        assert "历史待办：建议下一步" in text
        assert "待办：用户确认下一步" in text
        assert "历史待办：用户确认下一步" not in text
        assert "已确认" in text
