"""系统判断展示辅助。"""

import json


def parse_system_judgement(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def judgement_lists(judgement: dict | None) -> dict:
    if not judgement:
        return {
            "summary": None,
            "real_progress": [],
            "pseudo_progress_risk": [],
            "delegate_to_ai": [],
            "need_human_intervention": [],
            "pause_or_ignore": [],
            "top_control_recommendation": None,
        }
    top = judgement.get("top_control_recommendation")
    return {
        "summary": judgement.get("summary"),
        "real_progress": judgement.get("real_progress") or [],
        "pseudo_progress_risk": judgement.get("pseudo_progress_risk") or [],
        "delegate_to_ai": judgement.get("delegate_to_ai") or [],
        "need_human_intervention": judgement.get("need_human_intervention") or [],
        "pause_or_ignore": judgement.get("pause_or_ignore") or [],
        "top_control_recommendation": top,
    }
