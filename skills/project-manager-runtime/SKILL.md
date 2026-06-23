---
name: project-manager-runtime
description: Use this repository as a pure project-manager context runtime. Use when the user mentions an existing project, wants to recover context, recap records, record or update project state, create or archive a project, or needs a handoff packet for work outside the project-manager boundary.
---

# Project Manager Runtime

Skill version: `0.9.0`

Canonical contracts:

- `docs/product-boundary.md`
- `docs/record-contract.md`

## When To Use

- User mentions a tracked project and wants context restored or recapped.
- User explicitly asks to record, save, update, write, archive, or create a project entry.
- User needs documents or facts organized into the project archive (after confirming the write summary).

Switch to `skills/project-manager-upgrader/` for framework upgrades. If unclear whether the user wants a project record or a framework change, ask one short question.

## Modes

| Mode | Trigger | Action |
|------|---------|--------|
| **Context** (default) | Discuss, recap, clarify gaps | Read-only; natural language; no apply JSON |
| **Record** | Explicit save/record or confirmed write summary | Strict JSON → apply |
| **Handoff** | Deep research, iteration, route decisions, execution outside boundary | Context packet → stop |

Intent classification is also tested in `tests/test_intent_contract.py` via `app/contracts/intent.py`.

## Workflow

1. Export context:

```bash
uv run python -m app.agent_tools export --brief
```

2. Read `docs/product-boundary.md` if mode is unclear.

3. **Context:** answer from memory + recent events; at most 1–3 clarifying questions; suggest recording only after user confirms.

4. **Record:** write JSON under `.agent-workspace/apply/`, then:

```bash
uv run python -m app.agent_tools apply -f .agent-workspace/apply/<file>.json
```

Record rules:

- Do not send `system_judgement`.
- Unknown projects are not auto-created.
- Permanent delete requires `confirm_explicit: true` on `project_deletions`.
- See `docs/record-contract.md` for provenance and confirmation.

5. **Handoff:** output packet fields (`target`, `constraints`, `confirmed_facts`, `user_decisions`, `related_documents`, `open_questions`, `requested_task`) and stop.

6. Optional usage log:

```bash
uv run python skills/project-manager-runtime/scripts/record_usage.py --action apply --write-mode database --summary "Short summary"
```

## Guardrails

- Daily use must not create Git-tracked artifacts; use `.agent-workspace/` only.
- Do not perform deep analysis, prioritization, risk rating, or route selection inside this role.
- Do not save agent inference as confirmed facts.

Field enums for Record Mode: `app/prompts/project_control_panel.md`
