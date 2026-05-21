---
name: project-manager-runtime
description: Use this repository as an external-Agent personal project manager runtime. Use when the user describes project progress, asks what to work on, wants to record or update project state, wants to create/archive a project, or asks for project direction based on the local project context.
---

# Project Manager Runtime

Skill version: `0.1.0`

Use this skill to operate the repository as a project-manager runtime for an external Agent. The user talks naturally; the Agent reads context, decides whether to discuss or write, and keeps the workspace clean.

## Core Rule

Daily skill use must not create Git-tracked artifacts. Generated drafts, usage records, feedback notes, and apply payloads belong under `.agent-workspace/`, which is ignored by Git.

If normal use requires changing tracked files, say that the framework needs an upgrade and ask before editing code, prompts, docs, or this skill.

## Version And Records

- Runtime version source: `pyproject.toml` field `project.version`.
- Skill version source: this `SKILL.md`.
- Usage record path: `.agent-workspace/usage/usage.jsonl`.
- Record meaningful uses only: applying updates, making a project-direction judgement, or noticing framework friction. Do not record every quick read.

Use the bundled script for records:

```bash
uv run python skills/project-manager-runtime/scripts/record_usage.py --action apply --write-mode database --summary "Recorded Hermes progress and updated current judgement"
```

Accepted `--write-mode`: `none`, `database`, `workspace`, `framework`.

## Workflow

1. Export context:

```bash
uv run python -m app.agent_tools export
```

2. Read `app/prompts/project_control_panel.md`.

3. Classify the user request:

- Discussion only: answer from context, do not write the database.
- Progress or feedback: add `project_events`.
- Changed project judgement: add `project_updates`.
- New project: use `project_creations` only after explicit user confirmation.
- Stop a project: prefer `project_deletions` with `mode: "archive"`.
- Framework friction: optionally record feedback in `.agent-workspace/usage/usage.jsonl`; do not patch tracked files unless asked.

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

## Feedback Notes

Keep feedback rare and summary-level. Use `--feedback` when the framework or skill made the task harder, for example:

```bash
uv run python skills/project-manager-runtime/scripts/record_usage.py --action feedback --write-mode workspace --summary "Discussed project priorities without database writes" --feedback "The context export does not show enough recent-event grouping by project."
```

Future maintenance can inspect `.agent-workspace/usage/usage.jsonl` to decide whether the framework or skill should be upgraded.
