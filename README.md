# AI项目管家（ai-project-manager）

给外部 Agent 使用的**项目上下文运行时**：帮 Agent 恢复项目档案、复述记录、在用户确认后写入，并在越界时交接任务。

一句话：用户用自然语言提到项目 → Agent 先导出上下文 → 默认只读讨论 → 显式确认后才记录。

完整 Agent 协议见 [AGENTS.md](AGENTS.md)；产品边界见 [docs/product-boundary.md](docs/product-boundary.md)。

## 能做什么

- 维护项目档案、用户确认的事实与决定、开放问题、约束
- 导出上下文包（含 `--brief` / `--group-events`）
- 登记项目事件与长期记忆（Record Mode）
- 网页查看项目列表、详情与事件流

**不做：** 替项目做深度分析、方案迭代、优先级或路线决策（见 product-boundary 的 Handoff）。

## 三种模式（简述）

| 模式 | 说明 |
|------|------|
| Context | 默认；恢复、复述、指出缺口 |
| Record | 用户明确要求或确认写入后 apply |
| Handoff | 超出边界；输出 context packet 后停止 |

## Skills

- `skills/project-manager-runtime/` — 日常项目操作
- `skills/project-manager-upgrader/` — 框架自身升级

## 安装与运行

需要 [uv](https://docs.astral.sh/uv/) 与 Python 3.11+。

```bash
uv sync
uv run python -m app.seed
```

启动面板：

```powershell
.\start_dashboard.cmd
```

浏览器：http://127.0.0.1:8000

## 常用命令

```bash
uv run python -m app.agent_tools export --brief
uv run python -m app.agent_tools apply -f response.json
uv run python -m app.agent_tools doctor
uv run pytest -q
```

## apply 示例（单事件，无 system_judgement）

```json
{
  "project_events": [
    {
      "project_name": "示例项目",
      "event_type": "decision",
      "summary": "用户确认暂停推进",
      "decision": "维持 paused"
    }
  ]
}
```

## API

```http
GET  /api/context
GET  /api/projects
GET  /api/events?limit=30
POST /api/apply
```

## 数据

SQLite：`data/project_control_panel.db`。表：`projects`、`project_events`、`logs`。

字段说明与枚举见 `app/prompts/project_control_panel.md`；legacy 决策型字段（value_score、control_action 等）仍在库中，新写入协议逐步废弃，见 roadmap。
