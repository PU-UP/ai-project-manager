"""Append a lightweight Agent usage record for project-manager-runtime."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tomllib


SKILL_VERSION = "1.0.4"
ROOT_DIR = Path(__file__).resolve().parents[3]
USAGE_PATH = ROOT_DIR / ".agent-workspace" / "usage" / "usage.jsonl"
FRICTION_TYPES = (
    "context_missing",
    "prompt_ambiguous",
    "schema_gap",
    "workflow_repetitive",
    "ui_gap",
    "safety_gate_needed",
    "other",
)
SEVERITIES = ("low", "medium", "high")
UPGRADE_TARGETS = (
    "skill",
    "prompt",
    "schema",
    "cli",
    "api",
    "ui",
    "logging",
    "docs",
    "other",
)


def app_version() -> str:
    try:
        data = tomllib.loads((ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8"))
        return str(data.get("project", {}).get("version") or "0.0.0")
    except OSError:
        return "0.0.0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Record project manager runtime usage.")
    parser.add_argument(
        "--action",
        required=True,
        choices=("read", "discuss", "apply", "feedback", "upgrade"),
        help="Kind of skill use",
    )
    parser.add_argument("--summary", required=True, help="Short human-readable summary")
    parser.add_argument(
        "--write-mode",
        default="none",
        choices=("none", "database", "workspace", "framework"),
        help="Where this use wrote data",
    )
    parser.add_argument("--feedback", default="", help="Optional low-frequency improvement note")
    parser.add_argument(
        "--friction-type",
        choices=FRICTION_TYPES,
        help="Optional category for the friction that may drive a future upgrade",
    )
    parser.add_argument(
        "--severity",
        choices=SEVERITIES,
        help="Optional severity for the friction note",
    )
    parser.add_argument(
        "--upgrade-target",
        choices=UPGRADE_TARGETS,
        help="Optional framework area that should be considered for upgrade",
    )
    args = parser.parse_args()

    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "skill": "project-manager-runtime",
        "skill_version": SKILL_VERSION,
        "runtime_version": app_version(),
        "action": args.action,
        "write_mode": args.write_mode,
        "summary": args.summary,
    }
    if args.feedback:
        record["feedback"] = args.feedback
    if args.friction_type:
        record["friction_type"] = args.friction_type
    if args.severity:
        record["severity"] = args.severity
    if args.upgrade_target:
        record["upgrade_target"] = args.upgrade_target

    with USAGE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(str(USAGE_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
