"""决策型 legacy 字段常量与导出辅助。"""

from __future__ import annotations

from typing import Any

# 库中保留、新协议禁止写入、默认导出/UI 不展示
LEGACY_DECISION_FIELDS: tuple[str, ...] = (
    "value_score",
    "risk_level",
    "ai_delegation_level",
    "human_intervention_level",
    "control_action",
    "control_action_note",
    "progress_percent",
    "key_judgements",
)

FORBIDDEN_NEW_WRITE_FIELDS: frozenset[str] = frozenset(LEGACY_DECISION_FIELDS)

# 新项目 INSERT 时写入库列的中性占位（不暴露给 Agent schema）
NEUTRAL_DB_DEFAULTS: dict[str, Any] = {
    "value_score": 3,
    "risk_level": "medium",
    "risk_note": "",
    "ai_delegation_level": 3,
    "human_intervention_level": 3,
    "control_action": "observe",
    "control_action_note": "",
}


def _has_legacy_value(value: Any) -> bool:
    if value is None:
        return False
    if value == "" or value == 0:
        return False
    if isinstance(value, list) and not value:
        return False
    return True


def extract_legacy_decision_fields(project: dict[str, Any]) -> dict[str, Any]:
    """从项目 dict 抽出非空的 legacy 决策字段。"""
    legacy: dict[str, Any] = {}
    for key in LEGACY_DECISION_FIELDS:
        if key not in project:
            continue
        value = project[key]
        if _has_legacy_value(value):
            legacy[key] = value
    return legacy


def project_for_core_export(project: dict[str, Any]) -> dict[str, Any]:
    """默认导出用：移除 legacy 决策字段，保留 legacy 块供只读追溯。"""
    out = dict(project)
    legacy = extract_legacy_decision_fields(out)
    for key in LEGACY_DECISION_FIELDS:
        out.pop(key, None)
    if legacy:
        out["legacy_decision_fields"] = legacy
    return out
