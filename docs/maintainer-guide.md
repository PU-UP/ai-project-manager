# 维护者指南

> 面向框架升级与 harness 维护；日常项目操作见 `skills/project-manager-runtime/SKILL.md` 与 `AGENTS.md`。

## Usage 记录

路径：`.agent-workspace/usage/usage.jsonl`（不纳入 Git）

```bash
uv run python skills/project-manager-runtime/scripts/record_usage.py \
  --action apply --write-mode database --summary "简短摘要"
```

`feedback-report` 只汇总使用与反馈事实，不自动生成产品升级建议：

```bash
uv run python -m app.agent_tools feedback-report
```

## Apply Episode 审计

每次 `apply` 在 `.agent-workspace/episodes/YYYY-MM-DD.jsonl` 追加一行最小审计：

- `ok`、`error`、`source`、`changed_projects`
- 不含完整 raw JSON；仅供维护者事后抽查 apply 健康度

无独立消费端；不要依赖 episode 做业务逻辑。

## 框架升级

用户讨论 skill、prompt、schema、CLI、API、UI、测试或 docs 时，使用 `skills/project-manager-upgrader/`，不要写入项目业务库。

## 健康检查与验证

```bash
uv run python -m app.agent_tools doctor
uv run python -m app.agent_tools verify
```

`verify` 串联：Python compile、pytest、JS 语法、doctor、版本同步、契约引用检查、导出 smoke。

## 版本同步

发布时同步：

- `pyproject.toml` → `project.version`
- `skills/project-manager-runtime/SKILL.md` → `Skill version:`

`doctor` / `verify` 会检查 runtime 与 skill 版本一致。
