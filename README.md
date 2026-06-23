# AI项目管家（ai-project-manager）

给外部 Agent 使用的**项目上下文运行时**：帮 Agent 恢复项目档案、复述记录、在用户确认后写入，并在越界时交接任务。

一句话：用户用自然语言提到项目 → Agent 先导出上下文 → 默认只读讨论 → 显式确认后才记录。

完整 Agent 协议见 [AGENTS.md](AGENTS.md)；产品边界见 [docs/product-boundary.md](docs/product-boundary.md)。

## 快速开始

```bash
uv sync
uv run python -m app.seed          # 可选：示例数据
uv run python -m app.agent_tools export --brief
uv run python -m app.agent_tools verify
```

启动面板：`.\start_dashboard.cmd` → http://127.0.0.1:8000

## 能做什么

- 维护项目档案、用户确认的事实与决定、开放问题、已知风险、约束
- 登记与关联文档（`document_adds` 等）
- 导出上下文包（含 `--brief` / `--group-events`）
- 网页查看项目列表、详情与事件流

**不做：** 替项目做深度分析、方案迭代、优先级或路线决策 → 使用 Handoff。

## 三种模式

| 模式 | 说明 |
|------|------|
| Context | 默认；恢复、复述、指出缺口 |
| Record | 用户明确要求或确认写入后 apply |
| Handoff | 超出边界；输出 context packet 后停止 |

## Handoff 示例

当用户要求「深入研究并决定路线」时，输出如下结构后**停止执行**（不 apply）：

```json
{
  "target": "为 X 项目选定下一阶段技术路线",
  "constraints": ["预算上限 5 万", "须兼容现有 Hermes 数据"],
  "confirmed_facts": ["用户已确认暂停大规模重构"],
  "user_decisions": ["维持 paused 状态至 Q3"],
  "related_documents": [
    {"title": "2026-06-20 会议纪要", "status": "current", "source_uri": "..."}
  ],
  "open_questions": ["是否在 Q3 重启移动端？"],
  "requested_task": "对比方案 A/B 并给出实施步骤（由领域 Agent 完成）"
}
```

## 常用命令

```bash
uv run python -m app.agent_tools export --brief
uv run python -m app.agent_tools apply -f response.json
uv run python -m app.agent_tools doctor
uv run python -m app.agent_tools verify
uv run pytest -q
```

框架维护（usage/episode/升级）见 [docs/maintainer-guide.md](docs/maintainer-guide.md)。

## Record 示例（单事件）

```json
{
  "project_events": [
    {
      "project_name": "示例项目",
      "event_type": "note",
      "summary": "用户确认的讨论记录"
    }
  ]
}
```

含 `decision` 时须附带 `decision_provenance`；`validated_facts` 须附带 `_provenance`。见 `docs/record-contract.md`。

## Skills

- `skills/project-manager-runtime/` — 日常项目操作
- `skills/project-manager-upgrader/` — 框架自身升级

## API

```http
GET  /api/context
GET  /api/snapshot
GET  /api/projects
GET  /api/events?limit=30
POST /api/apply
```

## 数据

SQLite：`data/project_control_panel.db`。主要表：`projects`、`project_events`、`project_documents`、`logs`。

Legacy 决策型列（`value_score`、`control_action` 等）仍在库中供历史只读；新写入协议已废弃，导出时归入 `legacy_decision_fields`。
