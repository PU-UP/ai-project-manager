# AI项目管家（ai-project-manager）

**AI项目管家** 是一个给外部 Agent 使用的项目上下文运行时。

一句话：用户用自然语言提到已有项目时，Agent 先通过本工程恢复项目上下文，接上讨论或工作；只有形成值得长期保存的结论、或用户明确要求记录时，才写入项目记录。网页用于展示近期项目局面、系统判断和下一步控制动作。

## 目标

帮助外部 Agent 不需要你每次重讲项目背景，就能继续参与项目讨论和工作：

- 读取当前所有项目状态、项目记忆和近期事件
- 通过 `discussion_brief`、`risk_note`、`project_constraint` 和最新系统判断恢复上下文
- 围绕已有项目参与讨论、复盘、分析和方向判断
- 在你不知道做什么时，基于上下文给出建议
- 仅在必要时记录近期进展、反馈、风险、想法、决策和阻塞
- 更新项目价值、风险、AI 接管程度、人工介入程度和控制动作
- 重命名项目，更新项目约束
- 将项目局面可视化给用户查看

默认工作流：

1. 用户用自然语言提到已有项目、项目困惑、进展或判断。
2. Agent 导出并读取项目上下文，优先关注 project memory、`discussion_brief`、`recent_events`、`risk_note`、`project_constraint` 和 `latest_system_judgement`。
3. Agent 阅读系统 prompt，并判断本轮属于讨论、工作还是记录。
4. Context / Discussion Mode：用户想聊项目、继续讨论、复盘、思考、问建议时，默认只读上下文并自然语言回答。
5. Work Mode：用户希望 Agent 在某个项目语境下分析、整理、复盘、提出建议时，仍默认只读，除非用户要求保存结果。
6. Record Mode：只有用户明确说“记录/保存/更新/写入/归档/创建”，或确认 Agent 建议写入时，才产出严格 JSON。
7. 进入 Record Mode 后，Agent 通过 CLI 或 API apply；用户刷新网页查看更新后的系统判断、近期记录和项目进度。

网页用于查看项目局面；项目上下文恢复、讨论参与和必要记录由 Agent 完成。记录不是默认主流程，它只是讨论形成稳定结论后的保存动作。

## 当前能力

- 本地单用户，无登录
- 版本号从 `pyproject.toml` 读取，并在导出上下文中返回
- 项目总览与项目详情页
- 系统级判断展示
- 近期项目事件流
- Agent 通过 CLI / API 导出上下文
- Agent 通过 JSON 创建、重命名、更新、记录、调整约束、维护长期记忆、归档或删除项目
- SQLite 存储
- `logs/interactions.jsonl` 记录 Agent 交互
- 可选内置 LLM 代码保留，但默认不作为核心入口

## Skills

仓库内置一个给外部 Agent 使用的技能：

```text
skills/project-manager-runtime/
```

它约定了 Agent 如何先恢复项目上下文、区分讨论/工作/记录模式、判断是否写入、应用 JSON 更新、记录低频使用反馈，并保证日常使用不会产生 Git 记录。使用记录写入 `.agent-workspace/usage/usage.jsonl`，该目录被 Git 忽略。

另有一个框架升级技能：

```text
skills/project-manager-upgrader/
```

当用户讨论系统反馈、升级框架、优化 skill / prompt / schema / CLI / API / UI / logging / docs 时使用。若 Agent 不确定用户是在记录项目进展还是优化框架，应先询问。

## Agent 协议

只有进入 Record Mode 时，Agent 才生成 apply JSON。JSON 顶层支持：

- `project_creations`：用户明确确认后创建新项目
- `project_renames`：重命名已有项目
- `project_updates`：更新项目当前状态和控制判断
- `project_constraint_updates`：更新已有项目的范围约束
- `project_memory_updates`：维护项目长期记忆和讨论摘要
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

## 常用诊断

导出简版上下文或按项目聚合近期事件：

```bash
uv run python -m app.agent_tools export --brief
uv run python -m app.agent_tools export --group-events
```

复盘框架 feedback 并生成升级建议：

```bash
uv run python -m app.agent_tools feedback-report
```

检查运行时、技能版本和本地记录状态：

```bash
uv run python -m app.agent_tools doctor
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

推荐使用便捷启动脚本：

```powershell
.\start_dashboard.cmd
```

脚本会默认启动 http://127.0.0.1:8000 并打开浏览器。如果 8000 已经是本项目服务，会直接打开现有页面；如果被其他服务占用，会自动尝试 8001-8010。

也可以指定端口：

```powershell
.\scripts\start_dashboard.ps1 -Port 8010
```

手动启动方式：

```bash
uv run python -m uvicorn app.main:app --reload
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
