# Changelog

All notable changes to EvoZeus-wrapper are recorded here.

## [Unreleased]

- None yet.

## [v0.6.0] - 2026-07-07

### Changed

- Renamed target repo-local harness infra from `.evozeus` to `.evozeus_evoinfra`.
- Kept global EvoZeus installation and project pointers under `~/.evozeus`.
- Added legacy manifest fallback, conflict detection, migration execution, and JSON output fields for `target_infra_dir`, `legacy_infra_dir`, `manifest_path`, `legacy_manifest_detected`, and `migration_required`.
- Added `loop audit` to produce feedback capture decisions and Skill Feedback Issue drafts.
- Added target templates for feedback policy and audit rule files.

### Verification

- `python3 -m unittest tests/test_evozeus_wrapper_lifecycle.py`
- `python3 scripts/evozeus_wrapper.py harness upgrade-check --target /Users/anthonyf/.codex/skills/daxing-phase2-project-management --latest-version v0.6.0 --json`
- `python3 scripts/evozeus_wrapper.py loop audit --target /Users/anthonyf/.codex/skills/daxing-phase2-project-management --user-input "这个 wrapper 没有自动 issue 回收，有问题" --json`
