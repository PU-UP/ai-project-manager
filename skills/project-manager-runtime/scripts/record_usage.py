"""Append a lightweight Agent usage record for project-manager-runtime."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tomllib


SKILL_VERSION = "0.2.0"
ROOT_DIR = Path(__file__).resolve().parents[3]
USAGE_PATH = ROOT_DIR / ".agent-workspace" / "usage" / "usage.jsonl"


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

    with USAGE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(str(USAGE_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
