"""logs 表与 interactions.jsonl 写入。"""

import json
from app.datetime_util import now_beijing
from app.db import INTERACTIONS_JSONL, get_connection
from app.schemas import ControlResponse
from app.services.project_updater import updates_summary


def save_log(
    user_input: str,
    ai_raw_output: str | None,
    response: ControlResponse | None,
    source: str = "agent",
) -> int:
    conn = get_connection()
    try:
        parsed_summary = updates_summary(response) if response else None
        system_judgement = None
        if response and response.system_judgement is not None:
            system_judgement = json.dumps(
                response.system_judgement.model_dump(),
                ensure_ascii=False,
            )
        now = now_beijing()
        cur = conn.execute(
            """
            INSERT INTO logs (user_input, ai_raw_output, parsed_summary, system_judgement, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_input, ai_raw_output or "", parsed_summary, system_judgement, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def append_jsonl(
    user_input: str,
    ai_raw_output: str | None,
    response: ControlResponse | None,
    updated_projects: list[str],
    source: str = "agent",
) -> None:
    try:
        INTERACTIONS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "created_at": now_beijing(),
            "source": source,
            "user_input": user_input,
            "ai_raw_output": ai_raw_output or "",
            "parsed_system_judgement": (
                response.system_judgement.model_dump()
                if response and response.system_judgement is not None
                else None
            ),
            "updated_projects": updated_projects,
        }
        with open(INTERACTIONS_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def get_latest_judgement(conn) -> dict | None:
    row = conn.execute(
        """
        SELECT system_judgement FROM logs
        WHERE system_judgement IS NOT NULL AND system_judgement != ''
        ORDER BY id DESC LIMIT 1
        """
    ).fetchone()
    if not row or not row["system_judgement"]:
        return None
    try:
        return json.loads(row["system_judgement"])
    except json.JSONDecodeError:
        return None
