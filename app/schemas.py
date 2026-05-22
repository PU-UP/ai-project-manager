"""Pydantic 模型：LLM/Agent 响应校验。"""

import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models import CONTROL_ACTIONS, PROJECT_EVENT_TYPES, RISK_LEVELS, STATUSES

Status = Literal[
    "active", "maintain", "observe", "paused", "archived"
]
RiskLevel = Literal["low", "medium", "high"]
ControlAction = Literal[
    "continue",
    "maintain",
    "observe",
    "pause",
    "delegate_to_ai",
    "human_intervene",
    "seek_feedback",
    "narrow_scope",
    "change_metric",
    "archive",
]
ProjectEventType = Literal[
    "progress",
    "decision",
    "risk",
    "feedback",
    "idea",
    "blocker",
    "note",
]


class ProjectUpdate(BaseModel):
    project_name: str
    status: Status | None = None
    value_score: int | None = Field(default=None, ge=1, le=5)
    risk_level: RiskLevel | None = None
    risk_note: str | None = None
    ai_delegation_level: int | None = Field(default=None, ge=0, le=5)
    human_intervention_level: int | None = Field(default=None, ge=0, le=5)
    control_action: ControlAction | None = None
    control_action_note: str | None = Field(default=None, max_length=80)
    latest_update: str | None = Field(default=None, max_length=200)
    reason: str | None = None


class ProjectRename(BaseModel):
    project_name: str
    new_project_name: str
    reason: str | None = None


class ProjectConstraintUpdate(BaseModel):
    project_name: str
    project_constraint: str
    reason: str | None = None


class ProjectMemoryUpdate(BaseModel):
    project_name: str
    origin: str | None = None
    current_goal: str | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    progress_note: str | None = None
    key_judgements: list[str] | None = None
    validated_facts: list[str] | None = None
    open_questions: list[str] | None = None
    discussion_brief: str | None = None
    reason: str | None = None


class ProjectCreation(BaseModel):
    project_name: str
    status: Status = "observe"
    value_score: int = Field(default=3, ge=1, le=5)
    risk_level: RiskLevel = "medium"
    risk_note: str = "新项目，尚未形成稳定判断"
    ai_delegation_level: int = Field(default=3, ge=0, le=5)
    human_intervention_level: int = Field(default=3, ge=0, le=5)
    control_action: ControlAction = "observe"
    control_action_note: str = Field(default="先记录并观察，不急于扩展范围", max_length=80)
    latest_update: str = Field(default="由 Agent 根据用户确认创建", max_length=200)
    project_constraint: str = "先验证真实需求和下一步控制动作，再扩展系统能力"
    reason: str | None = None


class ProjectEventInput(BaseModel):
    project_name: str
    event_type: ProjectEventType = "progress"
    summary: str
    evidence: str | None = None
    decision: str | None = None
    next_action: str | None = None
    happened_at: str | None = None


class ProjectDeletion(BaseModel):
    project_name: str
    mode: Literal["archive", "delete"] = "archive"
    reason: str | None = None


class TopControlRecommendation(BaseModel):
    control_action: ControlAction
    project_name: str
    note: str


class SystemJudgement(BaseModel):
    summary: str
    real_progress: list[str] = Field(default_factory=list)
    pseudo_progress_risk: list[str] = Field(default_factory=list)
    delegate_to_ai: list[str] = Field(default_factory=list)
    need_human_intervention: list[str] = Field(default_factory=list)
    pause_or_ignore: list[str] = Field(default_factory=list)
    top_control_recommendation: TopControlRecommendation | None = None


class ControlResponse(BaseModel):
    project_creations: list[ProjectCreation] = Field(default_factory=list)
    project_renames: list[ProjectRename] = Field(default_factory=list)
    project_updates: list[ProjectUpdate] = Field(default_factory=list)
    project_constraint_updates: list[ProjectConstraintUpdate] = Field(default_factory=list)
    project_memory_updates: list[ProjectMemoryUpdate] = Field(default_factory=list)
    project_events: list[ProjectEventInput] = Field(default_factory=list)
    project_deletions: list[ProjectDeletion] = Field(default_factory=list)
    system_judgement: SystemJudgement

    @field_validator("project_updates", mode="before")
    @classmethod
    def ensure_list(cls, v):
        return v or []

    @field_validator(
        "project_creations",
        "project_renames",
        "project_constraint_updates",
        "project_memory_updates",
        "project_events",
        "project_deletions",
        mode="before",
    )
    @classmethod
    def ensure_operation_lists(cls, v):
        return v or []


def row_to_project_dict(row) -> dict:
    """sqlite3.Row → API/模板用 dict。"""
    from app.datetime_util import format_display

    d = dict(row)
    d["constraint"] = d.pop("project_constraint", "")
    for field in ("key_judgements", "validated_facts", "open_questions"):
        d[field] = _parse_string_list(d.get(field))
    if d.get("updated_at"):
        d["updated_at"] = format_display(d["updated_at"], with_seconds=False)
    if d.get("created_at"):
        d["created_at"] = format_display(d["created_at"], with_seconds=False)
    return d


def _parse_string_list(raw) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, str)]


def row_to_event_dict(row) -> dict:
    """sqlite3.Row → API/模板用 event dict。"""
    from app.datetime_util import format_display, format_event_display, has_time_component

    d = dict(row)
    raw_created_at = d.get("created_at")
    raw_happened_at = d.get("happened_at")
    d["display_at"] = format_event_display(raw_happened_at, raw_created_at, with_seconds=False)
    if d.get("created_at"):
        d["created_at"] = format_display(d["created_at"], with_seconds=False)
    if d.get("happened_at"):
        if has_time_component(d["happened_at"]):
            d["happened_at"] = format_display(d["happened_at"], with_seconds=False)
        else:
            d["happened_at"] = format_display(d["happened_at"], with_seconds=False)[:10]
    return d
