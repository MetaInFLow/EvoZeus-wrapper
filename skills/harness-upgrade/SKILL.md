---
name: evozeus-wrapper-harness-upgrade
description: Use when checking or upgrading the wrapper harness version embedded in a target Skill repo.
---

# Harness Upgrade

Use this stage to keep target Skill infrastructure aligned with `MetaInFLow/EvoZeus-wrapper`.

## Commands

```bash
python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/skill --json
python3 scripts/evozeus_wrapper.py harness migrate-layout --target /absolute/path/to/skill --latest-version v0.10.0 --dry-run --json
python3 scripts/evozeus_wrapper.py harness migrate-layout --target /absolute/path/to/skill --latest-version v0.10.0 --json
python3 scripts/evozeus_wrapper.py harness upgrade-all --latest-version v0.10.0 --dry-run --json
python3 scripts/evozeus_wrapper.py harness upgrade-all --latest-version v0.10.0 --approve --json
```

## Rules

- Skill release version and wrapper harness version are separate axes.
- `upgrade-check` resolves GitHub latest release by default. It may report `latest_unknown`, but must never self-substitute the installed version.
- Only update harness-managed files.
- Do not touch target Skill business rules.
- Preserve Codex project-local hook registration at `.codex/hooks.json`; keep its adapter under `.evozeus-wrapper/hooks/` and label it `repo_maintenance_hook` with `canonical_repository` scope.
- Prevalidate `.codex/hooks.json` as structured JSON, preserve unrelated hooks, and create or refresh exactly one wrapper SessionStart registration.
- `SKILL.md` must start, after frontmatter, with `EvoZeus-wrapper 状态检查` before the target Skill's main chain.
- Other `SKILL.md` changes are append-only: add the `EvoZeus-wrapper` section if missing, otherwise append a migration note.
- Record every wrapper migration under `.evozeus-wrapper/docs/migrations/` with from/to wrapper version, file moves, validation, and rollback.
- Update `.evozeus-wrapper/wrapper.json` to `layout_version=2` only after all destination conflicts are cleared.
- Add the onboarding guide and default onboarding contract during legacy layout migration; do not leave migrated manifests structurally incomplete.
- Refresh the wrapper-owned status prelude and manifest integration, append a migration note, and require structure post-validation before reporting success.
- Keep workflow validation active independently of optional Pages deployment; Pages requires `EVOZEUS_PAGES_ENABLED=true`.
- Old `.evozeus_evoinfra/` and `.evozeus/wrapper.json` paths are migration inputs, not runtime fallbacks.
- Major wrapper upgrades require explicit user confirmation.
- `upgrade-all` must prevalidate every registered target before the first write and restore every target snapshot if any apply step fails.
- A target harness manifest declares global capability ownership and scope, but live user-level dispatcher installation/trust comes from `hook global status` or the diagnosis overlay.
- The global dispatcher is a native `SessionStart` aggregate gate, not a native per-Skill invocation hook.

## Stop Conditions

- `.evozeus-wrapper/wrapper.json` is missing and no legacy layout can be migrated or the user has not approved repair.
- A migration destination differs from its legacy source.
- Managed files, including `.codex/hooks.json` or `.evozeus-wrapper/hooks/evozeus_wrapper_start_check.py`, have local edits and no merge strategy exists.
