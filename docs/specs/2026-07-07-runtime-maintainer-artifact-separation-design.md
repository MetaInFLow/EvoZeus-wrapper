# Runtime and Maintainer Artifact Separation Design

## Related Contract

- `docs/specs/2026-07-07-install-artifact-contract.md`
- `docs/harness-contract.md`

## Problem

EvoZeus-wrapper currently transforms a target Skill folder into a wrapped repo, but the generated instruction surface can treat wrapper governance state as a hard prerequisite for running the target Skill.

This mixes three contracts:

- target Skill runtime contract;
- wrapped repo maintainer contract;
- host install contract.

The concrete failure: a user can install only the Skill runtime files, without `.evozeus`, GitHub auth, project pointers, or the EvoZeus-wrapper repo. The current generated status prelude may still require wrapper checks to pass before entering the target Skill business flow.

## Goal

Separate runtime and maintainer artifacts in code, templates, preflight, install planning, and harness upgrade.

Success means:

- runtime-copy installs can run without `.evozeus`;
- symlink installs can expose maintainer files without making them business dependencies;
- wrapper governance checks block maintainer actions, not normal target Skill execution;
- existing wrapped Skills can be upgraded without rerunning bootstrap;
- tests simulate both runtime-copy and maintainer-bundle installs.

## Non-Goals

- Do not redesign every target Skill.
- Do not move target Skill business rules into EvoZeus-wrapper.
- Do not require normal Skill users to install GitHub tooling.
- Do not make `.evozeus` a hidden runtime dependency.
- Do not remove maintainer governance; scope it correctly.

## Design Summary

Add an explicit artifact split:

```text
runtime_bundle = minimum runnable closure of target Skill
maintainer_bundle = runtime_bundle + wrapper governance files
install_mode = symlink | runtime_copy | repo_clone
```

EvoZeus-wrapper becomes responsible for producing and verifying both artifacts. The target Skill instruction surface must remain runtime-safe.

## Artifact Metadata

Extend `.evozeus/wrapper.json` with maintainer metadata and a runtime bundle declaration:

```json
{
  "wrapper_repo": "MetaInFLow/EvoZeus-wrapper",
  "wrapper_version": "vNEXT",
  "canonical_repo": "OWNER/REPO",
  "managed_files": ["WRAPPER.md", "docs/index.md"],
  "install_links": [],
  "runtime_bundle": {
    "instruction_surface": "SKILL.md",
    "required_files": ["SKILL.md"],
    "optional_files": [],
    "external_tools": []
  },
  "install_modes": ["symlink", "runtime_copy", "repo_clone"]
}
```

For runtime-copy installs, the installer must not depend on `.evozeus/wrapper.json` being present after installation. It can use this metadata during packaging, then copy only the runtime bundle files.

## Runtime Bundle Discovery

Add a deterministic helper:

```python
discover_runtime_bundle(target: Path) -> RuntimeBundleSpec
```

Discovery order:

1. Use `runtime_bundle` from `.evozeus/wrapper.json` when present.
2. Otherwise use the selected instruction surface.
3. Include files explicitly referenced by wrapper-recognized declarations.
4. Fall back to a conservative root-level runtime set:
   - `SKILL.md`;
   - `references/**` when the instruction surface references `references/`;
   - `scripts/**` when the instruction surface references `scripts/`;
   - `assets/**` or `templates/**` when referenced;
   - host metadata such as `agents/openai.yaml` when present.

This is intentionally conservative. A runtime-copy installer may include extra runtime resources, but must not include maintainer-only governance files unless requested.

## Maintainer Bundle

Maintainer bundle required files remain wrapper-owned:

- `.evozeus/wrapper.json`;
- `.evozeus/feedback-policy.json`;
- `.evozeus/audit-rule.md`;
- `WRAPPER.md`;
- `docs/index.md`;
- `docs/design-doc-template.md`;
- `docs/designs/README.md`;
- `docs/wrapper-migrations/README.md`;
- `.github/ISSUE_TEMPLATE/skill-feedback.yml`;
- `.github/pull_request_template.md`;
- `.github/workflows/evozeus-wrapper-preflight.yml`;
- `CHANGELOG.md`;
- `scripts/evozeus_wrapper_preflight.py`.

Maintainer checks may fail when these are missing. Runtime checks must not.

## CLI Changes

### Diagnose

Extend `skill diagnose` output:

```json
{
  "runtime_bundle": {
    "status": "ok|missing_required_files",
    "required_files": [],
    "missing_files": []
  },
  "maintainer_bundle": {
    "status": "ok|missing|partial|error",
    "required_files": [],
    "missing_files": []
  },
  "install_mode": "unknown|symlink|runtime_copy|repo_clone"
}
```

### Preflight

Split `structure` into two explicit checks:

```bash
python3 scripts/evozeus_wrapper_preflight.py runtime --target /path/to/skill
python3 scripts/evozeus_wrapper_preflight.py maintainer --target /path/to/repo
```

Keep `structure` as a compatibility alias for `maintainer` until a major wrapper release.

Runtime check:

- does not require `.evozeus`;
- verifies the instruction surface exists;
- verifies declared runtime required files exist;
- flags wrapper status preludes that block business flow without runtime fallback language.

Maintainer check:

- requires wrapper governance files;
- validates `.evozeus/wrapper.json`;
- validates feedback audit files;
- validates wrapper migration docs and templates.

### Publish / Reinstall

Add apply mode:

```bash
python3 scripts/evozeus_wrapper.py publish reinstall \
  --skill-name skill-name \
  --canonical-path /path/to/wrapped-repo \
  --target codex \
  --mode symlink \
  --apply \
  --json
```

Modes:

- `symlink`: host skill path points to maintainer bundle.
- `runtime-copy`: copy only runtime bundle files.
- `repo-clone`: clone or use full repo as install path.

Default should remain dry-run. Apply requires explicit `--apply`.

### Harness Upgrade

Harness upgrade applies only to maintainer bundle. It must:

- read `.evozeus/wrapper.json`;
- discover latest wrapper version from `wrapper_repo` unless explicitly provided;
- fail as `latest_unknown` instead of defaulting latest to current;
- update wrapper-managed files only;
- update runtime bundle metadata only when runtime files change;
- append migration notes;
- add a target Skill patch release entry for the changed installable artifact;
- run both maintainer and runtime checks.

## Template Changes

### Status Prelude

Replace blocking status text with runtime-safe maintainer-mode text:

```text
If this is a maintainer/canonical repo session, run wrapper status checks before changing or releasing the Skill.
If `.evozeus/wrapper.json` or wrapper tooling is unavailable, treat this as a runtime-only install and continue with the target Skill business flow.
Do not block normal Skill execution only because wrapper governance files are absent.
```

### WRAPPER.md

`WRAPPER.md` must state:

- this repo is the maintainer artifact;
- runtime-copy installs may omit `.evozeus`;
- ordinary users should rely on target Skill runtime files;
- maintainers use wrapper checks before modifying or releasing the Skill.

### docs/index.md

Dashboard must label sections as maintainer-facing. It must not imply that all runtime installs include `.evozeus`.

## Test Plan

Add unit tests:

1. Runtime bundle check passes with only `SKILL.md` and referenced runtime files.
2. Runtime bundle check passes when `.evozeus` is absent.
3. Runtime bundle check fails when `SKILL.md` references a missing runtime file.
4. Maintainer bundle check fails when `.evozeus/wrapper.json` is missing.
5. Maintainer bundle check requires feedback audit files.
6. Generated status prelude contains runtime-only fallback language.
7. Generated status prelude does not contain unconditional "only continue after all wrapper checks are OK" language.
8. `publish reinstall --mode runtime-copy --dry-run` lists only runtime files.
9. `publish reinstall --mode symlink --dry-run` points host path to canonical repo.
10. `harness upgrade-check` auto-discovers latest wrapper release or returns `latest_unknown`.

Add fixture tests using a minimal target Skill:

```text
skill/
  SKILL.md
  references/config.md
  scripts/run.mjs
```

and a wrapped maintainer repo:

```text
wrapped-skill/
  SKILL.md
  references/config.md
  scripts/run.mjs
  .evozeus/wrapper.json
  WRAPPER.md
  docs/index.md
```

## Migration Plan

1. Add runtime bundle metadata support while preserving old manifests.
2. Change generated status prelude to runtime-safe language.
3. Add `runtime` and `maintainer` preflight commands.
4. Update `structure` to call maintainer check for compatibility.
5. Update templates.
6. Add latest wrapper auto-discovery.
7. Add install planning for symlink vs runtime-copy.
8. Add apply mode after dry-run output is stable.
9. Run migration plan on an existing wrapped Skill and verify both artifact checks.

## Rollback

If the split creates compatibility issues:

- keep old `structure` behavior as maintainer-only;
- keep old wrapper manifest fields accepted;
- keep symlink install path unchanged;
- revert template status prelude only after confirming runtime-copy installs do not depend on it.

## Acceptance Criteria

The design is complete when:

- docs and templates no longer treat maintainer checks as ordinary runtime prerequisites;
- CLI can tell whether it is checking runtime bundle or maintainer bundle;
- a runtime-copy bundle can be validated without `.evozeus`;
- an existing wrapped Skill can be upgraded through maintainer bundle logic;
- tests cover the two artifact classes and three install modes.
