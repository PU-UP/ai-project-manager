"""表 DDL 与枚举常量。"""

STATUSES = ("active", "maintain", "observe", "paused", "archived")
RISK_LEVELS = ("low", "medium", "high")
PROJECT_EVENT_TYPES = (
    "progress",
    "decision",
    "risk",
    "feedback",
    "idea",
    "blocker",
    "note",
)
CONTROL_ACTIONS = (
    "continue",
    "maintain",
    "observe",
    "pause",
    "delegate_to_ai",
    "human_intervene",
    "seek_feedback",
    "narrow_scope",
    "change_metric",
    "archive",
)

# 项目名别名（小写）→ 正式名称
PROJECT_ALIASES: dict[str, str] = {
    "hermes": "Hermes每日任务",
    "hermes每日任务": "Hermes每日任务",
    "alpha": "Alpha mining",
    "alpha mining": "Alpha mining",
    "晚餐": "晚餐推荐",
    "晚餐推荐": "晚餐推荐",
    "周末": "周末去哪玩",
    "周末去哪玩": "周末去哪玩",
    "工作": "工作掌控力",
    "工作掌控力": "工作掌控力",
    "投资": "投资学习",
    "投资学习": "投资学习",
    "ai客服": "AI客服",
    "股票": "股票分析",
    "股票分析": "股票分析",
}

CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    value_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    risk_note TEXT NOT NULL DEFAULT '',
    ai_delegation_level INTEGER NOT NULL,
    human_intervention_level INTEGER NOT NULL,
    control_action TEXT NOT NULL,
    control_action_note TEXT NOT NULL DEFAULT '',
    latest_update TEXT NOT NULL DEFAULT '',
    project_constraint TEXT NOT NULL DEFAULT '',
    origin TEXT NOT NULL DEFAULT '',
    current_goal TEXT NOT NULL DEFAULT '',
    progress_percent INTEGER NOT NULL DEFAULT 0,
    progress_note TEXT NOT NULL DEFAULT '',
    key_judgements TEXT NOT NULL DEFAULT '[]',
    validated_facts TEXT NOT NULL DEFAULT '[]',
    open_questions TEXT NOT NULL DEFAULT '[]',
    known_risks TEXT NOT NULL DEFAULT '[]',
    discussion_brief TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

PROJECT_MEMORY_COLUMNS = {
    "origin": "TEXT NOT NULL DEFAULT ''",
    "current_goal": "TEXT NOT NULL DEFAULT ''",
    "progress_percent": "INTEGER NOT NULL DEFAULT 0",
    "progress_note": "TEXT NOT NULL DEFAULT ''",
    "key_judgements": "TEXT NOT NULL DEFAULT '[]'",
    "validated_facts": "TEXT NOT NULL DEFAULT '[]'",
    "open_questions": "TEXT NOT NULL DEFAULT '[]'",
    "discussion_brief": "TEXT NOT NULL DEFAULT ''",
    "known_risks": "TEXT NOT NULL DEFAULT '[]'",
}

CREATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_input TEXT NOT NULL,
    ai_raw_output TEXT,
    parsed_summary TEXT,
    system_judgement TEXT,
    created_at TEXT NOT NULL
);
"""

CREATE_PROJECT_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS project_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    project_name TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'progress',
    summary TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL DEFAULT '',
    decision_provenance TEXT NOT NULL DEFAULT '',
    next_action TEXT NOT NULL DEFAULT '',
    happened_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);
"""

EVENT_PROVENANCE_COLUMNS = {
    "decision_provenance": "TEXT NOT NULL DEFAULT ''",
}

DOCUMENT_STATUSES = ("current", "stale", "superseded", "unknown")

CREATE_PROJECT_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS project_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL DEFAULT '',
    source_uri TEXT NOT NULL DEFAULT '',
    source_kind TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    version_or_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'current',
    added_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""
