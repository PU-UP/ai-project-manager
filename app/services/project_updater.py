"""根据 Agent 返回的项目经理操作更新数据库。"""

import json
from app.datetime_util import now_beijing
from app.models import PROJECT_ALIASES
from app.provenance import serialize_validated_facts
from app.services.document_index import apply_document_operations
from app.schemas import (
    ControlResponse,
    ProjectConstraintUpdate,
    ProjectCreation,
    ProjectDeletion,
    ProjectEventInput,
    ProjectMemoryUpdate,
    ProjectRename,
    ProjectUpdate,
    row_to_event_dict,
    row_to_project_dict,
)

UPDATABLE_FIELDS = (
    "status",
    "value_score",
    "risk_level",
    "risk_note",
    "ai_delegation_level",
    "human_intervention_level",
    "control_action",
    "control_action_note",
    "latest_update",
)

MEMORY_TEXT_FIELDS = (
    "origin",
    "current_goal",
    "progress_note",
    "discussion_brief",
)
MEMORY_JSON_FIELDS = (
    "key_judgements",
    "validated_facts",
    "open_questions",
)
MEMORY_INT_FIELDS = (
    "progress_percent",
)


def _normalize_name(name: str) -> str:
    return name.strip().lower()


def match_project(name: str, projects: list[dict]) -> dict | None:
    name = name.strip()
    for p in projects:
        if p["name"] == name:
            return p
    alias = PROJECT_ALIASES.get(_normalize_name(name))
    if alias:
        for p in projects:
            if p["name"] == alias:
                return p
    norm = _normalize_name(name)
    for p in projects:
        if _normalize_name(p["name"]) == norm:
            return p
        if norm in _normalize_name(p["name"]) or _normalize_name(p["name"]) in norm:
            return p
    return None


def list_projects(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
    return [row_to_project_dict(r) for r in rows]


def list_recent_events(conn, limit: int = 20, project_id: int | None = None) -> list[dict]:
    if project_id is None:
        rows = conn.execute(
            """
            SELECT * FROM project_events
            ORDER BY COALESCE(happened_at, created_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM project_events
            WHERE project_id = ?
            ORDER BY COALESCE(happened_at, created_at) DESC, id DESC
            LIMIT ?
            """,
            (project_id, limit),
        ).fetchall()
    return [row_to_event_dict(r) for r in rows]


def rename_project(
    conn,
    item: ProjectRename,
    project: dict,
    projects: list[dict],
    now: str,
) -> str:
    new_name = item.new_project_name.strip()
    if not new_name:
        raise ValueError("new_project_name 不能为空")
    for p in projects:
        if p["id"] != project["id"] and _normalize_name(p["name"]) == _normalize_name(new_name):
            raise ValueError(f"项目名已存在: {new_name}")

    conn.execute(
        """
        UPDATE projects
        SET name = ?, updated_at = ?
        WHERE id = ?
        """,
        (new_name, now, project["id"]),
    )
    conn.execute(
        """
        UPDATE project_events
        SET project_name = ?
        WHERE project_id = ?
        """,
        (new_name, project["id"]),
    )
    return new_name


def update_project_constraint(
    conn,
    item: ProjectConstraintUpdate,
    project: dict,
    now: str,
) -> str:
    conn.execute(
        """
        UPDATE projects
        SET project_constraint = ?, updated_at = ?
        WHERE id = ?
        """,
        (item.project_constraint, now, project["id"]),
    )
    return project["name"]


def update_project_memory(
    conn,
    item: ProjectMemoryUpdate,
    project: dict,
    now: str,
) -> str:
    sets: list[str] = []
    values: list = []

    for field in MEMORY_TEXT_FIELDS + MEMORY_INT_FIELDS:
        val = getattr(item, field, None)
        if val is None:
            continue
        sets.append(f"{field} = ?")
        values.append(val)

    for field in MEMORY_JSON_FIELDS:
        val = getattr(item, field, None)
        if val is None:
            continue
        if field == "validated_facts":
            resolved = item.resolved_validated_facts(now)
            if resolved is not None:
                sets.append(f"{field} = ?")
                values.append(serialize_validated_facts(resolved))
            continue
        sets.append(f"{field} = ?")
        values.append(json.dumps(val, ensure_ascii=False))

    if not sets:
        return project["name"]

    sets.append("updated_at = ?")
    values.append(now)
    values.append(project["id"])
    conn.execute(
        f"UPDATE projects SET {', '.join(sets)} WHERE id = ?",
        values,
    )
    return project["name"]


def create_project(conn, item: ProjectCreation, now: str) -> str:
    conn.execute(
        """
        INSERT INTO projects (
            name, status, value_score, risk_level, risk_note,
            ai_delegation_level, human_intervention_level,
            control_action, control_action_note, latest_update,
            project_constraint, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.project_name.strip(),
            item.status,
            item.value_score,
            item.risk_level,
            item.risk_note,
            item.ai_delegation_level,
            item.human_intervention_level,
            item.control_action,
            item.control_action_note,
            item.latest_update,
            item.project_constraint,
            now,
            now,
        ),
    )
    return item.project_name.strip()


def append_project_event(
    conn,
    item: ProjectEventInput,
    project: dict,
    now: str,
) -> str:
    decision_prov = ""
    if item.decision_provenance is not None:
        prov = item.decision_provenance.model_dump()
        prov["recorded_at"] = now
        decision_prov = json.dumps(prov, ensure_ascii=False)
    conn.execute(
        """
        INSERT INTO project_events (
            project_id, project_name, event_type, summary, evidence,
            decision, decision_provenance, next_action, happened_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project["id"],
            project["name"],
            item.event_type,
            item.summary,
            item.evidence or "",
            item.decision or "",
            decision_prov,
            item.next_action or "",
            item.happened_at,
            now,
        ),
    )
    return project["name"]


def apply_deletion(conn, item: ProjectDeletion, project: dict, now: str) -> str:
    reason = item.reason or "由 Agent 根据用户意图处理"
    if item.mode == "delete":
        if not item.confirm_explicit:
            raise ValueError("彻底删除需要 confirm_explicit=true")
        conn.execute("DELETE FROM projects WHERE id = ?", (project["id"],))
        return "deleted"

    conn.execute(
        """
        UPDATE projects
        SET status = ?, control_action = ?, control_action_note = ?, updated_at = ?
        WHERE id = ?
        """,
        ("archived", "archive", reason, now, project["id"]),
    )
    return "archived"


def apply_updates(
    conn,
    response: ControlResponse,
) -> dict:
    projects = list_projects(conn)
    created: list[str] = []
    renamed: list[str] = []
    updated: list[str] = []
    constraint_updated: list[str] = []
    memory_updated: list[str] = []
    archived: list[str] = []
    deleted: list[str] = []
    events: list[str] = []
    skipped: list[str] = []
    invalid: list[dict] = []
    renamed_lookup: dict[str, str] = {}
    now = now_beijing()

    for item in response.project_creations:
        if match_project(item.project_name, projects):
            skipped.append(item.project_name)
            continue
        try:
            created.append(create_project(conn, item, now))
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    if created:
        conn.commit()
        projects = list_projects(conn)

    for item in response.project_renames:
        project = match_project(item.project_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            new_name = rename_project(conn, item, project, projects, now)
            renamed.append(f"{project['name']} -> {new_name}")
            renamed_lookup[_normalize_name(item.project_name)] = new_name
            renamed_lookup[_normalize_name(project["name"])] = new_name
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    if renamed:
        conn.commit()
        projects = list_projects(conn)

    for item in response.project_updates:
        lookup_name = renamed_lookup.get(_normalize_name(item.project_name), item.project_name)
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue

        sets: list[str] = []
        values: list = []
        row_invalid: list[str] = []

        for field in UPDATABLE_FIELDS:
            val = getattr(item, field, None)
            if val is None:
                continue
            sets.append(f"{field} = ?")
            values.append(val)

        if not sets:
            updated.append(project["name"])
            continue

        sets.append("updated_at = ?")
        values.append(now)
        values.append(project["id"])

        try:
            conn.execute(
                f"UPDATE projects SET {', '.join(sets)} WHERE id = ?",
                values,
            )
            updated.append(project["name"])
            for p in projects:
                if p["id"] == project["id"]:
                    for field in UPDATABLE_FIELDS:
                        val = getattr(item, field, None)
                        if val is not None:
                            p[field] = val
                    p["updated_at"] = now
                    break
        except Exception as e:
            row_invalid.append({"project": item.project_name, "error": str(e)})
            invalid.extend(row_invalid)

    for item in response.project_constraint_updates:
        lookup_name = renamed_lookup.get(_normalize_name(item.project_name), item.project_name)
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            constraint_updated.append(update_project_constraint(conn, item, project, now))
            for p in projects:
                if p["id"] == project["id"]:
                    p["constraint"] = item.project_constraint
                    p["updated_at"] = now
                    break
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    for item in response.project_memory_updates:
        lookup_name = renamed_lookup.get(_normalize_name(item.project_name), item.project_name)
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            memory_updated.append(update_project_memory(conn, item, project, now))
            for p in projects:
                if p["id"] == project["id"]:
                    for field in MEMORY_TEXT_FIELDS + MEMORY_INT_FIELDS:
                        val = getattr(item, field, None)
                        if val is not None:
                            p[field] = val
                    for field in MEMORY_JSON_FIELDS:
                        val = getattr(item, field, None)
                        if val is not None:
                            if field == "validated_facts":
                                resolved = item.resolved_validated_facts(now)
                                if resolved is not None:
                                    p[field] = resolved
                            else:
                                p[field] = val
                    p["updated_at"] = now
                    break
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    for item in response.project_deletions:
        lookup_name = renamed_lookup.get(_normalize_name(item.project_name), item.project_name)
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            mode = apply_deletion(conn, item, project, now)
            if mode == "deleted":
                deleted.append(project["name"])
            else:
                archived.append(project["name"])
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    if archived or deleted:
        conn.commit()
        projects = list_projects(conn)

    for item in response.project_events:
        lookup_name = renamed_lookup.get(_normalize_name(item.project_name), item.project_name)
        project = match_project(lookup_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            events.append(append_project_event(conn, item, project, now))
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    doc_result = apply_document_operations(
        conn,
        response.document_adds,
        response.document_metadata_updates,
        response.document_links,
        response.document_archives,
        projects,
        renamed_lookup,
    )
    skipped.extend(doc_result["skipped"])
    invalid.extend(doc_result["invalid"])

    conn.commit()
    return {
        "created": created,
        "renamed": renamed,
        "updated": updated,
        "constraint_updated": constraint_updated,
        "memory_updated": memory_updated,
        "archived": archived,
        "deleted": deleted,
        "events": events,
        "documents_added": doc_result["documents_added"],
        "documents_metadata_updated": doc_result["documents_metadata_updated"],
        "documents_linked": doc_result["documents_linked"],
        "documents_archived": doc_result["documents_archived"],
        "skipped": skipped,
        "invalid": invalid,
    }


def updates_summary(response: ControlResponse) -> str:
    return json.dumps(
        {
            "project_creations": [
                u.model_dump(exclude_none=True) for u in response.project_creations
            ],
            "project_renames": [
                u.model_dump(exclude_none=True) for u in response.project_renames
            ],
            "project_updates": [
                u.model_dump(exclude_none=True) for u in response.project_updates
            ],
            "project_constraint_updates": [
                u.model_dump(exclude_none=True)
                for u in response.project_constraint_updates
            ],
            "project_memory_updates": [
                u.model_dump(exclude_none=True, by_alias=True)
                for u in response.project_memory_updates
            ],
            "project_events": [
                u.model_dump(exclude_none=True) for u in response.project_events
            ],
            "project_deletions": [
                u.model_dump(exclude_none=True) for u in response.project_deletions
            ],
            "document_adds": [
                u.model_dump(exclude_none=True) for u in response.document_adds
            ],
            "document_metadata_updates": [
                u.model_dump(exclude_none=True)
                for u in response.document_metadata_updates
            ],
            "document_links": [
                u.model_dump(exclude_none=True) for u in response.document_links
            ],
            "document_archives": [
                u.model_dump(exclude_none=True) for u in response.document_archives
            ],
        },
        ensure_ascii=False,
    )


def build_change_summary(result: dict) -> str:
    """中性变更摘要，不含推荐或系统判断。"""
    parts: list[str] = []
    labels = (
        ("created", "创建"),
        ("renamed", "重命名"),
        ("updated", "更新"),
        ("constraint_updated", "约束更新"),
        ("memory_updated", "记忆更新"),
        ("archived", "归档"),
        ("deleted", "删除"),
        ("events", "事件"),
        ("documents_added", "文档登记"),
        ("documents_metadata_updated", "文档元数据"),
        ("documents_linked", "文档关联"),
        ("documents_archived", "文档归档"),
    )
    for key, label in labels:
        items = result.get(key) or []
        if items:
            parts.append(f"{label} {len(items)} 项")
    skipped = result.get("skipped") or []
    if skipped:
        parts.append(f"跳过 {len(skipped)} 项")
    invalid = result.get("invalid") or []
    if invalid:
        parts.append(f"无效 {len(invalid)} 项")
    return "；".join(parts) if parts else "无变更"
