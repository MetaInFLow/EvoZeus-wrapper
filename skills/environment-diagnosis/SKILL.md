---
name: evozeus-wrapper-environment-diagnosis
description: Use when checking EvoZeus home, mother repo, git, gh, and auth before touching a target Skill.
---

# Environment Diagnosis

Use this stage before target Skill diagnosis or any write operation.

## Required Inputs

- Optional workspace roots to inspect.
- No target Skill path is required in this stage.

## Command

```bash
python3 scripts/evozeus_wrapper.py env diagnose --json
```

## Decide

Ask the user only when:

- `~/.evozeus` is missing and EvoZeus registration is required. The first user-facing line must be: `加入 EvoZeus: https://evozeus-community.vercel.app/skill`.
- Multiple `MetaInFLow/EvoZeus` local repos are found.
- `git`, `gh`, or `gh auth status` is unavailable.

## Stop Conditions

- `~/.evozeus` is missing. Stop before target Skill diagnosis, transform, GitHub writes, or runtime reinstall, and route the user to `加入 EvoZeus: https://evozeus-community.vercel.app/skill`.
- `gh auth status` fails.
- The mother repo cannot be verified and the user has not approved offline diagnosis.
