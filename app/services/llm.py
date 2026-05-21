"""可选内置 LLM：ENABLE_BUILTIN_LLM=false|true|mock"""

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.db import ROOT_DIR
from app.services.control_parser import parse_control_response

load_dotenv(ROOT_DIR / ".env")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "project_control_panel.md"


def get_llm_mode() -> str:
    return os.getenv("ENABLE_BUILTIN_LLM", "false").strip().lower()


def is_builtin_enabled() -> bool:
    mode = get_llm_mode()
    return mode in ("true", "1", "yes")


def is_mock_mode() -> bool:
    return get_llm_mode() == "mock"


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def mock_response(user_input: str) -> str:
    """验收用固定 mock，覆盖常见自然语言场景。"""
    payload = {
        "project_updates": [
            {
                "project_name": "Hermes每日任务",
                "status": "active",
                "value_score": 2,
                "risk_level": "medium",
                "risk_note": "日报仍然偏泛泛，存在自动运行但不改变行动的假性推进风险",
                "ai_delegation_level": 3,
                "human_intervention_level": 3,
                "control_action": "change_metric",
                "control_action_note": "重新定义日报评价标准，要求每次输出至少一个可行动建议",
                "latest_update": "用户反馈 Hermes 日报仍然泛泛",
                "reason": "输出没有形成行动闭环",
            },
            {
                "project_name": "Alpha mining",
                "latest_update": "用户今日未关注，继续低成本维持",
                "control_action": "maintain",
                "control_action_note": "无正式 offer 前保持自动运行即可",
            },
            {
                "project_name": "晚餐推荐",
                "status": "active",
                "value_score": 4,
                "risk_level": "medium",
                "risk_note": "需避免扩展为 APP",
                "ai_delegation_level": 4,
                "human_intervention_level": 2,
                "control_action": "delegate_to_ai",
                "control_action_note": "先做消息推送验证 7 天，不做 APP",
                "latest_update": "用户想先试推送方案",
            },
            {
                "project_name": "工作掌控力",
                "status": "active",
                "value_score": 5,
                "risk_level": "medium",
                "risk_note": "本周对关键模块了解不足，技术判断力可能下降",
                "ai_delegation_level": 1,
                "human_intervention_level": 5,
                "control_action": "human_intervene",
                "control_action_note": "本周至少亲自介入一个关键技术点或评审关键模块",
                "latest_update": "用户反馈本周未深入关键模块",
            },
        ],
        "system_judgement": {
            "summary": "当前核心问题不是缺少项目，而是 Hermes 可能假性推进、工作掌控力需亲自介入；晚餐推荐有明确验证路径。",
            "real_progress": ["晚餐推荐有明确生活场景，可低成本验证推送"],
            "pseudo_progress_risk": [
                "Hermes每日任务可能只是持续输出信息，但没有改变行动",
            ],
            "delegate_to_ai": [
                "Alpha mining 继续低成本自动运行",
                "晚餐推荐可交给 AI 生成消息推送",
            ],
            "need_human_intervention": [
                "工作掌控力需要用户亲自介入一个关键技术点",
                "Hermes每日任务需要用户重新定义价值评价标准",
            ],
            "pause_or_ignore": [
                "AI客服除非有客户反馈，否则继续暂停",
                "股票分析暂时不恢复",
            ],
            "top_control_recommendation": {
                "control_action": "change_metric",
                "project_name": "Hermes每日任务",
                "note": "先修正 Hermes 日报的价值评价标准，否则继续运行只会增加噪声",
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False)


async def analyze(user_input: str, projects: list[dict]) -> tuple[str, str | None]:
    """
    返回 (raw_output, error_message)。
    error_message 非空表示未调用模型或调用失败。
    """
    if is_mock_mode():
        return mock_response(user_input), None

    if not is_builtin_enabled():
        return "", "builtin_llm_disabled"

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "", "missing_api_key"

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    system = load_system_prompt()
    user_content = (
        "当前所有项目状态（JSON）：\n"
        + json.dumps(projects, ensure_ascii=False, indent=2)
        + "\n\n用户今日输入：\n"
        + user_input
        + "\n\n请仅输出严格 JSON，无 markdown。"
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content, None
    except Exception as e:
        return "", str(e)


def analyze_sync(user_input: str, projects: list[dict]) -> tuple[str, str | None]:
    import asyncio

    return asyncio.run(analyze(user_input, projects))
