"""根据 Agent 返回的项目经理操作更新数据库。"""

import json
from app.datetime_util import now_beijing
from app.models import PROJECT_ALIASES
from app.schemas import (
    ControlResponse,
    ProjectCreation,
    ProjectDeletion,
    ProjectEventInput,
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
    conn.execute(
        """
        INSERT INTO project_events (
            project_id, project_name, event_type, summary, evidence,
            decision, next_action, happened_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project["id"],
            project["name"],
            item.event_type,
            item.summary,
            item.evidence or "",
            item.decision or "",
            item.next_action or "",
            item.happened_at,
            now,
        ),
    )
    return project["name"]


def apply_deletion(conn, item: ProjectDeletion, project: dict, now: str) -> str:
    reason = item.reason or "由 Agent 根据用户意图处理"
    if item.mode == "delete":
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
    updated: list[str] = []
    archived: list[str] = []
    deleted: list[str] = []
    events: list[str] = []
    skipped: list[str] = []
    invalid: list[dict] = []
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

    for item in response.project_updates:
        project = match_project(item.project_name, projects)
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

    for item in response.project_deletions:
        project = match_project(item.project_name, projects)
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
        project = match_project(item.project_name, projects)
        if not project:
            skipped.append(item.project_name)
            continue
        try:
            events.append(append_project_event(conn, item, project, now))
        except Exception as e:
            invalid.append({"project": item.project_name, "error": str(e)})

    conn.commit()
    return {
        "created": created,
        "updated": updated,
        "archived": archived,
        "deleted": deleted,
        "events": events,
        "skipped": skipped,
        "invalid": invalid,
    }


def updates_summary(response: ControlResponse) -> str:
    return json.dumps(
        {
            "project_creations": [
                u.model_dump(exclude_none=True) for u in response.project_creations
            ],
            "project_updates": [
                u.model_dump(exclude_none=True) for u in response.project_updates
            ],
            "project_events": [
                u.model_dump(exclude_none=True) for u in response.project_events
            ],
            "project_deletions": [
                u.model_dump(exclude_none=True) for u in response.project_deletions
            ],
        },
        ensure_ascii=False,
    )
