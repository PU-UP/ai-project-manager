---
name: project-manager-runtime
description: Use this repository as an external-Agent project context runtime. Use when the user mentions an existing project, wants to recover context, discuss or work through a project, asks what to work on, wants to record or update project state, wants to create/archive a project, or asks for project direction based on the local project context.
---

# Project Manager Runtime

Skill version: `0.8.0`

Use this skill to operate the repository as a project context runtime for an external Agent. The user talks naturally; the Agent first restores project context, joins the discussion or work, decides whether anything needs to be recorded, and keeps the workspace clean.

Project Context First: when the user mentions an existing project, export and read the local context before answering. Prioritize project memory, `discussion_brief`, `recent_events`, `risk_note`, `project_constraint`, and `latest_system_judgement`. Default to reconnecting in natural language; do not default to an apply payload.

If the user asks to optimize, upgrade, repair, review feedback for, or improve the framework itself, switch to `skills/project-manager-upgrader/` instead. If it is unclear whether the user wants to record project progress or improve the system, ask one short clarifying question before writing.

## Core Rule

Daily skill use must not create Git-tracked artifacts. Generated drafts, usage records, feedback notes, and apply payloads belong under `.agent-workspace/`, which is ignored by Git.

If normal use requires changing tracked files, say that the framework needs an upgrade and ask before editing code, prompts, docs, or this skill.

## Version And Records

- Runtime version source: `pyproject.toml` field `project.version`.
- Skill version source: this `SKILL.md`.
- Usage record path: `.agent-workspace/usage/usage.jsonl`.
- Mini episode path: `.agent-workspace/episodes/YYYY-MM-DD.jsonl`.
- Record meaningful uses only: applying updates, making a project-direction judgement, or noticing framework friction. Do not record every quick read.
- Each apply automatically writes one mini episode for lightweight review. Daily quick reads do not generate episodes.

Use the bundled script for records:

```bash
uv run python skills/project-manager-runtime/scripts/record_usage.py --action apply --write-mode database --summary "Recorded Hermes progress and updated current judgement"
```

Accepted `--write-mode`: `none`, `database`, `workspace`, `framework`.

For framework friction, optionally add structured fields:

- `--friction-type`: `context_missing`, `prompt_ambiguous`, `schema_gap`, `workflow_repetitive`, `ui_gap`, `safety_gate_needed`, `other`.
- `--severity`: `low`, `medium`, `high`.
- `--upgrade-target`: `skill`, `prompt`, `schema`, `cli`, `api`, `ui`, `logging`, `docs`, `other`.

These fields help future maintenance aggregate feedback into small skill, prompt, schema, CLI/API, UI, logging, or docs upgrades.

## Workflow

1. Export context before answering about an existing project:

```bash
uv run python -m app.agent_tools export
```

For discussion-heavy or review tasks, prefer a smaller context:

```bash
uv run python -m app.agent_tools export --brief
uv run python -m app.agent_tools export --group-events
```

2. Read `app/prompts/project_control_panel.md`.

3. Classify the user request:

- Context / Discussion Mode: the user wants to chat about a project, continue a previous thread, think, review, or ask for advice. Read context and project memory, answer in natural language, and stay read-only unless the user explicitly asks to record or confirms a proposed write.
- Work Mode: the user wants analysis, review, synthesis, prioritization, or suggestions inside a project context. Still stay read-only by default; save only if the user asks to preserve the result.
- Record Mode: the user explicitly says record, save, update, write, archive, create, or confirms the Agent's proposed write. Only then create strict JSON and apply it.
- Progress or feedback in Record Mode: add `project_events`.
- Changed project judgement in Record Mode: add `project_updates`.
- Renamed project in Record Mode: add `project_renames`.
- Changed project constraint in Record Mode: add `project_constraint_updates`.
- Changed long-term project memory in Record Mode: add `project_memory_updates`.
- New project in Record Mode: use `project_creations` only after explicit user confirmation.
- Stop a project in Record Mode: prefer `project_deletions` with `mode: "archive"`.
- Framework friction: optionally record feedback in `.agent-workspace/usage/usage.jsonl`; do not patch tracked files unless asked.
- Framework upgrade request: use `skills/project-manager-upgrader/` and do not write project database updates unless explicitly requested.

Recording is not the main path. The value of this runtime is that the Agent can continue project discussion and give useful advice without making the user restate the background. Recording happens only when a discussion or work session produces durable information worth preserving.

## Status And Action Protocol

Use the fixed status and action enums from `app/prompts/project_control_panel.md`.

Status intent:

- `active`: current focus, worth spending effort now.
- `maintain`: stable enough to keep running with low attention.
- `observe`: worth thinking about or validating without execution pressure.
- `paused`: temporarily set aside, can be resumed later.
- `archived`: historical record outside the active project pool.

Action intent:

- `control_action` must be one of the fixed enum values. Do not invent custom action words.
- Keep `control_action_note` within 80 Chinese characters.
- Put longer background into `latest_update` or `project_events`.
- Prefer `project_events` for ordinary progress, thoughts, feedback, decisions, risks, and blockers.
- Use `project_updates` only when the current project judgement changes.
- Use `project_renames` for project name changes; do not maintain the database directly.
- Use `project_constraint_updates` for scope or anti-expansion constraint changes.
- Use `project_memory_updates` when long-term project understanding changes.

## Project Memory

Project Memory is the compressed long-term layer for restoring project context. It includes:

- `origin`
- `current_goal`
- `progress_percent`
- `progress_note`
- `key_judgements`
- `validated_facts`
- `open_questions`
- `discussion_brief`

Use `project_memory_updates` when:

- A new project needs initial memory after creation.
- A project is merged, renamed, or enters a new stage.
- The user explicitly asks for a project summary.
- A key judgement is formed.
- The event stream has grown and should be compressed into durable memory.
- Future project discussion needs clearer background.

Do not use `project_memory_updates` for:

- Ordinary daily progress.
- One-off ideas.
- Facts that are not yet confirmed.
- Mechanical updates on every apply.

## Project Discussion Mode

Use discussion mode when the user asks to discuss, think through, review, or make sense of a specific project without clearly asking to record a change.

Discussion mode should first read memory fields, especially `origin`, `current_goal`, `key_judgements`, `validated_facts`, `open_questions`, `discussion_brief`, plus `recent_events`, `risk_note`, `project_constraint`, and `latest_system_judgement`.

Discussion mode is read-only by default:

- Answer in natural language from the current context.
- Do not create an apply payload just because the conversation is useful.
- Do not write the database unless the user explicitly says to record, save, update, or confirms a proposed write.
- If a multi-turn discussion stays on the same project, keep using the same project context until the user switches topics.

This skill is invoked per turn; it is not a persistent app mode by itself. Conversation context can still carry an ongoing project discussion across turns, and the Agent should treat that as one discussion thread when the project remains clear.

Write after discussion only when durable content has formed and the user has asked for or confirmed recording:

- Use `project_events` for confirmed facts, feedback, decisions, risks, and notable discussion outcomes.
- Use `project_updates` when current judgement, status, control action, risk, or delegation changes.
- Use `project_memory_updates` when the long-term project understanding changes.

When memory is missing or thin, ask 1-3 focused questions instead of turning the project into a form. Prioritize why the project exists, what the current stage is trying to validate, what is already confirmed, and what remains uncertain. Do not invent missing background; put uncertain items in `open_questions` only after the user confirms they should be recorded.

## Work Mode

Use work mode when the user wants help doing thinking work inside a project context: analysis, review, synthesis, planning, prioritization, risk assessment, or drafting recommendations.

Work mode is also read-only by default:

- Use the restored project context to make the output more specific.
- Do not record intermediate analysis, temporary advice, or speculative conclusions.
- If the output contains a stable conclusion worth preserving, suggest what could be recorded and wait for confirmation.
- If the user asks to save the result, switch to Record Mode and use the normal JSON protocol.

4. If writing, create a temporary JSON payload under `.agent-workspace/apply/`.

5. Apply it:

```bash
uv run python -m app.agent_tools apply -f .agent-workspace/apply/<payload>.json
```

6. Record meaningful use with `scripts/record_usage.py`.

7. End by checking:

```bash
git status --short
```

If files outside `.agent-workspace/` changed unexpectedly, explain before continuing.

## Response Style

After a successful write, tell the user:

- which projects changed,
- whether the update was a record, judgement change, creation, or archive,
- what to look for after refreshing the page.

For discussion-only requests, make the judgement clear and say that no project data was written.

For discussion or work mode, you may use this natural-language shape when helpful, but do not force it into every answer:

- 我先按当前项目记忆接上：
- 我对这次输入的判断：
- 接下来值得讨论/推进的问题：
- 是否建议记录：

## Feedback Notes

Keep feedback rare and summary-level. Use `--feedback` when the framework or skill made the task harder, for example:

```bash
uv run python skills/project-manager-runtime/scripts/record_usage.py --action feedback --write-mode workspace --summary "Discussed project priorities without database writes" --feedback "The context export does not show enough recent-event grouping by project."
```

When the friction has a clear shape, include `--friction-type`, `--severity`, and `--upgrade-target` so future system-upgrade work can group similar issues without reading every note manually:

```bash
uv run python skills/project-manager-runtime/scripts/record_usage.py --action feedback --write-mode workspace --summary "Context grouping was insufficient" --feedback "Recent events are not grouped by project." --friction-type context_missing --severity medium --upgrade-target prompt
```

Future maintenance can inspect `.agent-workspace/usage/usage.jsonl` to decide whether the framework or skill should be upgraded. Apply calls also write compact mini episodes to `.agent-workspace/episodes/YYYY-MM-DD.jsonl`; these are for lightweight replay and upgrade review, not full tracing.
