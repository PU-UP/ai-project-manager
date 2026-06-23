"""Pydantic 模型：LLM/Agent 响应校验。"""

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import CONTROL_ACTIONS, PROJECT_EVENT_TYPES, RISK_LEVELS, STATUSES
from app.provenance import (
    NEW_WRITE_SOURCE_TYPES,
    legacy_decision_provenance,
    merge_facts_with_provenance,
    normalize_decision_provenance,
    parse_validated_facts,
)

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
SourceType = Literal["user", "document", "import"]
Confirmation = Literal["confirmed", "unconfirmed"]
DocumentStatus = Literal["current", "stale", "superseded", "unknown"]


class ProvenanceInput(BaseModel):
    """新写入的来源与确认（不含 legacy）。"""

    source_type: SourceType
    source_ref: str = ""
    confirmation: Confirmation


class ProvenanceRecord(ProvenanceInput):
    """持久化后的 provenance 条目。"""

    text: str = ""
    recorded_at: str = ""


class DecisionProvenanceInput(BaseModel):
    source_type: SourceType
    source_ref: str = ""
    confirmation: Confirmation


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
    model_config = ConfigDict(populate_by_name=True)

    project_name: str
    origin: str | None = None
    current_goal: str | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    progress_note: str | None = None
    key_judgements: list[str] | None = None
    validated_facts: list[str | dict[str, Any]] | None = None
    open_questions: list[str] | None = None
    discussion_brief: str | None = None
    reason: str | None = None
    provenance: list[ProvenanceInput] | None = Field(default=None, alias="_provenance")

    @model_validator(mode="after")
    def validate_validated_facts_provenance(self) -> "ProjectMemoryUpdate":
        if not self.validated_facts:
            return self
        has_embedded = any(
            isinstance(item, dict) and "text" in item for item in self.validated_facts
        )
        if has_embedded:
            for item in self.validated_facts:
                if not isinstance(item, dict):
                    continue
                confirmation = item.get("confirmation")
                if confirmation == "unconfirmed":
                    raise ValueError(
                        "unconfirmed 内容不能写入 validated_facts；改用 open_questions"
                    )
                source_type = item.get("source_type")
                if source_type and source_type not in NEW_WRITE_SOURCE_TYPES:
                    raise ValueError("新写入不能使用 legacy 作为 source_type")
            return self
        if not self.provenance:
            raise ValueError(
                "validated_facts 需要附带 _provenance（source_type, confirmation, source_ref）"
            )
        if len(self.provenance) < len(self.validated_facts):
            raise ValueError("_provenance 条目数须与 validated_facts 对齐")
        for prov in self.provenance:
            if prov.confirmation == "unconfirmed":
                raise ValueError(
                    "unconfirmed 内容不能写入 validated_facts；改用 open_questions"
                )
            if prov.source_type not in NEW_WRITE_SOURCE_TYPES:
                raise ValueError("新写入不能使用 legacy 作为 source_type")
        return self

    def resolved_validated_facts(self, recorded_at: str) -> list[dict[str, Any]] | None:
        if self.validated_facts is None:
            return None
        prov_list = (
            [p.model_dump() for p in self.provenance] if self.provenance else None
        )
        return merge_facts_with_provenance(
            self.validated_facts, prov_list, recorded_at
        )


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
    decision_provenance: DecisionProvenanceInput | None = None
    next_action: str | None = None
    happened_at: str | None = None

    @model_validator(mode="after")
    def decision_requires_provenance(self) -> "ProjectEventInput":
        if not (self.decision or "").strip():
            return self
        if self.decision_provenance is None:
            raise ValueError(
                "decision 非空时需要 decision_provenance（source_type, confirmation）"
            )
        if self.decision_provenance.confirmation == "unconfirmed":
            raise ValueError("unconfirmed 决定不能写入 decision 字段")
        return self


class ProjectDeletion(BaseModel):
    project_name: str
    mode: Literal["archive", "delete"] = "archive"
    reason: str | None = None
    confirm_explicit: bool = False

    @model_validator(mode="after")
    def delete_requires_explicit_confirm(self) -> "ProjectDeletion":
        if self.mode == "delete" and not self.confirm_explicit:
            raise ValueError("彻底删除需要 confirm_explicit=true")
        return self


class DocumentAdd(BaseModel):
    project_name: str
    title: str = Field(min_length=1)
    document_type: str = ""
    source_uri: str = ""
    source_kind: str = ""
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    version_or_date: str = ""
    status: DocumentStatus | None = None
    reason: str | None = None


class DocumentUpdateMetadata(BaseModel):
    project_name: str
    document_id: int
    title: str | None = None
    document_type: str | None = None
    source_uri: str | None = None
    source_kind: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    version_or_date: str | None = None
    status: DocumentStatus | None = None
    reason: str | None = None


class DocumentLink(BaseModel):
    project_name: str
    document_id: int
    link_ref: str = ""
    source_uri: str | None = None
    reason: str | None = None


class DocumentArchive(BaseModel):
    project_name: str
    document_id: int
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
    document_adds: list[DocumentAdd] = Field(default_factory=list)
    document_metadata_updates: list[DocumentUpdateMetadata] = Field(default_factory=list)
    document_links: list[DocumentLink] = Field(default_factory=list)
    document_archives: list[DocumentArchive] = Field(default_factory=list)
    system_judgement: SystemJudgement | None = None

    @field_validator("system_judgement", mode="before")
    @classmethod
    def empty_judgement_as_none(cls, v):
        if v == {} or v is None:
            return None
        return v

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
        "document_adds",
        "document_metadata_updates",
        "document_links",
        "document_archives",
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
    d["key_judgements"] = _parse_string_list(d.get("key_judgements"))
    d["validated_facts"] = parse_validated_facts(d.get("validated_facts"))
    d["open_questions"] = _parse_string_list(d.get("open_questions"))
    if d.get("updated_at"):
        d["updated_at"] = format_display(d["updated_at"], with_seconds=False)
    if d.get("created_at"):
        d["created_at"] = format_display(d["created_at"], with_seconds=False)
    return d


def row_to_document_dict(row) -> dict:
    """sqlite3.Row → API/模板用 document dict。"""
    from app.datetime_util import format_display

    d = dict(row)
    d["tags"] = _parse_string_list(d.get("tags"))
    link_refs = [
        t[len("link:") :]
        for t in d["tags"]
        if isinstance(t, str) and t.startswith("link:")
    ]
    d["link_refs"] = link_refs
    if d.get("added_at"):
        d["added_at"] = format_display(d["added_at"], with_seconds=False)
    if d.get("updated_at"):
        d["updated_at"] = format_display(d["updated_at"], with_seconds=False)
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
    raw_prov = d.pop("decision_provenance", "") or ""
    if raw_prov:
        try:
            parsed = json.loads(raw_prov)
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        d["decision_provenance"] = normalize_decision_provenance(
            parsed, str(raw_created_at or "")
        )
    elif d.get("decision"):
        d["decision_provenance"] = legacy_decision_provenance(str(raw_created_at or ""))
    else:
        d["decision_provenance"] = None
    if d.get("created_at"):
        d["created_at"] = format_display(d["created_at"], with_seconds=False)
    if d.get("happened_at"):
        if has_time_component(d["happened_at"]):
            d["happened_at"] = format_display(d["happened_at"], with_seconds=False)
        else:
            d["happened_at"] = format_display(d["happened_at"], with_seconds=False)[:10]
    return d
