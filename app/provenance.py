"""来源与确认状态（provenance）模型与工具。

契约来源：docs/record-contract.md「来源与确认字段」
"""

from __future__ import annotations

import json
from typing import Any, Literal

SourceType = Literal["user", "document", "import", "legacy"]
Confirmation = Literal["confirmed", "unconfirmed", "legacy"]

SOURCE_TYPES: tuple[str, ...] = ("user", "document", "import", "legacy")
CONFIRMATIONS: tuple[str, ...] = ("confirmed", "unconfirmed", "legacy")
NEW_WRITE_SOURCE_TYPES: tuple[str, ...] = ("user", "document", "import")


def fact_text(item: Any) -> str:
    """从字符串或结构化条目提取展示文本。"""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("text") or "").strip()
    return ""


def is_structured_fact(item: Any) -> bool:
    return isinstance(item, dict) and "text" in item


def legacy_fact_record(text: str, recorded_at: str = "") -> dict[str, Any]:
    """历史字符串事实迁移为 legacy provenance 条目。"""
    return {
        "text": text,
        "source_type": "legacy",
        "source_ref": "",
        "confirmation": "legacy",
        "recorded_at": recorded_at or "",
    }


def legacy_decision_provenance(recorded_at: str = "") -> dict[str, Any]:
    return {
        "source_type": "legacy",
        "source_ref": "",
        "confirmation": "legacy",
        "recorded_at": recorded_at or "",
    }


def parse_validated_facts(raw: Any) -> list[dict[str, Any]]:
    """解析 DB/API 中的 validated_facts JSON。"""
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        raw = parsed
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            result.append(legacy_fact_record(item.strip()))
        elif is_structured_fact(item):
            result.append(normalize_fact_record(item))
    return result


def normalize_fact_record(item: dict[str, Any]) -> dict[str, Any]:
    """规范化单条 provenance 事实。"""
    source_type = item.get("source_type") or "legacy"
    if source_type not in SOURCE_TYPES:
        source_type = "legacy"
    confirmation = item.get("confirmation") or "legacy"
    if confirmation not in CONFIRMATIONS:
        confirmation = "legacy"
    return {
        "text": str(item.get("text") or "").strip(),
        "source_type": source_type,
        "source_ref": str(item.get("source_ref") or ""),
        "confirmation": confirmation,
        "recorded_at": str(item.get("recorded_at") or ""),
    }


def normalize_decision_provenance(item: Any, recorded_at: str = "") -> dict[str, Any]:
    if not isinstance(item, dict) or not item:
        return legacy_decision_provenance(recorded_at)
    source_type = item.get("source_type") or "legacy"
    if source_type not in SOURCE_TYPES:
        source_type = "legacy"
    confirmation = item.get("confirmation") or "legacy"
    if confirmation not in CONFIRMATIONS:
        confirmation = "legacy"
    return {
        "source_type": source_type,
        "source_ref": str(item.get("source_ref") or ""),
        "confirmation": confirmation,
        "recorded_at": str(item.get("recorded_at") or recorded_at or ""),
    }


def serialize_validated_facts(items: list[dict[str, Any]]) -> str:
    return json.dumps(items, ensure_ascii=False)


def merge_facts_with_provenance(
    facts: list[Any],
    provenance_list: list[dict[str, Any]] | None,
    recorded_at: str,
) -> list[dict[str, Any]]:
    """将 validated_facts 文本与 _provenance 伴生数组合并为结构化条目。"""
    merged: list[dict[str, Any]] = []
    prov = provenance_list or []
    for idx, fact in enumerate(facts):
        if is_structured_fact(fact):
            record = normalize_fact_record(fact)
            if not record["recorded_at"]:
                record["recorded_at"] = recorded_at
            merged.append(record)
            continue
        text = fact_text(fact)
        if not text:
            continue
        prov_item = prov[idx] if idx < len(prov) and isinstance(prov[idx], dict) else {}
        source_type = prov_item.get("source_type") or "user"
        confirmation = prov_item.get("confirmation") or "confirmed"
        merged.append(
            {
                "text": text,
                "source_type": source_type,
                "source_ref": str(prov_item.get("source_ref") or ""),
                "confirmation": confirmation,
                "recorded_at": recorded_at,
            }
        )
    return merged


def confirmation_label(confirmation: str) -> str:
    labels = {
        "confirmed": "已确认",
        "unconfirmed": "待确认",
        "legacy": "历史存档",
    }
    return labels.get(confirmation, confirmation)


def source_type_label(source_type: str) -> str:
    labels = {
        "user": "用户",
        "document": "文档",
        "import": "导入",
        "legacy": "历史",
    }
    return labels.get(source_type, source_type)
