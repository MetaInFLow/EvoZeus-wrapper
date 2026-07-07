---
name: evozeus-wrapper-harness-upgrade
description: Use when checking or upgrading the wrapper harness version embedded in a target Skill repo.
---

# Harness Upgrade

Use this stage to keep target Skill infrastructure aligned with `MetaInFLow/EvoZeus-wrapper`.

## Commands

```bash
python3 scripts/evozeus_wrapper.py hook start-check --target /absolute/path/to/skill --latest-version v0.3.0 --json
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/skill --json
python3 scripts/evozeus_wrapper.py harness upgrade --target /absolute/path/to/skill --latest-version v0.3.0 --dry-run --json
```

Use `hook start-check` at target Skill startup. It decides allow/warn/block and does not write files. Use `harness upgrade-check` and `harness upgrade --dry-run` after a hook warns or blocks.

## Rules

- Skill release version and wrapper harness version are separate axes.
- Only update harness-managed files.
- Do not touch target Skill business rules.
- `SKILL.md` must start, after frontmatter, with `EvoZeus-wrapper 状态检查` before the target Skill's main chain.
- Other `SKILL.md` changes are append-only: add the `EvoZeus-wrapper` section if missing, otherwise append a migration note.
- Record every wrapper migration under `docs/wrapper-migrations/` with from/to wrapper version, planned files, validation, and rollback.
- Update `.evozeus/wrapper.json` only after the migration plan is validated.
- Major wrapper upgrades require explicit user confirmation.

## Stop Conditions

- `.evozeus/wrapper.json` is missing and the user has not approved repair.
- Managed files have local edits and no merge strategy exists.
