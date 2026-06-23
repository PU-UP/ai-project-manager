"""Legacy 系统判断解析（仅供历史查看，非默认 UI）。"""

import json


def parse_system_judgement(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
