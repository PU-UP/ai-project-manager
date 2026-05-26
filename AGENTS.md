# Agent 操作指南

本仓库是给 **Cursor / Codex / Claude Code 等外部 Agent** 使用的项目上下文运行时。

用户自然语言描述项目进展、思考、困惑或决策；Agent 先恢复项目上下文，参与项目讨论或工作，只有必要时才写入项目状态和事件记录。

核心原则：Project Context First。用户提到已有项目时，Agent 应优先导出并读取项目上下文，包括 project memory、`discussion_brief`、`recent_events`、`risk_note`、`project_constraint`、`latest_system_judgement`。默认先用自然语言接上项目上下文并参与讨论，不要默认生成 apply JSON。

处理项目进展、方向判断、记录或归档请求时，优先使用仓库内技能：

```text
skills/project-manager-runtime/
```

处理本框架自身的反馈复盘、系统升级、技能/Prompt/Schema/CLI/API/UI/日志/文档优化请求时，使用：

```text
skills/project-manager-upgrader/
```

如果用户的表达可能同时指向“记录某个项目进展”和“优化项目经理框架”，不要猜测写入；先问一句确认。

日常使用该技能不得产生 Git-tracked 产物。临时 JSON、使用记录和低频反馈写入 `.agent-workspace/`，该目录被忽略。

## 1. 导出当前项目上下文

```bash
uv run python -m app.agent_tools export
```

当 Agent 只是要讨论、复盘或判断方向，优先使用简版或分组上下文，避免被完整事件流淹没：

```bash
uv run python -m app.agent_tools export --brief
uv run python -m app.agent_tools export --group-events
```

或（服务已启动）：

```http
GET http://127.0.0.1:8000/api/context
```

上下文包含当前项目状态、project memory、近期项目事件、最新系统级判断和可用操作协议。用户提到已有项目时，优先读取该项目的 `origin`、`current_goal`、`key_judgements`、`validated_facts`、`open_questions`、`discussion_brief`，并结合 `recent_events`、`risk_note`、`project_constraint`、`latest_system_judgement`。

## 2. 阅读系统 Prompt

文件：`app/prompts/project_control_panel.md`

它定义项目经理判断规则、输出 JSON 结构、项目创建、更新、记录和归档策略。

## 3. 判断本轮模式

先判断用户意图：

- 用户描述某个项目的进展、风险、反馈、决策、状态变化：按项目运行时处理。
- 用户要求“优化/升级/修复/复盘反馈/改进系统/改 skill/prompt/schema/CLI/API/UI/logging/docs”：按框架升级处理，使用 `skills/project-manager-upgrader/`。
- 用户意图不清：先询问，不要直接 apply，也不要直接改 tracked 文件。

项目运行时分三种模式：

- Context / Discussion Mode：用户想聊项目、继续讨论、复盘、思考、问建议时，默认只读上下文并自然语言回答。
- Work Mode：用户希望 Agent 在某个项目语境下帮忙分析、复盘、整理、提出建议时，仍然默认只读，除非用户要求保存结果。
- Record Mode：只有用户明确说“记录/保存/更新/写入/归档/创建”，或用户确认 Agent 建议写入时，才生成严格 JSON 并 apply。

记录不是默认主流程。本框架的核心价值是让 Agent 不需要用户每次重讲项目背景，就能继续讨论、判断和给建议；记录只是当讨论形成值得长期保存的结论时才发生。

如果用户只是想围绕某个项目讨论、梳理、追问或恢复上下文，默认进入 Context / Discussion Mode：

- 先读取项目 memory 字段，尤其是 `origin`、`current_goal`、`key_judgements`、`validated_facts`、`open_questions`、`discussion_brief`，并结合 `recent_events`、`risk_note`、`project_constraint`。
- 用自然语言回答，不要为了讨论本身强行产出 apply JSON。
- 默认不写入数据库，除非用户明确要求记录、保存、更新，或确认你提出的写入摘要。
- 如果多轮对话持续围绕同一项目，沿用同一项目上下文，直到用户切换项目。
- 如果项目记忆缺失或新项目信息不足，向用户提出 1-3 个聚焦问题，不要把它变成复杂表单。
- 不要虚构项目背景；尚未确认的内容只能作为问题保留，不能写成已验证事实。

Skill 的触发是按轮次发生的，不是持久后台会话；但对话上下文可以承载连续项目讨论。只要用户仍在讨论同一项目，Agent 应把它当作同一条讨论线索处理。

讨论或工作模式下可以参考这种自然语言结构，但不要强制每次套模板：

- 我先按当前项目记忆接上：
- 我对这次输入的判断：
- 接下来值得讨论/推进的问题：
- 是否建议记录：

## 4. Record Mode：写入时根据用户自然语言产出 JSON

- **仅输出严格 JSON**，无 markdown、无解释文字。
- 顶层结构支持：
  - `project_creations`
  - `project_renames`
  - `project_updates`
  - `project_constraint_updates`
  - `project_memory_updates`
  - `project_events`
  - `project_deletions`
  - `system_judgement`
- 未知项目不要自动创建；只有用户明确确认时才写入 `project_creations`。
- 普通进展、反馈、想法、风险和决策优先写入 `project_events`。
- 只有项目当前判断发生变化时才写入 `project_updates`。
- 项目改名写入 `project_renames`；项目约束变化写入 `project_constraint_updates`。
- 项目长期记忆变化写入 `project_memory_updates`，不要用它替代普通事件记录。
- 默认归档，不默认彻底删除。
- 遵守各项目 `constraint`。
- `status` 使用固定五类：`active` 当前推进、`maintain` 维持运行、`observe` 观察孵化、`paused` 短期暂停、`archived` 历史归档。
- `control_action` 必须使用系统 prompt 中的固定枚举，不要自定义动作词；`control_action_note` 控制在 80 个汉字以内。

## Project Memory

项目长期记忆由以下字段组成：

- `origin`
- `current_goal`
- `progress_percent`
- `progress_note`
- `key_judgements`
- `validated_facts`
- `open_questions`
- `discussion_brief`

适合使用 `project_memory_updates` 的情况：

- 项目刚创建后需要形成初始记忆。
- 项目合并、重命名或阶段变化后。
- 用户明确要求总结项目。
- 形成了关键判断。
- 事件流累积后需要压缩为长期记忆。
- 为后续项目讨论补充背景。

不要使用 `project_memory_updates` 的情况：

- 普通日常进展。
- 一次性想法。
- 尚未确认的事实。
- 每次 apply 都机械更新。

Discussion Mode 前置规则：

- 项目讨论模式默认先读取项目 memory 字段，尤其是 `origin`、`current_goal`、`key_judgements`、`validated_facts`、`open_questions`、`discussion_brief`、`recent_events`、`risk_note`、`project_constraint`、`latest_system_judgement`。
- 讨论模式默认不写入数据库，除非用户明确要求记录或确认写入。
- 讨论中形成值得长期保存的内容时，先总结建议写入项；用户确认后再写入。
- 用户确认写入后，普通讨论结论优先写入 `project_events`；当前判断变化写入 `project_updates`；长期项目理解变化写入 `project_memory_updates`。
- 本仓库目前只提供上下文结构，不实现独立聊天 UI 或 discussion skill。

## 5. 提交更新

```bash
uv run python -m app.agent_tools apply -f response.json
```

或：

```http
POST http://127.0.0.1:8000/api/apply
Content-Type: application/json

{
  "user_input": "用户原话…",
  "project_updates": [],
  "project_events": [],
  "system_judgement": {}
}
```

## 6. 辅助读取接口

```http
GET http://127.0.0.1:8000/api/projects
GET http://127.0.0.1:8000/api/events?limit=30
```

## 7. 刷新页面

首页会展示更新后的系统判断、近期项目记录和项目进度表。详情页会展示单个项目的控制动作、风险、约束和事件记录。

## 8. 框架反馈与健康检查

复盘历史 feedback：

```bash
uv run python -m app.agent_tools feedback-report
```

检查版本、技能、usage 和 episode 状态：

```bash
uv run python -m app.agent_tools doctor
```
