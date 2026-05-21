"""统一 JSON 解析与校验（Web/CLI/API/LLM 共用）。"""

import json
import re

from pydantic import ValidationError

from app.schemas import ControlResponse

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def strip_markdown_json(raw: str) -> str:
    text = raw.strip()
    text = _JSON_FENCE.sub("", text).strip()
    return text


def parse_control_response(raw: str) -> tuple[ControlResponse | None, str | None]:
    if not raw or not raw.strip():
        return None, "输出为空"
    try:
        text = strip_markdown_json(raw)
        data = json.loads(text)
        return ControlResponse.model_validate(data), None
    except json.JSONDecodeError as e:
        return None, f"JSON 解析失败: {e}"
    except ValidationError as e:
        return None, f"数据校验失败: {e}"
