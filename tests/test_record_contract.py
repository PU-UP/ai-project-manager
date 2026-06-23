"""记录与 schema 安全契约测试。

契约来源：docs/record-contract.md
"""

import json

import pytest

from app.contracts.record_guard import CONTRACT_REF, validate_record_payload
from app.db import get_connection
from app.services.control_parser import parse_control_response
from app.services.project_updater import apply_updates, list_projects


def _minimal_judgement() -> dict:
    return {"summary": "测试占位"}


def _single_event_payload(project_name: str = "已知项目") -> dict:
    return {
        "project_events": [
            {
                "project_name": project_name,
                "event_type": "note",
                "summary": "用户确认的决定：暂停推进",
                "decision": "维持暂停",
            }
        ]
    }


@pytest.mark.xfail(
    reason="Step 3：ControlResponse.system_judgement 仍为必填；"
    "修复 app/schemas.py 后移除此 xfail",
    strict=True,
)
def test_single_event_payload_validates_without_system_judgement():
    """只含一个 project event 的 payload 应能校验成功（无 judgement）。"""
    raw = json.dumps(_single_event_payload(), ensure_ascii=False)
    parsed, err = parse_control_response(raw)
    assert err is None, (
        f"schema 校验失败：{err}；修复 app/schemas.py ControlResponse"
        f" 与 {CONTRACT_REF}"
    )
    assert parsed is not None
    assert len(parsed.project_events) == 1
    assert parsed.system_judgement is None


def test_record_guard_rejects_system_judgement_in_record_payload():
    payload = {**_single_event_payload(), "system_judgement": _minimal_judgement()}
    violations = validate_record_payload(payload)
    codes = {v.code for v in violations}
    assert "forbidden_system_judgement" in codes
    assert any("app/schemas.py" in v.fix_hint for v in violations)


def test_record_guard_rejects_unconfirmed_validated_facts():
    payload = {
        "project_memory_updates": [
            {
                "project_name": "已知项目",
                "validated_facts": ["Agent 推断但未确认的事实"],
            }
        ]
    }
    violations = validate_record_payload(payload)
    assert any(v.code == "unconfirmed_validated_facts" for v in violations)
    v = next(v for v in violations if v.code == "unconfirmed_validated_facts")
    assert CONTRACT_REF in v.fix_hint


def test_record_guard_allows_confirmed_facts_with_provenance():
    payload = {
        "project_memory_updates": [
            {
                "project_name": "已知项目",
                "validated_facts": ["用户确认暂停 Hermes"],
                "_provenance": [
                    {
                        "source_type": "user",
                        "confirmation": "confirmed",
                        "source_ref": "用户原话",
                    }
                ],
            }
        ]
    }
    violations = validate_record_payload(payload)
    assert not any(v.code == "unconfirmed_validated_facts" for v in violations)


def test_record_guard_rejects_delete_without_explicit_confirm():
    payload = {
        "project_deletions": [
            {"project_name": "已知项目", "mode": "delete", "reason": "测试"}
        ]
    }
    violations = validate_record_payload(payload)
    assert any(v.code == "delete_without_explicit_confirm" for v in violations)
    v = next(v for v in violations if v.code == "delete_without_explicit_confirm")
    assert "app/schemas.py" in v.fix_hint


def test_unknown_project_event_does_not_auto_create(temp_db):
    """未知项目仅写 event 时不得自动创建项目。"""
    from app.schemas import ControlResponse, SystemJudgement

    payload = ControlResponse(
        project_events=[
            {
                "project_name": "不存在的项目",
                "event_type": "note",
                "summary": "不应创建项目",
            }
        ],
        system_judgement=SystemJudgement(summary="测试"),
    )
    conn = get_connection()
    try:
        before = {p["name"] for p in list_projects(conn)}
        result = apply_updates(conn, payload)
        after = {p["name"] for p in list_projects(conn)}
    finally:
        conn.close()

    assert "不存在的项目" in result["skipped"]
    assert "不存在的项目" not in result["created"]
    assert after == before
    assert "不存在的项目" not in after


def test_event_only_payload_with_judgement_parses_today(temp_db):
    """过渡期：含 system_judgement 的单事件 payload 仍可解析并 apply。"""
    raw = json.dumps(
        {**_single_event_payload(), "system_judgement": _minimal_judgement()},
        ensure_ascii=False,
    )
    parsed, err = parse_control_response(raw)
    assert err is None, err

    conn = get_connection()
    try:
        result = apply_updates(conn, parsed)
    finally:
        conn.close()

    assert "已知项目" in result["events"]
