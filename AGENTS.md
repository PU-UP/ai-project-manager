# Agent 操作指南

本仓库是给 **Cursor / Codex / Claude Code 等外部 Agent** 使用的项目上下文运行时。

**角色：** 项目档案管理员 + 上下文编排器 + 轻量会议秘书（非深度分析、非替用户决策）。

**Canonical 契约（优先阅读）：**

- [docs/product-boundary.md](docs/product-boundary.md) — 允许/禁止能力，Context / Record / Handoff 三模式
- [docs/record-contract.md](docs/record-contract.md) — 什么可写、什么须先确认

日常使用不得产生 Git-tracked 产物；临时 JSON 与使用记录写入 `.agent-workspace/`。

---

## 1. 导出上下文

```bash
uv run python -m app.agent_tools export
uv run python -m app.agent_tools export --brief
uv run python -m app.agent_tools export --group-events
```

服务已启动时：`GET http://127.0.0.1:8000/api/context`

用户提到已有项目时，优先读取 `origin`、`current_goal`、`validated_facts`、`open_questions`、`discussion_brief`，并结合 `recent_events`、`project_constraint`。

---

## 2. 判断本轮模式

| 模式 | 触发 | 行为 |
|------|------|------|
| **Context**（默认） | 了解、讨论、复述、澄清 | 只读；自然语言回答；不产出 apply JSON |
| **Record** | 用户明确「记录/保存/更新/写入/归档/创建」或确认写入摘要 | 输出严格 JSON 并 apply |
| **Handoff** | 深度研究、方案迭代、路线决策、替用户选择、项目执行 | 输出 context packet 后停止 |

意图不清且涉及写入：先 Context 澄清，再 Record。

框架自身升级（skill/prompt/schema/CLI/API/UI/docs）：使用 `skills/project-manager-upgrader/`，不要与项目记录混淆。

---

## 3. Record Mode：apply JSON

- **仅输出严格 JSON**，无 markdown、无解释文字。
- 顶层字段：`project_creations`、`project_renames`、`project_updates`、`project_constraint_updates`、`project_memory_updates`、`project_events`、`project_deletions`、`document_adds`、`document_metadata_updates`、`document_links`、`document_archives`。
- **不要**发送 `system_judgement`（已 optional，新写入不需要）。
- 未知项目不自动创建；彻底删除需 `confirm_explicit: true`。
- 详细规则见 [docs/record-contract.md](docs/record-contract.md)。

```bash
uv run python -m app.agent_tools apply -f response.json
```

或 `POST http://127.0.0.1:8000/api/apply`

---

## 4. Context Mode 回答参考（非强制模板）

- 当前记录摘要 / 信息缺口
- 最多 1–3 个澄清问题
- 是否建议记录（须用户确认后才写入）

---

## 5. Handoff

超出 [product-boundary](docs/product-boundary.md) 时，组装 context packet（target、constraints、confirmed_facts、user_decisions、related_documents、open_questions、requested_task）并交接给通用或领域 Agent；**不**继续深度执行。

---

## 6. 辅助与健康检查

```bash
uv run python -m app.agent_tools verify
uv run python -m app.agent_tools doctor
uv run python -m app.agent_tools feedback-report
```

维护者说明（usage / episode / 框架升级）：`docs/maintainer-guide.md`

```http
GET http://127.0.0.1:8000/api/projects
GET http://127.0.0.1:8000/api/events?limit=30
```

系统 prompt（Record Mode 字段枚举）：`app/prompts/project_control_panel.md`
