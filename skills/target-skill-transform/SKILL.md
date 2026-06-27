---
name: evozeus-wrapper-target-skill-transform
description: Use when bootstrapping, adopting, repairing, or verifying a target Skill harness after diagnosis.
---

# Target Skill Transform

Use this stage only after target Skill diagnosis has identified the canonical repo and harness state.

## Modes

- `bootstrap`: GitHub repo does not exist and harness is missing.
- `adopt`: GitHub repo exists and harness is missing.
- `repair`: harness is partial.
- `verify`: harness is complete or needs structure verification.

## Commands

```bash
python3 scripts/evozeus_wrapper.py skill transform \
  --mode bootstrap \
  --target /absolute/path/to/skill \
  --repo OWNER/REPO \
  --visibility private \
  --dry-run \
  --json

python3 scripts/evozeus_wrapper.py skill transform --mode verify --target /absolute/path/to/skill
```

## Rules

- Do not change target Skill business rules.
- `SKILL.md` changes are append-only: add the self-evolution method and `EvoZeus-wrapper` section if missing.
- Add `docs/wrapper-migrations/README.md` so future wrapper harness upgrades have a migration ledger.
- Do not overwrite existing files without explicit user confirmation.
- Keep `.evozeus/wrapper.json` as the harness manifest.

## Stop Conditions

- Managed files conflict with user edits and no merge decision exists.
- Visibility or data boundary is unresolved.
