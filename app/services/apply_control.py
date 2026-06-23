"""统一应用控制响应（API / 表单 / CLI）。"""

import json

from app.db import get_connection, init_db
from app.schemas import ControlResponse
from app.services.control_parser import parse_control_response
from app.services.episode_log import append_episode
from app.services.interaction_log import append_jsonl, save_log
from app.services.project_updater import apply_updates, build_change_summary, updates_summary
from app.version import get_app_version


def build_context() -> dict:
    init_db()
    conn = get_connection()
    try:
        from app.services.interaction_log import get_latest_judgement
        from app.services.project_updater import list_projects, list_recent_events

        projects = list_projects(conn)
        recent_events = list_recent_events(conn, limit=30)
        latest_judgement = get_latest_judgement(conn)
    finally:
        conn.close()
    return {
        "runtime": {
            "name": "AI项目管家",
            "version": get_app_version(),
            "role": "项目档案管理员 + 上下文编排器 + 轻量会议秘书",
            "principle": "默认只读恢复与复述；显式确认后才写入；越界任务交接后停止。",
            "contracts": {
                "product_boundary": "docs/product-boundary.md",
                "record_contract": "docs/record-contract.md",
            },
        },
        "projects": projects,
        "recent_events": recent_events,
        "latest_system_judgement": latest_judgement,
        "agent_operations": {
            "context_mode": "默认只读：恢复、复述、指出缺口、最多 1–3 个澄清问题；不产出 apply JSON。",
            "record_mode": "用户明确记录或确认写入摘要后：输出严格 JSON 并 apply；不需 system_judgement；见 docs/record-contract.md。",
            "handoff_mode": "深度研究、方案迭代、路线决策或项目外执行：输出 context packet 后停止；见 docs/product-boundary.md。",
            "project_creations": "用户明确确认新项目后创建；不要凭空创建。",
            "project_renames": "重命名已有项目，并同步历史事件中的项目显示名。",
            "project_updates": "用户明确要求的 status 或 latest_update 等字段变更。",
            "project_constraint_updates": "更新已有项目的范围约束。",
            "project_memory_updates": "用户确认后的长期记忆：origin、current_goal、validated_facts、open_questions、discussion_brief。",
            "project_events": "追加进展、反馈、决策、风险、想法或阻塞事件。",
            "project_deletions": "默认归档；彻底删除需 mode=delete 且 confirm_explicit=true。",
        },
        "prompt_path": "app/prompts/project_control_panel.md",
        "prompt_hint": "完整边界见 docs/product-boundary.md；写入规则见 docs/record-contract.md。讨论时自然语言回答；Record Mode 才输出严格 JSON。",
    }


def apply_raw_json(
    raw: str,
    user_input: str = "[external-agent]",
    source: str = "agent",
) -> dict:
    init_db()
    parsed, err = parse_control_response(raw)
    if err or not parsed:
        save_log(user_input, raw, None, source=source)
        append_jsonl(user_input, raw, None, [], source=source)
        append_episode(
            user_input=user_input,
            raw_output=raw,
            source=source,
            ok=False,
            error=err or "解析失败",
        )
        return {
            "ok": False,
            "error": err or "解析失败",
            "updated": [],
            "skipped": [],
        }

    conn = get_connection()
    try:
        result = apply_updates(conn, parsed)
    finally:
        conn.close()

    save_log(user_input, raw, parsed, source=source)
    changed_projects = sorted(
        set(
            result["created"]
            + result["renamed"]
            + result["updated"]
            + result["constraint_updated"]
            + result["memory_updated"]
            + result["archived"]
            + result["deleted"]
            + result["events"]
        )
    )
    append_jsonl(user_input, raw, parsed, changed_projects, source=source)
    append_episode(
        user_input=user_input,
        raw_output=raw,
        source=source,
        ok=True,
        error=None,
        parsed=parsed,
        result=result,
    )

    return {
        "ok": True,
        "error": None,
        "created": result["created"],
        "renamed": result["renamed"],
        "updated": result["updated"],
        "constraint_updated": result["constraint_updated"],
        "memory_updated": result["memory_updated"],
        "archived": result["archived"],
        "deleted": result["deleted"],
        "events": result["events"],
        "skipped": result["skipped"],
        "invalid": result.get("invalid", []),
        "change_summary": build_change_summary(result),
        "system_judgement": (
            parsed.system_judgement.model_dump()
            if parsed.system_judgement is not None
            else None
        ),
        "parsed_summary": updates_summary(parsed),
    }
