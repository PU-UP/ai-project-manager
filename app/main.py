"""
AI项目管家 — 项目档案与上下文展示。

由外部 Agent 维护项目记忆与事件记录；页面展示确定性档案快照，不展示 Agent 控制建议。
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
from app.labels import DOCUMENT_STATUS_LABELS, EVENT_LABELS, STATUS_LABELS
from app.provenance import confirmation_label, source_type_label
from app.services.apply_control import apply_raw_json, build_context
from app.services.context_snapshot import build_portfolio_snapshot
from app.services.project_updater import list_projects, list_recent_events

load_dotenv(ROOT_DIR / ".env")

APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
templates.env.globals["status_label"] = lambda s: STATUS_LABELS.get(s, s)
templates.env.globals["event_label"] = lambda e: EVENT_LABELS.get(e, e)
templates.env.globals["confirmation_label"] = confirmation_label
templates.env.globals["source_type_label"] = source_type_label
templates.env.globals["document_status_label"] = lambda s: DOCUMENT_STATUS_LABELS.get(s, s)
templates.env.globals["static_version"] = lambda name: int(
    (APP_DIR / "static" / name).stat().st_mtime
)


def _snapshot_stats(snapshot: dict) -> dict:
    counts = snapshot["status_counts"]
    return {
        "total": snapshot["total"],
        "active": counts.get("active", 0),
        "recently_updated": snapshot["recently_updated_count"],
        "stale": snapshot["stale_count"],
        "missing_memory": snapshot["missing_memory_count"],
        "pending_confirmation": snapshot["pending_confirmation_count"],
    }


app = FastAPI(title="AI项目管家", description="项目档案与上下文面板")
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
        snapshot = build_portfolio_snapshot(projects)
    finally:
        conn.close()

    flash = _parse_flash(request.query_params)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "projects": projects,
            "snapshot": snapshot,
            "recent_events": recent_events,
            "flash": flash,
            "stats": _snapshot_stats(snapshot),
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
        from app.services.document_index import list_documents

        documents = list_documents(conn, project_id=project_id)
    finally:
        conn.close()
    if not row:
        return HTMLResponse("项目不存在", status_code=404)
    from app.legacy_fields import project_for_core_export
    from app.schemas import row_to_project_dict

    project = project_for_core_export(row_to_project_dict(row))
    return templates.TemplateResponse(
        request, "project.html", {"project": project, "events": events, "documents": documents}
    )


@app.get("/api/snapshot")
async def api_snapshot():
    conn = get_connection()
    try:
        projects = list_projects(conn)
        return JSONResponse(build_portfolio_snapshot(projects))
    finally:
        conn.close()


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
            "document_adds",
            "document_metadata_updates",
            "document_links",
            "document_archives",
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
