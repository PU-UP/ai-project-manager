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
    assert "当前控制" not in text


def test_project_detail_404(client):
    assert client.get("/project/99999").status_code == 404
