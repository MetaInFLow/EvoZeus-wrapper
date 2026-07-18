# Changelog

All notable changes to EvoZeus-wrapper are recorded here.

## [Unreleased]

- None yet.

## [v0.9.0] - 2026-07-18

### Added

- Added apply mode to `publish reinstall`, with full prevalidation, canonical `SKILL.md` validation, safe symlink creation/relinking, explicit `--approve-archive`, deterministic EvoZeus archive placement, and rollback on write failures.
- Added manifest onboarding contracts for installation, invocation, target-owned initialization, and generated child Skills.
- Added `.evozeus-wrapper/docs/onboarding.md` and preflight enforcement for required initialization evidence, non-inherited child hooks, `/hooks` trust review, separate child wrapper lifecycles, and consumer-project smoke tests.

### Fixed

- Fixed `harness upgrade-check` self-comparison when `--latest-version` is omitted. The command now resolves the authoritative GitHub latest release and reports `latest_unknown` with source, timestamp, and error details when lookup fails.
- Updated the Codex `SessionStart` hook to refresh the GitHub latest release after installation instead of relying on an install-time version constant.
- Updated generated guidance so upgrade checks no longer pass the installed wrapper version back as the latest version.

### Changed

- Extended the legacy layout migration to generate the onboarding guide and add a default onboarding contract to migrated manifests.
- Bumped newly generated wrapper harness manifests to `v0.9.0`.

### Verification

- `python3 -m pytest -q`
- `python3 -m py_compile scripts/evozeus_wrapper.py scripts/evozeus_wrapper_bootstrap.py scripts/evozeus_wrapper_lifecycle.py scripts/evozeus_wrapper_preflight.py templates/target/.codex/hooks/evozeus_wrapper_start_check.py`
- Real target dry-run of `harness upgrade-check` without `--latest-version`, confirming authoritative GitHub release discovery.

## [v0.8.0] - 2026-07-18

### Added

- Added `harness migrate-layout` with dry-run and apply modes for the one-time scattered-v1 to consolidated-v2 target migration.
- Added conflict detection, path rewrite, migration records, empty legacy directory cleanup, and layout migration regression coverage.

### Changed

- Consolidated wrapper-owned target artifacts under `.evozeus-wrapper/`.
- Kept only host-required thin entrypoints in `.codex/hooks.json` and `.github/`.
- Changed legacy `.evozeus_evoinfra/` and `.evozeus/wrapper.json` handling from runtime fallback to migration-required input.
- Moved GitHub Pages publishing to a workflow that builds `.evozeus-wrapper/docs/`.
- Bumped newly generated harness manifests to `layout_version=2` and wrapper version `v0.8.0`.

### Verification

- `python3 -m pytest -q`
- `python3 -m py_compile scripts/evozeus_wrapper.py scripts/evozeus_wrapper_bootstrap.py scripts/evozeus_wrapper_lifecycle.py scripts/evozeus_wrapper_preflight.py`
- Temporary v0.7-shaped target dry-run, apply, structure, and runtime migration checks.

## [v0.7.0] - 2026-07-08

### Added

- Added official Codex project-local hook registration to wrapped target harnesses via `.codex/hooks.json`.
- Added the `SessionStart` wrapper adapter at `.codex/hooks/evozeus_wrapper_start_check.py`.
- Recorded Codex hook registration metadata in `.evozeus_evoinfra/wrapper.json`.

### Changed

- Treat complete Codex project-local hook files as `native_host_hook` evidence without requiring a plugin manifest.
- Updated preflight validation, harness upgrade planning, templates, and docs to distinguish official Codex hooks from wrapper CLI commands.
- Bumped the generated wrapper harness version to `v0.7.0`.

### Verification

- `python3 -m unittest tests.test_evozeus_wrapper_lifecycle -v`
- `python3 -m py_compile scripts/evozeus_wrapper_lifecycle.py scripts/evozeus_wrapper_preflight.py scripts/evozeus_wrapper_bootstrap.py templates/target/.codex/hooks/evozeus_wrapper_start_check.py`
- `python3 scripts/evozeus_wrapper.py skill transform --mode bootstrap --target examples/minimal-static-skill --repo MetaInFLow/minimal-static-skill --visibility private --dry-run --json`

## [v0.6.0] - 2026-07-07

### Changed

- Renamed target repo-local harness infra from `.evozeus` to `.evozeus_evoinfra`.
- Kept global EvoZeus installation and project pointers under `~/.evozeus`.
- Added legacy manifest fallback, conflict detection, migration execution, and JSON output fields for `target_infra_dir`, `legacy_infra_dir`, `manifest_path`, `legacy_manifest_detected`, and `migration_required`.
- Added `loop audit` to produce feedback capture decisions and Skill Feedback Issue drafts.
- Routed wrapper feedback audit issues to `MetaInFLow/EvoZeus-wrapper` instead of the target Skill repo.
- Hardened `version` preflight so local changelog versions ahead of GitHub latest release fail unless `--no-release-needed` is explicit.
- Added target templates for feedback policy and audit rule files.

### Verification

- `python3 -m unittest tests/test_evozeus_wrapper_lifecycle.py`
- `python3 scripts/evozeus_wrapper.py harness upgrade-check --target /Users/anthonyf/.codex/skills/daxing-phase2-project-management --latest-version v0.6.0 --json`
- `python3 scripts/evozeus_wrapper.py loop audit --target /Users/anthonyf/.codex/skills/daxing-phase2-project-management --user-input "这个 wrapper 没有自动 issue 回收，有问题" --json`
