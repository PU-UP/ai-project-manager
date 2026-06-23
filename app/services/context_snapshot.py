"""确定性组合上下文快照（不调用 LLM）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.datetime_util import BEIJING, _parse_timestamp

STALE_DAYS = 30
RECENT_DAYS = 14
TRACKED_STATUSES = frozenset({"active", "maintain", "observe"})

MEMORY_FIELDS = ("origin", "current_goal", "discussion_brief")


def _missing_memory_fields(project: dict) -> list[str]:
    missing: list[str] = []
    for field in MEMORY_FIELDS:
        if not (project.get(field) or "").strip():
            missing.append(field)
    facts = project.get("validated_facts") or []
    questions = project.get("open_questions") or []
    if not facts and not questions:
        missing.append("validated_facts_or_open_questions")
    return missing


def _project_age_days(project: dict, now: datetime) -> int | None:
    ts = _parse_timestamp(project.get("updated_at") or project.get("created_at") or "")
    if ts is None:
        return None
    return max(0, (now - ts).days)


def build_portfolio_snapshot(projects: list[dict]) -> dict:
    """由 projects 表字段确定性计算组合快照。"""
    now = datetime.now(BEIJING)
    status_counts = {
        "active": 0,
        "maintain": 0,
        "observe": 0,
        "paused": 0,
        "archived": 0,
    }
    recently_updated: list[dict] = []
    stale_projects: list[dict] = []
    missing_memory: list[dict] = []
    pending_confirmation: list[dict] = []

    for project in projects:
        status = project.get("status") or "observe"
        if status in status_counts:
            status_counts[status] += 1

        age_days = _project_age_days(project, now)
        entry = {
            "id": project["id"],
            "name": project["name"],
            "status": status,
            "updated_at": project.get("updated_at"),
        }

        if age_days is not None and age_days <= RECENT_DAYS:
            recently_updated.append({**entry, "days_since_update": age_days})

        if (
            status in TRACKED_STATUSES
            and age_days is not None
            and age_days >= STALE_DAYS
        ):
            stale_projects.append({**entry, "days_since_update": age_days})

        if status != "archived":
            missing = _missing_memory_fields(project)
            if missing:
                missing_memory.append({**entry, "missing_fields": missing})

        questions = project.get("open_questions") or []
        if questions and status != "archived":
            pending_confirmation.append(
                {
                    **entry,
                    "open_questions_count": len(questions),
                }
            )

    recently_updated.sort(key=lambda x: x.get("days_since_update", 999))
    stale_projects.sort(key=lambda x: -x.get("days_since_update", 0))

    return {
        "computed_at": now.strftime("%Y-%m-%d %H:%M"),
        "total": len(projects),
        "status_counts": status_counts,
        "recently_updated_count": len(recently_updated),
        "recently_updated": recently_updated[:10],
        "stale_count": len(stale_projects),
        "stale_projects": stale_projects[:10],
        "missing_memory_count": len(missing_memory),
        "missing_memory": missing_memory[:10],
        "pending_confirmation_count": len(pending_confirmation),
        "pending_confirmation": pending_confirmation[:10],
        "thresholds": {"stale_days": STALE_DAYS, "recent_days": RECENT_DAYS},
    }
