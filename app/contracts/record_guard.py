"""Record Mode apply payload 契约校验。

契约来源：docs/record-contract.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONTRACT_REF = "docs/record-contract.md"


@dataclass(frozen=True)
class ContractViolation:
    code: str
    message: str
    fix_hint: str


def _violation(code: str, message: str, fix_hint: str) -> ContractViolation:
    return ContractViolation(code=code, message=message, fix_hint=fix_hint)


def _is_record_mode_payload(data: dict[str, Any]) -> bool:
    """含写入操作且非仅 Handoff 说明的 payload。"""
    write_keys = (
        "project_creations",
        "project_renames",
        "project_updates",
        "project_constraint_updates",
        "project_memory_updates",
        "project_events",
        "project_deletions",
    )
    return any(data.get(key) for key in write_keys)


def _has_decision_fields(memory_update: dict[str, Any]) -> bool:
    if memory_update.get("validated_facts"):
        return True
    if memory_update.get("key_judgements"):
        return True
    return False


def validate_record_payload(data: dict[str, Any]) -> list[ContractViolation]:
    """校验 payload 是否符合记录契约；返回违规列表（空=通过）。"""
    violations: list[ContractViolation] = []

    if not _is_record_mode_payload(data):
        return violations

    judgement = data.get("system_judgement")
    if judgement is not None:
        violations.append(
            _violation(
                "forbidden_system_judgement",
                "Record Mode payload 不应包含 system_judgement",
                f"移除 system_judgement；见 {CONTRACT_REF}「不可以写」"
                "；Step 3 将同步 app/schemas.py ControlResponse",
            )
        )

    for idx, memory in enumerate(data.get("project_memory_updates") or []):
        if not isinstance(memory, dict):
            continue
        facts = memory.get("validated_facts")
        if facts and not memory.get("_provenance"):
            violations.append(
                _violation(
                    "unconfirmed_validated_facts",
                    f"project_memory_updates[{idx}].validated_facts 缺少来源与确认",
                    f"为每条事实附带 _provenance（source_type, confirmation, source_ref）；"
                    f"见 {CONTRACT_REF}「来源与确认字段」；Step 6 落地 schema",
                )
            )
        if memory.get("key_judgements"):
            violations.append(
                _violation(
                    "agent_inference_as_judgement",
                    f"project_memory_updates[{idx}].key_judgements 属于 Agent 推断",
                    f"改用 open_questions 或经用户确认的用户决定；见 {CONTRACT_REF}",
                )
            )

    for idx, deletion in enumerate(data.get("project_deletions") or []):
        if not isinstance(deletion, dict):
            continue
        if deletion.get("mode") == "delete" and not deletion.get("confirm_explicit"):
            violations.append(
                _violation(
                    "delete_without_explicit_confirm",
                    f"project_deletions[{idx}] 彻底删除缺少 confirm_explicit",
                "在 app/schemas.py ProjectDeletion 增加 confirm_explicit；"
                f"见 {CONTRACT_REF} FAQ「删除项目」",
                )
            )

    for idx, update in enumerate(data.get("project_updates") or []):
        if not isinstance(update, dict):
            continue
        for forbidden in (
            "value_score",
            "risk_level",
            "control_action",
            "control_action_note",
            "ai_delegation_level",
            "human_intervention_level",
        ):
            if update.get(forbidden) is not None:
                violations.append(
                    _violation(
                        f"forbidden_decision_field_{forbidden}",
                        f"project_updates[{idx}].{forbidden} 不属于新写入协议",
                        f"移除该字段；见 {CONTRACT_REF}「不可以写」",
                    )
                )

    return violations
