"""Lightweight apply episode JSONL records for future framework review."""

import json
from pathlib import Path

from app.datetime_util import now_beijing
from app.schemas import ControlResponse
from app.services.project_updater import updates_summary
from app.version import get_app_version

ROOT_DIR = Path(__file__).resolve().parents[2]
EPISODE_DIR = ROOT_DIR / ".agent-workspace" / "episodes"
PROMPT_PATH = "app/prompts/project_control_panel.md"


def _unique(items: list[str]) -> list[str]:
    return sorted(set(items))


def append_episode(
    *,
    user_input: str,
    raw_output: str | None,
    source: str,
    ok: bool,
    error: str | None,
    parsed: ControlResponse | None = None,
    result: dict | None = None,
) -> None:
    """Append one compact apply episode; never interrupt the main apply flow."""
    try:
        result = result or {}
        created = result.get("created", [])
        renamed = result.get("renamed", [])
        updated = result.get("updated", [])
        constraint_updated = result.get("constraint_updated", [])
        memory_updated = result.get("memory_updated", [])
        archived = result.get("archived", [])
        deleted = result.get("deleted", [])
        events = result.get("events", [])
        changed_projects = _unique(
            created
            + renamed
            + updated
            + constraint_updated
            + memory_updated
            + archived
            + deleted
            + events
        )
        created_at = now_beijing()

        entry = {
            "created_at": created_at,
            "runtime_version": get_app_version(),
            "source": source,
            "ok": ok,
            "error": error,
            "user_input": user_input,
            "raw_output": raw_output or "",
            "parsed_summary": updates_summary(parsed) if parsed else None,
            "system_judgement_summary": (
                parsed.system_judgement.summary
                if parsed and parsed.system_judgement is not None
                else None
            ),
            "changed_projects": changed_projects,
            "created": created,
            "renamed": renamed,
            "updated": updated,
            "constraint_updated": constraint_updated,
            "memory_updated": memory_updated,
            "archived": archived,
            "deleted": deleted,
            "events": events,
            "skipped": result.get("skipped", []),
            "invalid": result.get("invalid", []),
            "prompt_path": PROMPT_PATH,
        }

        EPISODE_DIR.mkdir(parents=True, exist_ok=True)
        path = EPISODE_DIR / f"{created_at[:10]}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass
