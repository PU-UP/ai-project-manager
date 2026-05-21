"""界面展示用中文标签。"""

STATUS_LABELS = {
    "active": "当前推进",
    "maintain": "维持运行",
    "observe": "观察孵化",
    "paused": "短期暂停",
    "archived": "历史归档",
}

RISK_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
}

ACTION_LABELS = {
    "continue": "继续",
    "maintain": "维持",
    "observe": "观察",
    "pause": "暂停",
    "delegate_to_ai": "AI执行",
    "human_intervene": "人工介入",
    "seek_feedback": "找反馈",
    "narrow_scope": "收窄",
    "change_metric": "调标准",
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
