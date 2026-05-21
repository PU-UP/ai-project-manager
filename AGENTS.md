# Agent 操作指南

本仓库是给 **Cursor / Codex / Claude Code 等外部 Agent** 使用的个人项目经理框架。

用户自然语言描述项目进展、思考、困惑或决策；Agent 负责读取上下文、判断影响、写入项目状态和事件记录。

处理项目进展、方向判断、记录或归档请求时，优先使用仓库内技能：

```text
skills/project-manager-runtime/
```

日常使用该技能不得产生 Git-tracked 产物。临时 JSON、使用记录和低频反馈写入 `.agent-workspace/`，该目录被忽略。

## 1. 导出当前项目上下文

```bash
uv run python -m app.agent_tools export
```

或（服务已启动）：

```http
GET http://127.0.0.1:8000/api/context
```

上下文包含当前项目状态、近期项目事件、最新系统级判断和可用操作协议。

## 2. 阅读系统 Prompt

文件：`app/prompts/project_control_panel.md`

它定义项目经理判断规则、输出 JSON 结构、项目创建、更新、记录和归档策略。

## 3. 根据用户自然语言产出 JSON

- **仅输出严格 JSON**，无 markdown、无解释文字。
- 顶层结构支持：
  - `project_creations`
  - `project_renames`
  - `project_updates`
  - `project_constraint_updates`
  - `project_events`
  - `project_deletions`
  - `system_judgement`
- 未知项目不要自动创建；只有用户明确确认时才写入 `project_creations`。
- 普通进展、反馈、想法、风险和决策优先写入 `project_events`。
- 只有项目当前判断发生变化时才写入 `project_updates`。
- 项目改名写入 `project_renames`；项目约束变化写入 `project_constraint_updates`。
- 默认归档，不默认彻底删除。
- 遵守各项目 `constraint`。
- `status` 使用固定五类：`active` 当前推进、`maintain` 维持运行、`observe` 观察孵化、`paused` 短期暂停、`archived` 历史归档。
- `control_action` 必须使用系统 prompt 中的固定枚举，不要自定义动作词；`control_action_note` 控制在 80 个汉字以内。

## 4. 提交更新

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

## 5. 辅助读取接口

```http
GET http://127.0.0.1:8000/api/projects
GET http://127.0.0.1:8000/api/events?limit=30
```

## 6. 刷新页面

首页会展示更新后的系统判断、近期项目记录和项目进度表。详情页会展示单个项目的控制动作、风险、约束和事件记录。
