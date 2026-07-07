# Changelog

All notable changes to {{SKILL_NAME}} are recorded here.

Wrapper harness migrations are recorded under `docs/wrapper-migrations/`. Every wrapper harness migration that changes the installable Skill artifact also gets a Skill patch release entry here, even when target business rules do not change.

## [Unreleased]

### Skill changes

- None yet.

### Feedback / Issues

- None yet.

### Verification

- None yet.

## [{{INITIAL_VERSION}}] - {{DATE}}

### Skill changes

- Initialized the EvoZeus-wrapper self-evolving dashboard.

### Feedback / Issues

- Initial harness creation.

### Verification

- `python3 scripts/evozeus_wrapper_preflight.py runtime`
- `python3 scripts/evozeus_wrapper_preflight.py maintainer`
- `python3 scripts/evozeus_wrapper_preflight.py release --tag {{INITIAL_VERSION}} --release-notes release-notes.md`

## Release Notes Policy

Every release must include:

- The Skill behavior that changed.
- Wrapper harness migration impact, when applicable.
- The related feedback Issue or design doc.
- The verification performed.
- Known limitations or rollback notes.

Release tags must use `vMAJOR.MINOR.PATCH`:

- `MAJOR`: incompatible Skill behavior or output contract change.
- `MINOR`: new capability, new required evidence rule, or new harness behavior.
- `PATCH`: wording, examples, bug fixes, validation fixes, or non-breaking clarifications.
