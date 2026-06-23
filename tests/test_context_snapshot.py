"""确定性组合快照测试。"""

from datetime import datetime, timedelta

from app.datetime_util import BEIJING
from app.services.context_snapshot import RECENT_DAYS, STALE_DAYS, build_portfolio_snapshot


def _ts(days_ago: int) -> str:
    return (datetime.now(BEIJING) - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M")


def test_snapshot_counts_statuses():
    projects = [
        {"id": 1, "name": "A", "status": "active", "updated_at": _ts(1)},
        {"id": 2, "name": "B", "status": "paused", "updated_at": _ts(2)},
        {"id": 3, "name": "C", "status": "archived", "updated_at": _ts(100)},
    ]
    snap = build_portfolio_snapshot(projects)
    assert snap["total"] == 3
    assert snap["status_counts"]["active"] == 1
    assert snap["status_counts"]["paused"] == 1
    assert snap["status_counts"]["archived"] == 1


def test_snapshot_detects_stale_and_recent():
    projects = [
        {
            "id": 1,
            "name": "Recent",
            "status": "active",
            "updated_at": _ts(2),
            "origin": "x",
            "current_goal": "y",
            "discussion_brief": "z",
            "validated_facts": ["fact"],
            "open_questions": [],
        },
        {
            "id": 2,
            "name": "Stale",
            "status": "maintain",
            "updated_at": _ts(STALE_DAYS + 5),
            "origin": "x",
            "current_goal": "y",
            "discussion_brief": "z",
            "validated_facts": ["fact"],
            "open_questions": [],
        },
    ]
    snap = build_portfolio_snapshot(projects)
    assert snap["recently_updated_count"] == 1
    assert snap["recently_updated"][0]["name"] == "Recent"
    assert snap["stale_count"] == 1
    assert snap["stale_projects"][0]["name"] == "Stale"


def test_snapshot_missing_memory_and_open_questions():
    projects = [
        {
            "id": 1,
            "name": "Thin",
            "status": "active",
            "updated_at": _ts(1),
            "open_questions": ["待确认？"],
        },
        {
            "id": 2,
            "name": "Full",
            "status": "observe",
            "updated_at": _ts(1),
            "origin": "o",
            "current_goal": "g",
            "discussion_brief": "b",
            "validated_facts": ["f"],
            "open_questions": [],
        },
    ]
    snap = build_portfolio_snapshot(projects)
    assert snap["missing_memory_count"] == 1
    assert snap["missing_memory"][0]["name"] == "Thin"
    assert "项目初衷" in snap["missing_memory"][0]["missing_field_labels"]
    assert snap["pending_confirmation_count"] == 1
    assert snap["pending_confirmation"][0]["name"] == "Thin"


def test_snapshot_thresholds_exposed():
    snap = build_portfolio_snapshot([])
    assert snap["thresholds"]["recent_days"] == RECENT_DAYS
    assert snap["thresholds"]["stale_days"] == STALE_DAYS
