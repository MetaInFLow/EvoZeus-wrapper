---
name: evozeus-wrapper-publish-reinstall
description: Use when creating or verifying release readiness and planning runtime symlink reinstall from the canonical Skill repo.
---

# Publish Reinstall

Use this stage after the target Skill harness is ready and before declaring the local runtime updated.

## Command

```bash
python3 scripts/evozeus_wrapper.py publish reinstall \
  --skill-name skill-name \
  --canonical-path /absolute/path/to/canonical/repo \
  --target codex \
  --dry-run \
  --json
```

## Rules

- Runtime install paths must be symlinks to the canonical repo.
- `~/.codex/skills/<skill-name>` is the default runtime pointer.
- `~/.agents/skills/<skill-name>` is optional and must also be a symlink if kept.
- Real directory installs must be archived or confirmed before replacement.

## Stop Conditions

- A real directory install differs from canonical `SKILL.md`.
- The user has not confirmed archive/delete behavior.
- Release readiness checks fail.
