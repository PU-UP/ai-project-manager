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
                "summary": "用户确认的讨论记录",
            }
        ]
    }


def _decision_event_payload(project_name: str = "已知项目") -> dict:
    return {
        "project_events": [
            {
                "project_name": project_name,
                "event_type": "decision",
                "summary": "用户确认暂停推进",
                "decision": "维持暂停",
                "decision_provenance": {
                    "source_type": "user",
                    "confirmation": "confirmed",
                    "source_ref": "用户原话",
                },
            }
        ]
    }


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


def test_single_event_applies_without_system_judgement(temp_db):
    """无 system_judgement 的单事件 payload 可成功 apply。"""
    raw = json.dumps(_single_event_payload(), ensure_ascii=False)
    parsed, err = parse_control_response(raw)
    assert err is None

    conn = get_connection()
    try:
        result = apply_updates(conn, parsed)
    finally:
        conn.close()

    assert "已知项目" in result["events"]


def test_delete_without_confirm_explicit_fails_parse():
    raw = json.dumps(
        {
            "project_deletions": [
                {"project_name": "已知项目", "mode": "delete", "reason": "测试"}
            ]
        },
        ensure_ascii=False,
    )
    parsed, err = parse_control_response(raw)
    assert parsed is None
    assert err is not None
    assert "confirm_explicit" in err


def test_delete_with_confirm_explicit_parses():
    raw = json.dumps(
        {
            "project_deletions": [
                {
                    "project_name": "已知项目",
                    "mode": "delete",
                    "confirm_explicit": True,
                    "reason": "用户明确要求",
                }
            ]
        },
        ensure_ascii=False,
    )
    parsed, err = parse_control_response(raw)
    assert err is None, err
    assert parsed is not None
    assert parsed.project_deletions[0].confirm_explicit is True


def test_record_guard_allows_legacy_system_judgement_for_production_compatibility():
    payload = {**_single_event_payload(), "system_judgement": _minimal_judgement()}
    violations = validate_record_payload(payload)
    assert not any(v.code == "forbidden_system_judgement" for v in violations)


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
    from app.schemas import ControlResponse

    payload = ControlResponse(
        project_events=[
            {
                "project_name": "不存在的项目",
                "event_type": "note",
                "summary": "不应创建项目",
            }
        ],
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


def test_event_only_payload_with_judgement_uses_production_entry(temp_db):
    """旧 judgement 可经生产入口 apply，但只归档并忽略。"""
    from app.services.apply_control import apply_raw_json

    raw = json.dumps(
        {**_single_event_payload(), "system_judgement": _minimal_judgement()},
        ensure_ascii=False,
    )
    result = apply_raw_json(raw, user_input="legacy payload", source="test")
    assert result["ok"] is True
    assert result["system_judgement"] is None
    assert any("已废弃" in warning for warning in result["warnings"])
    conn = get_connection()
    try:
        assert conn.execute(
            "SELECT COUNT(*) FROM project_events WHERE project_name = '已知项目'"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT system_judgement FROM logs ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
    finally:
        conn.close()


def test_schema_rejects_mixed_validated_fact_formats():
    raw = json.dumps(
        {
            "project_memory_updates": [{
                "project_name": "已知项目",
                "validated_facts": [
                    {
                        "text": "有来源事实",
                        "source_type": "document",
                        "confirmation": "confirmed",
                    },
                    "无来源事实",
                ],
                "_provenance": [{
                    "source_type": "user",
                    "confirmation": "confirmed",
                }],
            }]
        },
        ensure_ascii=False,
    )
    parsed, err = parse_control_response(raw)
    assert parsed is None
    assert "混用" in (err or "")


def test_record_guard_rejects_mixed_validated_fact_formats():
    payload = {
        "project_memory_updates": [{
            "project_name": "已知项目",
            "validated_facts": [
                {"text": "有来源", "source_type": "document", "confirmation": "confirmed"},
                "无来源",
            ],
            "_provenance": [{"source_type": "user", "confirmation": "confirmed"}],
        }]
    }
    assert any(
        v.code == "mixed_validated_facts_formats"
        for v in validate_record_payload(payload)
    )


@pytest.mark.parametrize(
    "facts,provenance",
    [
        ([{"text": "文档事实", "source_type": "document", "confirmation": "confirmed"}], None),
        (["用户事实"], [{"source_type": "user", "confirmation": "confirmed"}]),
    ],
)
def test_schema_allows_consistent_validated_fact_formats(facts, provenance):
    update = {"project_name": "已知项目", "validated_facts": facts}
    if provenance is not None:
        update["_provenance"] = provenance
    parsed, err = parse_control_response(
        json.dumps({"project_memory_updates": [update]}, ensure_ascii=False)
    )
    assert err is None
    assert parsed is not None


def test_record_guard_rejects_decision_without_provenance():
    payload = {
        "project_events": [
            {
                "project_name": "已知项目",
                "event_type": "decision",
                "summary": "决定暂停",
                "decision": "暂停",
            }
        ]
    }
    violations = validate_record_payload(payload)
    assert any(v.code == "decision_without_provenance" for v in violations)


def test_record_guard_rejects_next_action_without_valid_provenance():
    base = {
        "project_name": "已知项目",
        "event_type": "note",
        "summary": "会议记录",
        "next_action": "下一步",
    }
    missing = validate_record_payload({"project_events": [base]})
    assert any(v.code == "next_action_without_provenance" for v in missing)

    for provenance in (
        {"source_type": "document", "confirmation": "unconfirmed"},
        {"source_type": "legacy", "confirmation": "legacy"},
    ):
        invalid = validate_record_payload({
            "project_events": [{
                **base,
                "next_action_provenance": provenance,
            }]
        })
        assert any(v.code == "invalid_next_action_provenance" for v in invalid)


def test_schema_rejects_unconfirmed_validated_facts():
    raw = json.dumps(
        {
            "project_memory_updates": [
                {
                    "project_name": "已知项目",
                    "validated_facts": ["未确认事实"],
                    "_provenance": [
                        {
                            "source_type": "document",
                            "confirmation": "unconfirmed",
                        }
                    ],
                }
            ]
        },
        ensure_ascii=False,
    )
    parsed, err = parse_control_response(raw)
    assert parsed is None
    assert err is not None
    assert "unconfirmed" in err


def test_confirmed_facts_with_provenance_apply(temp_db):
    raw = json.dumps(
        {
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
        },
        ensure_ascii=False,
    )
    from app.services.apply_control import apply_raw_json

    result = apply_raw_json(raw, user_input="测试", source="test")
    assert result["ok"] is True

    conn = get_connection()
    try:
        projects = list_projects(conn)
        facts = projects[0]["validated_facts"]
        assert len(facts) == 1
        assert facts[0]["text"] == "用户确认暂停 Hermes"
        assert facts[0]["source_type"] == "user"
        assert facts[0]["confirmation"] == "confirmed"
        assert facts[0]["recorded_at"]
    finally:
        conn.close()


def test_apply_rejects_validated_facts_without_provenance(temp_db):
    raw = json.dumps(
        {
            "project_memory_updates": [
                {
                    "project_name": "已知项目",
                    "validated_facts": ["缺少 provenance"],
                }
            ]
        },
        ensure_ascii=False,
    )
    from app.services.apply_control import apply_raw_json

    result = apply_raw_json(raw, user_input="测试", source="test")
    assert result["ok"] is False
    assert "contract_violations" in result or "provenance" in result["error"].lower()


def test_apply_returns_neutral_change_summary(temp_db):
    """apply 返回中性 change_summary，不含系统判断。"""
    from app.services.apply_control import apply_raw_json

    raw = json.dumps(_single_event_payload(), ensure_ascii=False)
    result = apply_raw_json(raw, user_input="测试", source="test")

    assert result["ok"] is True
    assert result["change_summary"] == "事件 1 项"
    assert result["system_judgement"] is None
    assert "推荐" not in result["change_summary"]
