"""界面展示用中文标签。"""

STATUS_LABELS = {
    "active": "推进中",
    "maintain": "维持",
    "observe": "观察",
    "paused": "暂停",
    "archived": "归档",
}

RISK_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
}

ACTION_LABELS = {
    "continue": "继续推进",
    "maintain": "低成本维持",
    "observe": "继续观察",
    "pause": "暂停",
    "delegate_to_ai": "交给 AI",
    "human_intervene": "亲自介入",
    "seek_feedback": "寻求反馈",
    "narrow_scope": "缩小范围",
    "change_metric": "调整标准",
    "archive": "归档",
}

EVENT_LABELS = {
    "progress": "进展",
    "decision": "决策",
    "risk": "风险",
    "feedback": "反馈",
    "idea": "想法",
    "blocker": "阻塞",
    "note": "记录",
}

JUDGEMENT_SECTIONS = {
    "real_progress": ("真推进", "positive"),
    "pseudo_progress_risk": ("假性推进", "warning"),
    "delegate_to_ai": ("交给 AI", "ai"),
    "need_human_intervention": ("需我介入", "human"),
    "pause_or_ignore": ("暂停/忽略", "muted"),
}
