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

- `.evozeus` is missing and EvoZeus needs initialization.
- Multiple `MetaInFLow/EvoZeus` local repos are found.
- `git`, `gh`, or `gh auth status` is unavailable.

## Stop Conditions

- `gh auth status` fails.
- The mother repo cannot be verified and the user has not approved offline diagnosis.
