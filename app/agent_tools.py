"""CLI：供外部 Agent 导出上下文、提交操作和复盘框架反馈。"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
import sys

from app.legacy_fields import project_for_core_export
from app.services.apply_control import apply_raw_json, build_context
from app.version import ROOT_DIR, get_app_version

USAGE_PATH = ROOT_DIR / ".agent-workspace" / "usage" / "usage.jsonl"
EPISODE_DIR = ROOT_DIR / ".agent-workspace" / "episodes"
SKILL_PATH = ROOT_DIR / "skills" / "project-manager-runtime" / "SKILL.md"
SKILL_RECORD_SCRIPT = ROOT_DIR / "skills" / "project-manager-runtime" / "scripts" / "record_usage.py"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append({"_invalid": line})
    return records


def _skill_version() -> str | None:
    if not SKILL_PATH.exists():
        return None
    for line in SKILL_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("Skill version:"):
            return line.split("`")[1] if "`" in line else line.split(":", 1)[1].strip()
    return None


def _project_event_groups(events: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        grouped[event.get("project_name", "未命名项目")].append(event)
    return [
        {
            "project_name": name,
            "recent_events": items,
        }
        for name, items in grouped.items()
    ]


def _without_empty(data: dict) -> dict:
    return {
        key: value
        for key, value in data.items()
        if value not in (None, "", [], {})
    }


def _short_text(value: str | None, limit: int = 160) -> str | None:
    if not value:
        return value
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _short_fact_list(items: list, limit: int = 3) -> list:
    if not isinstance(items, list):
        return []
    out = []
    for item in items[:limit]:
        if isinstance(item, dict):
            out.append(
                _without_empty(
                    {
                        "text": _short_text(item.get("text"), 120),
                        "source_type": item.get("source_type"),
                        "confirmation": item.get("confirmation"),
                        "source_ref": _short_text(item.get("source_ref"), 80),
                    }
                )
            )
        elif isinstance(item, str):
            out.append({"text": _short_text(item, 120), "confirmation": "legacy"})
    return out


def _short_list(items: list, limit: int = 3) -> list:
    return items[:limit] if isinstance(items, list) else []


def _brief_event(event: dict) -> dict:
    prov = event.get("decision_provenance")
    prov_brief = None
    if isinstance(prov, dict):
        prov_brief = _without_empty(
            {
                "source_type": prov.get("source_type"),
                "confirmation": prov.get("confirmation"),
                "source_ref": _short_text(prov.get("source_ref"), 80),
            }
        )
    return _without_empty(
        {
            "project_name": event.get("project_name"),
            "event_type": event.get("event_type"),
            "summary": _short_text(event.get("summary"), 140),
            "decision": _short_text(event.get("decision"), 140),
            "decision_provenance": prov_brief,
            "next_action": _short_text(event.get("next_action"), 140),
            "display_at": event.get("display_at"),
        }
    )


def _brief_document(doc: dict) -> dict:
    return _without_empty(
        {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "document_type": doc.get("document_type"),
            "source_uri": _short_text(doc.get("source_uri"), 120),
            "source_kind": doc.get("source_kind"),
            "summary": _short_text(doc.get("summary"), 160),
            "status": doc.get("status"),
            "version_or_date": doc.get("version_or_date"),
            "link_refs": doc.get("link_refs"),
        }
    )


def _brief_context(ctx: dict, group_events: bool = False) -> dict:
    recent_events = ctx.get("recent_events", [])
    projects = []
    events_by_project: dict[str, list[dict]] = defaultdict(list)
    docs_by_project: dict[str, list[dict]] = defaultdict(list)
    for event in recent_events:
        events_by_project[event.get("project_name", "")].append(event)
    for doc in ctx.get("project_documents", []):
        docs_by_project[doc.get("project_name", "")].append(doc)

    for project in ctx.get("projects", []):
        if project.get("status") == "archived":
            continue
        core = project_for_core_export(project)
        memory = _without_empty(
            {
                "origin": core.get("origin"),
                "current_goal": core.get("current_goal"),
                "progress_note": _short_text(core.get("progress_note")),
                "known_risks": _short_fact_list(core.get("known_risks", [])),
                "validated_facts": _short_fact_list(core.get("validated_facts", [])),
                "open_questions": _short_list(core.get("open_questions", [])),
                "discussion_brief": _short_text(core.get("discussion_brief")),
            }
        )
        item = _without_empty(
            {
                "id": core.get("id"),
                "name": core.get("name"),
                "status": core.get("status"),
                "latest_update": _short_text(core.get("latest_update")),
                "updated_at": core.get("updated_at"),
                "memory": memory,
                "legacy_decision_fields": core.get("legacy_decision_fields"),
                "recent_events": [
                    _brief_event(event)
                    for event in events_by_project.get(project.get("name"), [])[:3]
                ],
                "documents": [
                    _brief_document(doc)
                    for doc in docs_by_project.get(project.get("name"), [])[:5]
                ],
            }
        )
        projects.append(item)

    output = {
        "runtime": ctx.get("runtime"),
        "projects": projects,
        "archived_project_names": [
            p.get("name") for p in ctx.get("projects", []) if p.get("status") == "archived"
        ],
        "project_documents": [
            _brief_document(doc) for doc in ctx.get("project_documents", [])[:20]
        ],
        "legacy_system_judgement": ctx.get("legacy_system_judgement"),
        "agent_operations": ctx.get("agent_operations"),
        "prompt_path": ctx.get("prompt_path"),
        "prompt_hint": ctx.get("prompt_hint"),
    }
    if group_events:
        output["recent_events_by_project"] = [
            {
                "project_name": group["project_name"],
                "recent_events": [_brief_event(event) for event in group["recent_events"][:3]],
            }
            for group in _project_event_groups(recent_events)
        ]
    else:
        output["recent_events"] = [_brief_event(event) for event in recent_events[:10]]
    return output


def cmd_export(brief: bool = False, group_events: bool = False) -> None:
    ctx = build_context()
    if brief:
        ctx = _brief_context(ctx, group_events=group_events)
    elif group_events:
        ctx = dict(ctx)
        ctx["recent_events_by_project"] = _project_event_groups(ctx.get("recent_events", []))
    print(json.dumps(ctx, ensure_ascii=False, indent=2))


def cmd_apply(file_path: str | None, stdin: bool) -> None:
    if stdin or file_path == "-":
        raw = sys.stdin.read()
    elif file_path:
        with open(file_path, encoding="utf-8") as f:
            raw = f.read()
    else:
        print("请指定 --file 或使用 --stdin", file=sys.stderr)
        sys.exit(1)

    result = apply_raw_json(raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


def cmd_feedback_report() -> None:
    usage = _read_jsonl(USAGE_PATH)
    feedback = [r for r in usage if r.get("feedback") or r.get("action") == "feedback"]
    upgrades = [r for r in usage if r.get("action") == "upgrade"]
    latest_upgrade_index = max(
        (i for i, r in enumerate(usage) if r.get("action") == "upgrade"),
        default=-1,
    )
    open_feedback = [
        r for i, r in enumerate(usage)
        if (r.get("feedback") or r.get("action") == "feedback") and i > latest_upgrade_index
    ]

    by_type: dict[str, int] = defaultdict(int)
    by_target: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)
    for item in feedback:
        by_type[item.get("friction_type") or "uncategorized"] += 1
        by_target[item.get("upgrade_target") or "uncategorized"] += 1
        by_severity[item.get("severity") or "uncategorized"] += 1

    report = {
        "usage_path": str(USAGE_PATH),
        "total_usage_records": len(usage),
        "feedback_count": len(feedback),
        "upgrade_count": len(upgrades),
        "open_feedback_count_since_last_upgrade": len(open_feedback),
        "by_friction_type": dict(sorted(by_type.items())),
        "by_upgrade_target": dict(sorted(by_target.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "latest_feedback": feedback[-10:],
        "latest_upgrades": upgrades[-10:],
        "open_feedback_since_last_upgrade": open_feedback,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def run_doctor_report() -> dict:
    runtime_version = get_app_version()
    skill_version = _skill_version()
    usage = _read_jsonl(USAGE_PATH)
    episode_files = sorted(EPISODE_DIR.glob("*.jsonl")) if EPISODE_DIR.exists() else []

    checks = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add("runtime_version", bool(runtime_version), runtime_version)
    add(
        "skill_version_matches_runtime",
        skill_version == runtime_version,
        f"skill={skill_version or 'missing'}, runtime={runtime_version}",
    )
    add("usage_log_exists", USAGE_PATH.exists(), str(USAGE_PATH))
    add("episode_dir_exists", EPISODE_DIR.exists(), str(EPISODE_DIR))
    add("recent_episode_exists", bool(episode_files), episode_files[-1].name if episode_files else "none")
    add("record_usage_script_exists", SKILL_RECORD_SCRIPT.exists(), str(SKILL_RECORD_SCRIPT))
    add("usage_jsonl_parseable", not any("_invalid" in r for r in usage), f"{len(usage)} records")

    return {
        "ok": all(item["ok"] for item in checks),
        "runtime_version": runtime_version,
        "skill_version": skill_version,
        "checks": checks,
    }


def _check_boundary_references() -> tuple[bool, str]:
    agents_path = ROOT_DIR / "AGENTS.md"
    skill_path = SKILL_PATH
    agents_text = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""
    ok = (
        "docs/product-boundary.md" in agents_text
        and "docs/record-contract.md" in agents_text
        and "docs/product-boundary.md" in skill_text
        and "docs/record-contract.md" in skill_text
    )
    return ok, "AGENTS.md 与 runtime SKILL 链接 canonical contract"


def _run_subprocess(cmd: list[str], name: str) -> dict:
    try:
        completed = subprocess.run(
            cmd,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        ok = completed.returncode == 0
        detail = (completed.stdout or completed.stderr or "").strip()[:500]
        return {"name": name, "ok": ok, "detail": detail or f"exit {completed.returncode}"}
    except OSError as exc:
        return {"name": name, "ok": False, "detail": str(exc)}


def cmd_verify(*, quiet: bool = False, quick: bool = False) -> dict:
    """串联健康检查；返回报告 dict。quick=True 时跳过 pytest（供测试内调用）。"""
    checks: list[dict] = []

    checks.append(
        _run_subprocess(
            [sys.executable, "-m", "compileall", "app"],
            "python_compile",
        )
    )

    if not quick:
        checks.append(
            _run_subprocess(
                [sys.executable, "-m", "pytest", "-q"],
                "pytest",
            )
        )

    js_path = ROOT_DIR / "app" / "static" / "app.js"
    if js_path.exists():
        checks.append(
            _run_subprocess(["node", "--check", str(js_path)], "js_syntax")
        )
    else:
        checks.append({"name": "js_syntax", "ok": False, "detail": "app.js missing"})

    doctor = run_doctor_report()
    for item in doctor["checks"]:
        checks.append(item)

    boundary_ok, boundary_detail = _check_boundary_references()
    checks.append(
        {"name": "boundary_reference_check", "ok": boundary_ok, "detail": boundary_detail}
    )

    try:
        ctx = build_context()
        export_ok = "projects" in ctx and "runtime" in ctx
        checks.append(
            {
                "name": "export_smoke",
                "ok": export_ok,
                "detail": f"projects={len(ctx.get('projects', []))}",
            }
        )
    except Exception as exc:
        checks.append({"name": "export_smoke", "ok": False, "detail": str(exc)})

    report = {
        "ok": all(item["ok"] for item in checks),
        "runtime_version": get_app_version(),
        "checks": checks,
    }
    if not quiet:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def cmd_doctor() -> None:
    report = run_doctor_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["ok"] else 1)


def main_export() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", action="store_true", help="导出简版上下文")
    parser.add_argument("--group-events", action="store_true", help="按项目聚合近期事件")
    args = parser.parse_args()
    cmd_export(brief=args.brief, group_events=args.group_events)


def main_apply() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", help="JSON 文件路径，- 表示 stdin")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取")
    args = parser.parse_args()
    cmd_apply(args.file, args.stdin)


def main_verify() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="跳过 pytest")
    args = parser.parse_args()
    report = cmd_verify(quick=args.quick)
    sys.exit(0 if report["ok"] else 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI项目管家 Agent 工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="导出当前项目态 JSON")
    p_export.add_argument("--brief", action="store_true", help="导出简版上下文")
    p_export.add_argument("--group-events", action="store_true", help="按项目聚合近期事件")

    p_apply = sub.add_parser("apply", help="应用 Agent 产出的 JSON")
    p_apply.add_argument("--file", "-f", help="JSON 文件路径")
    p_apply.add_argument("--stdin", action="store_true", help="从 stdin 读取")

    sub.add_parser("feedback-report", help="汇总框架使用反馈（仅事实）")
    sub.add_parser("doctor", help="检查运行时、技能版本和本地记录健康状态")
    p_verify = sub.add_parser("verify", help="全量工程健康检查")
    p_verify.add_argument("--quick", action="store_true", help="跳过 pytest（测试内使用）")

    args = parser.parse_args()
    if args.command == "export":
        cmd_export(brief=args.brief, group_events=args.group_events)
    elif args.command == "apply":
        cmd_apply(getattr(args, "file", None), getattr(args, "stdin", False))
    elif args.command == "feedback-report":
        cmd_feedback_report()
    elif args.command == "doctor":
        cmd_doctor()
    elif args.command == "verify":
        report = cmd_verify(quick=getattr(args, "quick", False))
        sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
