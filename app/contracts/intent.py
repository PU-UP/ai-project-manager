"""用户意图 → Context / Record / Handoff 判定。

契约来源：docs/product-boundary.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

IntentMode = Literal["context", "record", "handoff"]

CONTRACT_REF = "docs/product-boundary.md"
FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "intent_matrix.json"

# 先匹配更具体的 Context，避免「记录了什么」被 Record 规则误伤。
_CONTEXT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"记录了什么", "context-recap"),
    (r"未决问题", "context-open-questions"),
    (r"冲突了吗", "context-conflict-check"),
    (r"档案里分别", "context-neutral-compare"),
    (r"现在记[录载]了", "context-recap"),
)

_HANDOFF_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"深入研究", "handoff-deep-research"),
    (r"决定.{0,12}路线|路线.{0,12}决定", "handoff-route-decision"),
    (r"反复迭代", "handoff-iterate"),
    (r"迭代.{0,12}直到", "handoff-iterate-until"),
    (r"写代码|做投研|投研报告", "handoff-execution"),
    (r"哪个更值得", "handoff-value-compare"),
    (r"pause.{0,6}continue|该\s*pause\s*还是\s*continue", "handoff-control-decision"),
    (r"评估.{0,12}风险等级", "handoff-risk-rating"),
    (r"替我在", "handoff-delegate-execution"),
)

_RECORD_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"整理到|整理进", "record-organize"),
    (r"记录这|记录：|记录:", "record-explicit"),
    (r"^记录", "record-explicit"),
    (r"保存|写入|归档|创建项目", "record-save"),
)


def _first_match(text: str, patterns: tuple[tuple[str, str], ...]) -> str | None:
    for pattern, _rule_id in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return _rule_id
    return None


def classify_intent(user_input: str) -> IntentMode:
    """按 product-boundary 规则判定运行模式。"""
    text = user_input.strip()
    if not text:
        return "context"

    if _first_match(text, _CONTEXT_PATTERNS):
        return "context"
    if _first_match(text, _HANDOFF_PATTERNS):
        return "handoff"
    if _first_match(text, _RECORD_PATTERNS):
        return "record"
    return "context"


def load_intent_matrix() -> dict:
    """加载结构化 intent matrix fixture。"""
    with FIXTURE_PATH.open(encoding="utf-8") as f:
        return json.load(f)
