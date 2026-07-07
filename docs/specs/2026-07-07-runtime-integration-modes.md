# Runtime Integration Modes for Wrapped Skills

## Related Issue

- MetaInFLow/EvoZeus-wrapper#4

## Problem

EvoZeus-wrapper used the word `hook` for multiple mechanisms:

- host-native lifecycle hooks that run automatically;
- wrapper CLI commands such as `hook start-check`;
- prompt-level runtime checks written into `SKILL.md`.

That made wrapped Skills look hook-backed even when no host hook was installed.

## Decision

Record the actual integration level in `.evozeus_evoinfra/wrapper.json` and expose it in diagnosis and harness upgrade plans.

Supported modes:

- `native_host_hook`: host/plugin lifecycle hook files and plugin manifests are present.
- `bootstrap_skill`: plugin skill infrastructure is present, but no host hook files are detected.
- `prompt_runtime_check`: a root instruction surface can ask the agent to run checks; this is prompt-compliance fallback.
- `manual_only`: no runtime instruction surface or host integration is detected.

Wrapper CLI commands are not runtime hooks unless a host integration calls them.

## Implementation Plan

- Add `classify_integration_mode` to lifecycle diagnosis.
- Include `integration` in target architecture, target diagnosis, wrapper manifests, and harness upgrade plans.
- Add preflight validation that fails if a manifest claims `native_host_hook` without hook and plugin manifest evidence.
- Update docs and templates to say `integration.mode` instead of treating all checks as hooks.

## Verification Plan

- Unit tests cover single Skill, hook/plugin bundle, and Codex plugin with `hooks: {}`.
- Run `python3 -m unittest tests/test_evozeus_wrapper_lifecycle.py`.
- Run `scripts/evozeus_wrapper.py skill diagnose` against representative targets and inspect `integration.mode`.

## Release Plan

This is a wrapper harness behavior change. The next wrapper release should mention that hook semantics are now explicit and verifiable.
