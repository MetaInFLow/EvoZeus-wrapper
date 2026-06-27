---
name: evozeus-wrapper-harness-upgrade
description: Use when checking or upgrading the wrapper harness version embedded in a target Skill repo.
---

# Harness Upgrade

Use this stage to keep target Skill infrastructure aligned with `MetaInFLow/EvoZeus-wrapper`.

## Commands

```bash
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/skill --json
python3 scripts/evozeus_wrapper.py harness upgrade --target /absolute/path/to/skill --latest-version v0.2.0 --dry-run --json
```

## Rules

- Skill release version and wrapper harness version are separate axes.
- Only update harness-managed files.
- Do not touch target Skill business rules.
- Major wrapper upgrades require explicit user confirmation.

## Stop Conditions

- `.evozeus/wrapper.json` is missing and the user has not approved repair.
- Managed files have local edits and no merge strategy exists.
