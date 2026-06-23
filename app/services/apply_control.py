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
            "role": "外部 Agent 使用的个人项目经理工程框架",
            "principle": "用户自然语言描述，Agent 负责读取、判断、写入、维护和可视化。",
        },
        "projects": projects,
        "recent_events": recent_events,
        "latest_system_judgement": latest_judgement,
        "agent_operations": {
            "project_discussion_mode": "讨论、梳理或追问项目时，默认只读取项目记忆和近期事件并自然语言回答；只有用户明确要求或确认记录后才写入。",
            "project_creations": "用户明确确认新项目后创建项目；不要凭空创建。",
            "project_renames": "重命名已有项目，并同步历史事件中的项目显示名。",
            "project_updates": "修改项目当前状态、价值、风险、控制动作和最新进展。",
            "project_constraint_updates": "更新已有项目的范围约束或防蔓延约束。",
            "project_memory_updates": "更新项目长期记忆，包括初衷、当前目标、阶段进度、关键判断、已验证事实、未验证问题和讨论摘要。",
            "project_events": "追加项目进展、反馈、风险、决策、想法或阻塞事件。",
            "project_deletions": "默认归档；只有用户明确要求彻底删除时使用 delete。",
        },
        "prompt_path": "app/prompts/project_control_panel.md",
        "prompt_hint": "请阅读上述 prompt 文件；项目讨论时自然语言回答且默认不写入，生成 apply payload 时才输出严格 JSON。",
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
