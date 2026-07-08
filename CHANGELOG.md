# Changelog

All notable changes to EvoZeus-wrapper are recorded here.

## [Unreleased]

- None yet.

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
