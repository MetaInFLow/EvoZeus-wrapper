# Start Hook Harness Version Check

## Problem

The wrapped target instruction surface says the wrapper harness version should be checked before the target Skill main flow, but that is still prompt-level compliance. A target Skill can start without any runtime check.

## Goal

Expose a hook-facing command that checks the wrapped target's harness version before the target Skill runs:

```bash
python3 scripts/evozeus_wrapper.py hook start-check \
  --target /absolute/path/to/wrapped-skill \
  --latest-version <latest-wrapper-version> \
  --enforcement advisory \
  --json
```

## Decision Contract

The command returns:

- `decision.level`: `allow`, `warn`, or `block`
- `decision.allow`: boolean
- `decision.reason`: why the hook should continue or stop
- `decision.next_action`: matching harness upgrade or repair action
- `harness`: the underlying harness upgrade plan

## Enforcement

- `advisory`: non-breaking upgrades return `warn` and allow start.
- `strict`: any available upgrade blocks start.
- Missing `latest_version` blocks start because the hook cannot prove the harness is current.
- Missing manifest, dirty managed files, major upgrades, and unknown versions block start.

## Safety

The hook command is read-only. It never edits target files or creates PRs. Upgrade work remains in `harness upgrade-check`, `harness upgrade --dry-run`, PR, and release.

## Verification

Unit tests cover advisory warn, strict block, and missing latest version block.
