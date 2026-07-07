---
name: evozeus-wrapper-evolution-loop
description: Use for feedback audit, lesson intake, and Issue-to-PR flow after a Skill has an EvoZeus-wrapper harness.
---

# Evolution Loop

Use this stage after the target Skill is wrapped and installed through canonical repo pointers.

## Feedback Audit

Before ending a turn where the user corrected the agent, expressed dissatisfaction, or requested an evolution behavior change, run:

```bash
python3 scripts/evozeus_wrapper.py loop audit \
  --target /absolute/path/to/wrapped-skill \
  --user-input "<current user input>" \
  --context "<redacted recent context>" \
  --json
```

The target's `.evozeus/audit-rule.md` is the semantic judgment rule. Keyword matching is only a fallback and cannot replace the rule. If another model or hook has already applied the rule, pass its JSON through `--audit-json` so this command can validate routing and next action.

Management mode comes from `.evozeus/feedback-policy.json`:

- `full_managed`: create the issue directly when capture is required.
- `semi_managed`: dry-run and ask the user whether to submit.
- `manual`: report only.

Route issues by audit result:

- `target_skill`: current wrapped Skill repo.
- `wrapper`: `MetaInFLow/EvoZeus-wrapper`.
- `both`: both repos, cross-linked.
- `none`: no issue.

## Lesson Intake

```bash
python3 scripts/evozeus_wrapper.py loop lesson --dry-run --json
```

Ask the user whether to submit a lesson candidate. If approved, submit it as an Issue or lesson entry after checking sensitive data.

## Issue-to-PR

```bash
python3 scripts/evozeus_wrapper.py loop issue-to-pr --dry-run --json
```

Before creating a PR, check GitHub permissions:

- write access: branch and PR in canonical repo.
- fork access only: fork and PR.
- no PR permission: local patch/design doc only.

## Stop Conditions

- Lesson contains raw private session, secret, customer data, or unredacted commercial context.
- `gh auth` fails.
- Private repo access is missing.
