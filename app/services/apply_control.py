"""统一应用控制响应（API / 表单 / CLI）。"""

import json

from app.db import get_connection, init_db
from app.schemas import ControlResponse
from app.services.control_parser import parse_control_response
from app.services.interaction_log import append_jsonl, save_log
from app.services.project_updater import apply_updates, updates_summary
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
            "project_creations": "用户明确确认新项目后创建项目；不要凭空创建。",
            "project_updates": "修改项目当前状态、价值、风险、控制动作和最新进展。",
            "project_events": "追加项目进展、反馈、风险、决策、想法或阻塞事件。",
            "project_deletions": "默认归档；只有用户明确要求彻底删除时使用 delete。",
        },
        "prompt_path": "app/prompts/project_control_panel.md",
        "prompt_hint": "请阅读上述 prompt 文件，根据用户描述、当前项目进度和近期事件输出严格 JSON。",
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
            + result["updated"]
            + result["archived"]
            + result["deleted"]
            + result["events"]
        )
    )
    append_jsonl(user_input, raw, parsed, changed_projects, source=source)

    return {
        "ok": True,
        "error": None,
        "created": result["created"],
        "updated": result["updated"],
        "archived": result["archived"],
        "deleted": result["deleted"],
        "events": result["events"],
        "skipped": result["skipped"],
        "invalid": result.get("invalid", []),
        "system_judgement": parsed.system_judgement.model_dump(),
        "parsed_summary": updates_summary(parsed),
    }
