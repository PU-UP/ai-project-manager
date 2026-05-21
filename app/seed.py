"""初始化数据库与 8 个种子项目。运行: uv run python -m app.seed [--force]"""

import argparse
import sys
from app.datetime_util import now_beijing
from app.db import get_connection, init_db


SEED_PROJECTS = [
    {
        "name": "Hermes每日任务",
        "status": "active",
        "value_score": 2,
        "risk_level": "medium",
        "risk_note": "有一定价值，但输出可能泛泛，缺少从信息到行动的闭环",
        "ai_delegation_level": 3,
        "human_intervention_level": 3,
        "control_action": "change_metric",
        "control_action_note": "需要重新定义日报价值标准，让它输出可行动建议",
        "latest_update": "已运行一段时间，有价值但不够明确",
        "project_constraint": "只优化信息到判断到行动的转化，不扩展复杂架构",
    },
    {
        "name": "Alpha mining",
        "status": "maintain",
        "value_score": 3,
        "risk_level": "low",
        "risk_note": "没有正式 offer 前，不适合投入过多精力",
        "ai_delegation_level": 4,
        "human_intervention_level": 1,
        "control_action": "maintain",
        "control_action_note": "继续低成本自动运行，等待正式 offer 再考虑优化",
        "latest_update": "已达到基本分数标准，但还未收到正式 offer",
        "project_constraint": "不加码、不重构流程，保持自动化产出即可",
    },
    {
        "name": "晚餐推荐",
        "status": "active",
        "value_score": 4,
        "risk_level": "medium",
        "risk_note": "容易从真实需求变成做 APP 或搭系统",
        "ai_delegation_level": 4,
        "human_intervention_level": 2,
        "control_action": "delegate_to_ai",
        "control_action_note": "先让 AI 用消息推送验证 7 天，不做 APP",
        "latest_update": "需求明确：减少下班后饮食决策成本",
        "project_constraint": "不做 APP，先用简单消息推送验证是否真的改善饮食选择",
    },
    {
        "name": "周末去哪玩",
        "status": "active",
        "value_score": 4,
        "risk_level": "medium",
        "risk_note": "容易临时搜索太晚，或做成复杂攻略系统",
        "ai_delegation_level": 4,
        "human_intervention_level": 2,
        "control_action": "delegate_to_ai",
        "control_action_note": "每周四让 AI 提前给 3 个候选方向",
        "latest_update": "需求明确：减少周末临时决策成本",
        "project_constraint": "不做 APP，不做复杂攻略库，先用每周候选方案验证",
    },
    {
        "name": "工作掌控力",
        "status": "active",
        "value_score": 5,
        "risk_level": "medium",
        "risk_note": "如果长期只分配工作不介入关键技术，可能降低技术判断力和团队价值",
        "ai_delegation_level": 1,
        "human_intervention_level": 5,
        "control_action": "human_intervene",
        "control_action_note": "每周至少亲自介入一个关键技术点或评审一个关键模块",
        "latest_update": "成为组长后有更多空闲，但也担心掌控力下降",
        "project_constraint": "不抢回所有代码，但必须保持技术判断力和关键模块理解",
    },
    {
        "name": "投资学习",
        "status": "observe",
        "value_score": 3,
        "risk_level": "medium",
        "risk_note": "容易沉淀大量笔记但不转化为投资判断框架",
        "ai_delegation_level": 3,
        "human_intervention_level": 3,
        "control_action": "observe",
        "control_action_note": "先观察课程笔记是否能转化为结构化投资框架",
        "latest_update": "已有 Notion 笔记，但价值感不强",
        "project_constraint": "先沉淀投资框架，不急着做复杂私人投资 agent，不直接用于交易决策",
    },
    {
        "name": "AI客服",
        "status": "paused",
        "value_score": 2,
        "risk_level": "high",
        "risk_note": "技术流程跑通，但商业推进停滞，且依赖外部客户配合",
        "ai_delegation_level": 2,
        "human_intervention_level": 2,
        "control_action": "pause",
        "control_action_note": "除非朋友或客户明确推动，否则暂时不主动投入",
        "latest_update": "已有 demo，但项目停滞",
        "project_constraint": "不主动投入大量时间，除非出现明确客户反馈或付费意向",
    },
    {
        "name": "股票分析",
        "status": "paused",
        "value_score": 2,
        "risk_level": "high",
        "risk_note": "容易产生看似有用但无法验证投资价值的报告",
        "ai_delegation_level": 3,
        "human_intervention_level": 2,
        "control_action": "pause",
        "control_action_note": "暂时暂停，除非能定义清楚评价标准",
        "latest_update": "曾经本地部署 daily_stock_analysis，但因设备断电停工",
        "project_constraint": "不要投入太多，避免伪价值；不得直接给出交易指令",
    },
]


def seed(force: bool = False) -> None:
    init_db()
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if count > 0 and not force:
            print(f"数据库已有 {count} 个项目，跳过 seed。使用 --force 覆盖。")
            return
        if force:
            conn.execute("DELETE FROM project_events")
            conn.execute("DELETE FROM projects")
            conn.commit()
        now = now_beijing()
        for p in SEED_PROJECTS:
            cur = conn.execute(
                """
                INSERT INTO projects (
                    name, status, value_score, risk_level, risk_note,
                    ai_delegation_level, human_intervention_level,
                    control_action, control_action_note, latest_update,
                    project_constraint, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p["name"],
                    p["status"],
                    p["value_score"],
                    p["risk_level"],
                    p["risk_note"],
                    p["ai_delegation_level"],
                    p["human_intervention_level"],
                    p["control_action"],
                    p["control_action_note"],
                    p["latest_update"],
                    p["project_constraint"],
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO project_events (
                    project_id, project_name, event_type, summary, decision,
                    next_action, happened_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cur.lastrowid,
                    p["name"],
                    "note",
                    p["latest_update"],
                    p["risk_note"],
                    p["control_action_note"],
                    now,
                    now,
                ),
            )
        conn.commit()
        print(f"已初始化 {len(SEED_PROJECTS)} 个项目。")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="清空并重新插入种子数据")
    args = parser.parse_args()
    seed(force=args.force)


if __name__ == "__main__":
    main()
    sys.exit(0)
