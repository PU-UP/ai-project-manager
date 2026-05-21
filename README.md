# AI项目管家（ai-project-manager）

**AI项目管家** 是一个给外部 Agent 使用的个人项目经理框架。

一句话：用户用自然语言和 Agent 交流，Agent 通过本工程读取、写入、维护项目记录，并在网页上展示近期项目局面、系统判断和下一步控制动作。

## 目标

帮助外部 Agent 长期维护你的项目记忆：

- 读取当前所有项目状态
- 记录近期进展、反馈、风险、想法、决策和阻塞
- 更新项目价值、风险、AI 接管程度、人工介入程度和控制动作
- 重命名项目，更新项目约束
- 在你不知道做什么时，基于记录给出方向判断
- 将项目局面可视化给用户查看

默认工作流：

1. 用户对 Agent 自然语言描述项目进展或困惑。
2. Agent 导出项目上下文。
3. Agent 阅读系统 prompt。
4. Agent 产出严格 JSON。
5. Agent 通过 CLI 或 API 写入本工程。
6. 用户刷新网页查看系统判断、近期记录和项目进度。

网页用于查看项目局面；项目维护由 Agent 完成。

## 当前能力

- 本地单用户，无登录
- 版本号从 `pyproject.toml` 读取，并在导出上下文中返回
- 项目总览与项目详情页
- 系统级判断展示
- 近期项目事件流
- Agent 通过 CLI / API 导出上下文
- Agent 通过 JSON 创建、重命名、更新、记录、调整约束、归档或删除项目
- SQLite 存储
- `logs/interactions.jsonl` 记录 Agent 交互
- 可选内置 LLM 代码保留，但默认不作为核心入口

## Skills

仓库内置一个给外部 Agent 使用的技能：

```text
skills/project-manager-runtime/
```

它约定了 Agent 如何读取上下文、判断是否写入、应用 JSON 更新、记录低频使用反馈，并保证日常使用不会产生 Git 记录。使用记录写入 `.agent-workspace/usage/usage.jsonl`，该目录被 Git 忽略。

## Agent 协议

Agent 的输出 JSON 顶层支持：

- `project_creations`：用户明确确认后创建新项目
- `project_renames`：重命名已有项目
- `project_updates`：更新项目当前状态和控制判断
- `project_constraint_updates`：更新已有项目的范围约束
- `project_events`：追加项目事件，形成近期进展记录
- `project_deletions`：归档或删除项目，默认归档
- `system_judgement`：本轮系统级判断

详细规则见 [AGENTS.md](AGENTS.md) 与 `app/prompts/project_control_panel.md`。

## 安装

需要 [uv](https://docs.astral.sh/uv/) 与 Python 3.11+。

```bash
cd ai-project-manager
uv sync
```

也可使用 pip：

```bash
pip install -r requirements.txt
```

## 初始化数据库

```bash
uv run python -m app.seed
```

已有数据时跳过；强制重建：

```bash
uv run python -m app.seed --force
```

## 本地运行

```bash
uv run uvicorn app.main:app --reload
```

浏览器打开：http://127.0.0.1:8000

## 导出上下文

```bash
uv run python -m app.agent_tools export
```

或：

```http
GET http://127.0.0.1:8000/api/context
```

## 提交 Agent 更新

```bash
uv run python -m app.agent_tools apply -f response.json
```

或：

```http
POST http://127.0.0.1:8000/api/apply
Content-Type: application/json
```

示例：

```json
{
  "project_events": [
    {
      "project_name": "Hermes每日任务",
      "event_type": "feedback",
      "summary": "用户感觉日报仍然泛泛，没有转化为行动",
      "decision": "存在假性推进风险",
      "next_action": "调整日报评价标准"
    }
  ],
  "project_updates": [
    {
      "project_name": "Hermes每日任务",
      "control_action": "change_metric",
      "control_action_note": "要求每次输出至少一个可行动建议",
      "latest_update": "用户反馈 Hermes 仍缺少行动闭环"
    }
  ],
  "system_judgement": {
    "summary": "当前最重要的不是增加项目，而是让 Hermes 从信息输出转向行动建议。",
    "real_progress": [],
    "pseudo_progress_risk": ["Hermes每日任务可能只是持续输出信息，但没有改变行动"],
    "delegate_to_ai": [],
    "need_human_intervention": ["Hermes每日任务需要用户重新定义价值标准"],
    "pause_or_ignore": [],
    "top_control_recommendation": {
      "control_action": "change_metric",
      "project_name": "Hermes每日任务",
      "note": "先修正日报价值标准，否则继续运行只会增加噪声"
    }
  }
}
```

## API

```http
GET  /api/context
GET  /api/projects
GET  /api/events?limit=30
POST /api/apply
```

## 数据模型

### `projects`

| 字段 | 说明 |
|------|------|
| id, name | 主键、项目名（唯一） |
| status | active / maintain / observe / paused / archived |
| value_score | 1-5 主观价值 |
| risk_level | low / medium / high |
| risk_note | 风险说明 |
| ai_delegation_level | 0-5 |
| human_intervention_level | 0-5 |
| control_action | 控制动作枚举 |
| control_action_note | 动作说明，控制在 80 个汉字以内 |
| latest_update | 最近进展 |
| project_constraint | 项目约束 |
| created_at, updated_at | 时间戳 |

状态含义：`active` 当前推进，`maintain` 维持运行，`observe` 观察孵化，`paused` 短期暂停，`archived` 历史归档。控制动作使用系统 prompt 中的固定枚举，不由 Agent 自定义。

### `project_events`

| 字段 | 说明 |
|------|------|
| project_id, project_name | 所属项目 |
| event_type | progress / decision / risk / feedback / idea / blocker / note |
| summary | 事件摘要 |
| evidence | 判断依据 |
| decision | 形成的判断 |
| next_action | 下一步动作 |
| happened_at, created_at | 时间戳 |

### `logs`

记录 Agent 原始输入、原始输出、解析摘要和系统判断。

## 验收清单

1. `uv sync`
2. `uv run python -m app.seed`
3. `uv run uvicorn app.main:app --reload`
4. 打开 http://127.0.0.1:8000 看到项目总览
5. `uv run python -m app.agent_tools export` 可导出项目和近期事件
6. `uv run python -m app.agent_tools apply -f response.json` 可写入项目事件和判断
7. 刷新页面可见系统判断、近期项目记录和项目详情事件流
