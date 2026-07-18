---
name: evozeus-wrapper-publish-reinstall
description: Use when creating or verifying release readiness and planning or applying runtime symlink reinstall from the canonical Skill repo.
---

# Publish Reinstall

Use this stage after the target Skill harness is ready and before declaring the local runtime updated.

## Commands

```bash
python3 scripts/evozeus_wrapper.py publish reinstall \
  --skill-name skill-name \
  --canonical-path /absolute/path/to/canonical/repo \
  --target codex \
  --dry-run \
  --json

python3 scripts/evozeus_wrapper.py publish reinstall \
  --skill-name skill-name \
  --canonical-path /absolute/path/to/canonical/repo \
  --target codex \
  --json
```

If a real directory must be replaced after reviewing the dry-run, add `--approve-archive`. The directory moves under `~/.evozeus/archives/runtime-installs/`; it is never deleted.

## Rules

- Runtime install paths must be symlinks to the canonical repo.
- `~/.codex/skills/<skill-name>` is the default runtime pointer.
- `~/.agents/skills/<skill-name>` is optional and must also be a symlink if kept.
- The canonical path must be an existing directory containing `SKILL.md`.
- All targets are prevalidated before any write. One blocked target means zero writes.
- Real directory installs require explicit archive approval before replacement, even when `SKILL.md` is identical.
- A differing real directory may be archived only with the same explicit approval; preserve its archive path in the JSON report.
- Files and other unsupported install types require manual handling.

## Stop Conditions

- A real directory exists and `--approve-archive` was not supplied.
- The install path is an unsupported type.
- Release readiness checks fail.
