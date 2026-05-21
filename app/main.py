"""
AI项目管家 — 给外部 Agent 使用的个人项目经理工程框架。

不是：Notion 替代品、Todo List、日程管理、复杂 PM、多用户 SaaS、
大型 Dashboard、自动创业系统、每日打卡、投资决策系统、工作汇报系统。

是：由外部 Agent 按规则维护项目记忆、事件记录与控制判断，
并展示近期项目局面、价值、风险、AI 接管程度与下一控制动作。
"""

import json
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import ROOT_DIR, get_connection, init_db
from app.labels import ACTION_LABELS, EVENT_LABELS, RISK_LABELS, STATUS_LABELS
from app.services.apply_control import apply_raw_json, build_context
from app.services.control_analyzer import judgement_lists
from app.services.interaction_log import get_latest_judgement
from app.services.project_updater import list_projects, list_recent_events

load_dotenv(ROOT_DIR / ".env")

APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
templates.env.globals["status_label"] = lambda s: STATUS_LABELS.get(s, s)
templates.env.globals["risk_label"] = lambda r: RISK_LABELS.get(r, r)
templates.env.globals["action_label"] = lambda a: ACTION_LABELS.get(a, a)
templates.env.globals["event_label"] = lambda e: EVENT_LABELS.get(e, e)


def _project_stats(projects: list[dict]) -> dict:
    return {
        "total": len(projects),
        "active": sum(1 for p in projects if p.get("status") == "active"),
        "high_risk": sum(1 for p in projects if p.get("risk_level") == "high"),
        "need_human": sum(
            1 for p in projects if (p.get("human_intervention_level") or 0) >= 4
        ),
    }

app = FastAPI(title="AI项目管家", description="个人项目进度控制面板")
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = get_connection()
    try:
        projects = list_projects(conn)
        recent_events = list_recent_events(conn, limit=100)
        judgement = get_latest_judgement(conn)
    finally:
        conn.close()

    j = judgement_lists(judgement)
    flash = _parse_flash(request.query_params)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "projects": projects,
            "judgement": j,
            "recent_events": recent_events,
            "flash": flash,
            "stats": _project_stats(projects),
        },
    )


def _parse_flash(params) -> dict | None:
    if params.get("result") != "ok" and params.get("result") != "error":
        if not params.get("message"):
            return None
    flash = {
        "result": params.get("result", "error"),
        "message": params.get("message", ""),
        "updated": [x for x in params.get("updated", "").split("|") if x],
        "skipped": [x for x in params.get("skipped", "").split("|") if x],
    }
    if params.get("judgement"):
        try:
            flash["judgement"] = json.loads(urllib.parse.unquote(params["judgement"]))
        except json.JSONDecodeError:
            flash["judgement"] = None
    return flash


@app.get("/project/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        events = list_recent_events(conn, limit=20, project_id=project_id)
    finally:
        conn.close()
    if not row:
        return HTMLResponse("项目不存在", status_code=404)
    from app.schemas import row_to_project_dict

    project = row_to_project_dict(row)
    return templates.TemplateResponse(
        request, "project.html", {"project": project, "events": events}
    )


@app.get("/api/context")
async def api_context():
    return JSONResponse(build_context())


@app.get("/api/projects")
async def api_projects():
    conn = get_connection()
    try:
        return JSONResponse({"projects": list_projects(conn)})
    finally:
        conn.close()


@app.get("/api/events")
async def api_events(limit: int = 30):
    conn = get_connection()
    try:
        safe_limit = max(1, min(limit, 100))
        return JSONResponse({"events": list_recent_events(conn, limit=safe_limit)})
    finally:
        conn.close()


@app.post("/api/apply")
async def api_apply(request: Request):
    body = await request.json()
    user_input = body.get("user_input", "[external-agent]")
    if any(
        key in body
        for key in (
            "project_creations",
            "project_renames",
            "project_updates",
            "project_constraint_updates",
            "project_memory_updates",
            "project_events",
            "project_deletions",
            "system_judgement",
        )
    ):
        raw = json.dumps(body, ensure_ascii=False)
    else:
        raw = body.get("raw") or body.get("json") or ""
        if isinstance(raw, dict):
            raw = json.dumps(raw, ensure_ascii=False)
    result = apply_raw_json(raw, user_input=user_input, source="agent")
    return JSONResponse(result)
