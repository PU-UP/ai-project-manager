---
name: project-manager-upgrader
description: Use this repository as a self-improving project-manager framework. Use when the user asks to upgrade, optimize, repair, improve, review feedback for, evolve, or discuss friction in the project-manager system itself rather than record ordinary project progress. Also use when the user asks whether past feedback suggests framework changes, when the request mentions system upgrade, skill upgrade, prompt/schema/CLI/API/UI/logging/docs improvements, or when intent is ambiguous between updating a project and improving the framework.
---

# Project Manager Upgrader

Use this skill to decide and execute small framework upgrades for this repository.

## Intent Split

First classify the user request:

- **Project update**: The user describes progress, decisions, risks, feedback, or state changes for a normal tracked project. Use `skills/project-manager-runtime/`.
- **Framework upgrade**: The user discusses the project-manager system itself: feedback, friction, export/apply workflow, prompt rules, skill behavior, schema, CLI/API, dashboard UI, logs, versioning, or Agent routing. Use this skill.
- **Ambiguous**: Ask one short question before writing: "Do you want to record a project update, or improve the project-manager framework itself?"

Do not treat framework-upgrade discussion as a database write unless the user explicitly asks to record that as an `ai-project-manager` project event.

## Upgrade Workflow

1. Inspect feedback and health:

```bash
uv run python -m app.agent_tools feedback-report
uv run python -m app.agent_tools doctor
```

If `uv` is broken, use the local environment only as needed, but do not create Git-tracked scratch files.

2. Read the relevant context:

- `skills/project-manager-runtime/SKILL.md` for daily project operation rules.
- `AGENTS.md` for cross-agent entry instructions.
- `app/prompts/project_control_panel.md` if prompt behavior changes.
- `app/agent_tools.py` for CLI/export/apply/report changes.

3. Choose the smallest upgrade target:

- `prompt`: intent classification or output rules.
- `skill`: Agent workflow and trigger guidance.
- `schema`: durable data fields or validation.
- `cli` / `api`: deterministic support commands.
- `ui`: dashboard usability.
- `logging`: usage feedback or mini episode records.
- `docs`: AGENTS/README alignment.

4. Implement only the agreed or clearly implied upgrade. Avoid expanding the dashboard or data model unless feedback points there.

5. Validate:

```bash
node --check app/static/app.js
uv run python -m compileall app
uv run python -m app.agent_tools feedback-report
uv run python -m app.agent_tools doctor
git status --short
```

Run only checks relevant to changed files if a tool is unavailable.

6. Record meaningful framework upgrades:

```bash
uv run python skills/project-manager-runtime/scripts/record_usage.py --action upgrade --write-mode framework --summary "Short upgrade summary"
```

Add `--feedback`, `--friction-type`, `--severity`, and `--upgrade-target` when the upgrade addresses a known feedback item.

## Guardrails

- Keep `.agent-workspace/` as the only place for temporary outputs.
- Do not write project database updates for framework maintenance unless requested.
- If the user asks to review feedback or asks whether anything is worth upgrading, answer with a recommendation first; implement only when they ask to proceed.
- When changing framework behavior, update the version consistently: `pyproject.toml`, `uv.lock`, `skills/project-manager-runtime/SKILL.md`, and `record_usage.py`.
