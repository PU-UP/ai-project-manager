"""Lightweight apply episode JSONL records (minimal apply audit)."""

import json
from pathlib import Path

from app.datetime_util import now_beijing
from app.version import get_app_version

ROOT_DIR = Path(__file__).resolve().parents[2]
EPISODE_DIR = ROOT_DIR / ".agent-workspace" / "episodes"


def _unique(items: list[str]) -> list[str]:
    return sorted(set(items))


def _changed_projects(result: dict) -> list[str]:
    doc_keys = (
        "documents_added",
        "documents_metadata_updated",
        "documents_linked",
        "documents_archived",
    )
    doc_projects = []
    for key in doc_keys:
        for item in result.get(key) or []:
            if isinstance(item, str) and ":" in item:
                doc_projects.append(item.split(":", 1)[0])
    return _unique(
        (result.get("created") or [])
        + (result.get("renamed") or [])
        + (result.get("updated") or [])
        + (result.get("constraint_updated") or [])
        + (result.get("memory_updated") or [])
        + (result.get("archived") or [])
        + (result.get("deleted") or [])
        + (result.get("events") or [])
        + doc_projects
    )


def append_episode(
    *,
    user_input: str,
    raw_output: str | None,
    source: str,
    ok: bool,
    error: str | None,
    parsed=None,
    result: dict | None = None,
) -> None:
    """追加一行最小 apply 审计；不中断主流程。"""
    try:
        result = result or {}
        created_at = now_beijing()
        entry = {
            "created_at": created_at,
            "runtime_version": get_app_version(),
            "source": source,
            "ok": ok,
            "error": error,
            "user_input": user_input[:200] if user_input else "",
            "changed_projects": _changed_projects(result),
            "skipped_count": len(result.get("skipped") or []),
            "invalid_count": len(result.get("invalid") or []),
        }

        EPISODE_DIR.mkdir(parents=True, exist_ok=True)
        path = EPISODE_DIR / f"{created_at[:10]}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass
