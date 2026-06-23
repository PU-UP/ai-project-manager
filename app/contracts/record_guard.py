"""Record Mode apply payload 契约校验。

契约来源：docs/record-contract.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.legacy_fields import FORBIDDEN_NEW_WRITE_FIELDS

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


def _validate_provenance_collection(
    violations: list[ContractViolation],
    memory: dict[str, Any],
    idx: int,
    field_name: str,
    provenance_name: str,
) -> None:
    invalid_code = (
        "unconfirmed_validated_facts"
        if field_name == "validated_facts"
        else "invalid_known_risks_provenance"
    )
    items = memory.get(field_name) or []
    if not isinstance(items, list) or not items:
        return
    provenance = memory.get(provenance_name) or []
    structured = [isinstance(item, dict) for item in items]
    if any(structured) and not all(structured):
        violations.append(_violation(
            f"mixed_{field_name}_formats",
            f"project_memory_updates[{idx}].{field_name} 混用了结构化与字符串条目",
            "所有条目使用结构化 provenance，或全部使用字符串并附带等长来源数组",
        ))
        return
    if all(structured):
        for item_idx, item in enumerate(items):
            if (
                not str(item.get("text") or "").strip()
                or item.get("source_type") not in ("user", "document", "import")
                or item.get("confirmation") != "confirmed"
            ):
                violations.append(_violation(
                    invalid_code,
                    f"project_memory_updates[{idx}].{field_name}[{item_idx}] 缺少有效来源或确认",
                    f"见 {CONTRACT_REF}「来源与确认字段」",
                ))
        return
    if not isinstance(provenance, list) or len(provenance) != len(items):
        violations.append(_violation(
            invalid_code,
            f"project_memory_updates[{idx}].{field_name} 缺少等长 {provenance_name}",
            f"见 {CONTRACT_REF}「来源与确认字段」",
        ))
        return
    for prov_idx, prov in enumerate(provenance):
        if (
            not isinstance(prov, dict)
            or prov.get("source_type") not in ("user", "document", "import")
            or prov.get("confirmation") != "confirmed"
        ):
            violations.append(_violation(
                invalid_code,
                f"project_memory_updates[{idx}].{provenance_name}[{prov_idx}] 无效",
                f"见 {CONTRACT_REF}「来源与确认字段」",
            ))


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

    for idx, memory in enumerate(data.get("project_memory_updates") or []):
        if not isinstance(memory, dict):
            continue
        _validate_provenance_collection(
            violations, memory, idx, "validated_facts", "_provenance"
        )
        _validate_provenance_collection(
            violations, memory, idx, "known_risks", "_risk_provenance"
        )
        if memory.get("key_judgements"):
            violations.append(
                _violation(
                    "agent_inference_as_judgement",
                    f"project_memory_updates[{idx}].key_judgements 属于 Agent 推断",
                    f"改用 open_questions 或 known_risks；见 {CONTRACT_REF}",
                )
            )
        for forbidden in ("progress_percent",):
            if memory.get(forbidden) is not None:
                violations.append(
                    _violation(
                        f"forbidden_legacy_field_{forbidden}",
                        f"project_memory_updates[{idx}].{forbidden} 已废弃",
                        "不得在新写入中使用；见 roadmap Step 8",
                    )
                )

    for idx, creation in enumerate(data.get("project_creations") or []):
        if not isinstance(creation, dict):
            continue
        for forbidden in FORBIDDEN_NEW_WRITE_FIELDS:
            if creation.get(forbidden) is not None:
                violations.append(
                    _violation(
                        f"forbidden_legacy_field_{forbidden}",
                        f"project_creations[{idx}].{forbidden} 已废弃",
                        "新项目不得写入决策型字段；见 roadmap Step 8",
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
        if update.get("risk_note") is not None:
            violations.append(_violation(
                "risk_note_without_provenance",
                f"project_updates[{idx}].risk_note 仅供 legacy 读取",
                "新风险请写入带 _risk_provenance 的 known_risks",
            ))
        for forbidden in FORBIDDEN_NEW_WRITE_FIELDS:
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
