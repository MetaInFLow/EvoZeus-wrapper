---
name: evozeus-wrapper-evolution-loop
description: Use for lesson intake and Issue-to-PR flow after a Skill has an EvoZeus-wrapper harness.
---

# Evolution Loop

Use this stage after the target Skill is wrapped and installed through canonical repo pointers.

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
