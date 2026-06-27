---
name: evozeus-wrapper-target-skill-diagnosis
description: Use when identifying the target Skill, local installs, candidate repos, GitHub repo state, harness state, and publication boundary.
---

# Target Skill Diagnosis

Use this stage after environment diagnosis and before bootstrap, adopt, repair, publish, or reinstall.

## Required Inputs

- Target Skill folder.
- Target GitHub repo in `OWNER/REPO` format when known.
- Skill name override only when `SKILL.md` cannot identify it.

## Command

```bash
python3 scripts/evozeus_wrapper.py skill diagnose \
  --target /absolute/path/to/skill \
  --repo OWNER/REPO \
  --json
```

## Decide

Ask the user only when:

- The target path is missing or does not contain `SKILL.md`.
- Multiple local repos can be the canonical source.
- Multiple install copies differ from the canonical repo.
- Visibility is not explicitly `public` or `private`.
- Private data could enter docs, Issues, release notes, or Pages.

## Stop Conditions

- Target Skill identity is ambiguous.
- The user has not chosen visibility.
- Sensitive data cannot be safely redacted.
