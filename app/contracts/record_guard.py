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
        "document_adds",
        "document_metadata_updates",
        "document_links",
        "document_archives",
    )
    return any(data.get(key) for key in write_keys)


def _has_decision_fields(memory_update: dict[str, Any]) -> bool:
    if memory_update.get("validated_facts"):
        return True
    if memory_update.get("key_judgements"):
        return True
    return False


def _provenance_list(memory_update: dict[str, Any]) -> list[dict[str, Any]]:
    prov = memory_update.get("_provenance") or memory_update.get("provenance") or []
    return prov if isinstance(prov, list) else []


def _facts_need_provenance(memory_update: dict[str, Any]) -> list[Any]:
    facts = memory_update.get("validated_facts") or []
    if not facts:
        return []
    if all(isinstance(f, dict) and "text" in f for f in facts):
        return []
    return facts


def validate_record_payload(data: dict[str, Any]) -> list[ContractViolation]:
    """校验 payload 是否符合记录契约；返回违规列表（空=通过）。"""
    violations: list[ContractViolation] = []

    forbidden_rewrite_keys = (
        "document_rewrites",
        "document_content_updates",
        "document_content_rewrites",
    )
    for key in forbidden_rewrite_keys:
        if data.get(key):
            violations.append(
                _violation(
                    "forbidden_document_rewrite",
                    f"payload 含禁止的 {key} 操作",
                    "runtime 不提供自主重写文档内容；仅 document_adds / "
                    "document_metadata_updates / document_links / document_archives",
                )
            )

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
        needs_prov = _facts_need_provenance(memory)
        if needs_prov and not _provenance_list(memory):
            violations.append(
                _violation(
                    "unconfirmed_validated_facts",
                    f"project_memory_updates[{idx}].validated_facts 缺少来源与确认",
                    f"为每条事实附带 _provenance（source_type, confirmation, source_ref）；"
                    f"见 {CONTRACT_REF}「来源与确认字段」",
                )
            )
        for prov_idx, prov in enumerate(_provenance_list(memory)):
            if not isinstance(prov, dict):
                continue
            if prov.get("confirmation") == "unconfirmed":
                violations.append(
                    _violation(
                        "unconfirmed_validated_facts",
                        f"project_memory_updates[{idx}]._provenance[{prov_idx}] "
                        "confirmation 为 unconfirmed",
                        "改用 open_questions；见 docs/record-contract.md",
                    )
                )
            if prov.get("source_type") == "legacy":
                violations.append(
                    _violation(
                        "legacy_source_on_new_write",
                        f"project_memory_updates[{idx}]._provenance[{prov_idx}] "
                        "新写入不得使用 legacy",
                        f"见 {CONTRACT_REF}「来源与确认字段」",
                    )
                )
        if isinstance(facts, list):
            for fact_idx, fact in enumerate(facts):
                if not isinstance(fact, dict):
                    continue
                if fact.get("confirmation") == "unconfirmed":
                    violations.append(
                        _violation(
                            "unconfirmed_validated_facts",
                            f"project_memory_updates[{idx}].validated_facts[{fact_idx}] "
                            "confirmation 为 unconfirmed",
                            "改用 open_questions；见 docs/record-contract.md",
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

    for idx, event in enumerate(data.get("project_events") or []):
        if not isinstance(event, dict):
            continue
        decision = (event.get("decision") or "").strip()
        if not decision:
            continue
        prov = event.get("decision_provenance")
        if not prov:
            violations.append(
                _violation(
                    "decision_without_provenance",
                    f"project_events[{idx}].decision 缺少 decision_provenance",
                    f"附带 decision_provenance（source_type, confirmation）；"
                    f"见 {CONTRACT_REF}「来源与确认字段」",
                )
            )
        elif isinstance(prov, dict):
            if prov.get("confirmation") == "unconfirmed":
                violations.append(
                    _violation(
                        "unconfirmed_decision",
                        f"project_events[{idx}].decision_provenance confirmation 为 unconfirmed",
                        "改用 open_questions 或待用户确认后再写入",
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

    for idx, doc in enumerate(data.get("document_adds") or []):
        if not isinstance(doc, dict):
            continue
        if not (doc.get("title") or "").strip():
            violations.append(
                _violation(
                    "document_missing_title",
                    f"document_adds[{idx}].title 不能为空",
                    "登记文档须提供标题",
                )
            )

    return violations
