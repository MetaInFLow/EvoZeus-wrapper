# Install Artifact Contract

## Problem

EvoZeus-wrapper is a transformation facility. The target Skill is an input artifact, not a subsystem of the wrapper.

The current harness contract mixes three different concerns:

- the target Skill's business runtime contract;
- the wrapped repo's maintainer governance contract;
- the host/runtime installation contract.

That creates a failure mode: wrapper governance files such as `.evozeus/wrapper.json`, GitHub release checks, `gh`, project pointers, and harness upgrade commands can become hard prerequisites for running the target Skill. A user who installs only the Skill may not receive those files or tools, so the business Skill can be blocked by missing maintainer machinery.

## Core Model

```text
Target Skill Source
  -> EvoZeus-wrapper transformation facility
      -> Maintainer Artifact: wrapped Skill repo
      -> Runtime Artifact: installable runnable Skill bundle
      -> Optional Runtime Proxy: hook/start-check/audit integration
```

The wrapper may decorate and govern the target Skill, but it must not turn wrapper governance assets into mandatory runtime dependencies unless the installation mode explicitly guarantees them.

## Entity Boundaries

| Entity | Role | Owns | Must not own |
| --- | --- | --- | --- |
| EvoZeus-wrapper | Transformation facility / builder | diagnosis, planning, migration, governance templates, publish/reinstall commands | target Skill business rules |
| Target Skill Source | Input business capability | `SKILL.md`, referenced business resources, business scripts, domain rules | `.evozeus`, GitHub governance, wrapper release mechanics |
| Wrapped Skill Repo | Maintainer artifact | target Skill source plus `.evozeus`, docs, GitHub templates, preflight, changelog, release governance | assumptions that every runtime install is a full repo clone |
| Runtime Skill Bundle | Install artifact | minimum runnable closure of the target Skill | maintainer-only governance files as hard dependencies |
| Runtime Proxy | Optional host integration | start hook, turn-end audit, advisory checks | edits to target business flow |

## Design Pattern Mapping

| Pattern | Correct use in EvoZeus-wrapper |
| --- | --- |
| Builder / Factory | Build a wrapped repo and runtime artifact from a target Skill input. |
| Decorator | Add governance around the Skill without changing its business semantics. |
| Adapter | Adapt a target Skill to Codex, Agents, GitHub repo, and Pages surfaces. |
| Pipeline / Template Method | Diagnose -> plan -> apply -> verify -> release. |
| Repository Pattern | Canonical repo is the source of truth; runtime installs are deployments. |
| Proxy / Guard | Start hook checks wrapper state before launching, when the host actually provides that hook. |
| Observer | Feedback audit observes session outcomes; it does not belong inside the business execution path. |
| Strategy | Installation mode determines available files: symlink, repo clone, or runtime-copy bundle. |
| Command | CLI commands execute explicit lifecycle actions and report planned writes. |

## Artifact Classes

### Runtime Bundle

The runtime bundle is the minimum closure required to execute the target Skill's business behavior.

It includes:

- the selected instruction surface, usually `SKILL.md`;
- every file directly required by the instruction surface, such as `references/`, templates, assets, and business scripts;
- host metadata needed to display or invoke the Skill, such as `agents/openai.yaml`;
- runtime dependency notes for external tools that the Skill actually uses.

It does not require:

- `.evozeus/`;
- `.github/`;
- `docs/`;
- `CHANGELOG.md`;
- `WRAPPER.md`;
- `scripts/evozeus_wrapper_preflight.py`;
- `gh`, GitHub auth, GitHub releases, or project pointers.

### Maintainer Bundle

The maintainer bundle is the wrapped repo used to evolve, audit, publish, and migrate the Skill.

It includes:

- the full runtime bundle;
- `.evozeus/wrapper.json`;
- `.evozeus/feedback-policy.json`;
- `.evozeus/audit-rule.md`;
- `WRAPPER.md`;
- `docs/index.md`;
- `docs/design-doc-template.md`;
- `docs/designs/`;
- `docs/wrapper-migrations/`;
- `.github/ISSUE_TEMPLATE/skill-feedback.yml`;
- `.github/pull_request_template.md`;
- `.github/workflows/evozeus-wrapper-preflight.yml`;
- `CHANGELOG.md`;
- `scripts/evozeus_wrapper_preflight.py`.

The maintainer bundle may fail preflight when wrapper governance state is broken. That failure must not imply the runtime bundle is unusable for normal business execution.

### Symlink Install

A symlink install points the host runtime path at the maintainer bundle:

```text
~/.codex/skills/<skill-name> -> /path/to/wrapped-repo
```

In this mode, maintainer files are present at runtime because the runtime path is the repo. They are still not business dependencies. Wrapper checks should run through host hooks or explicit maintainer commands, not by blocking target Skill instructions.

### Runtime-Copy Install

A runtime-copy install contains only the runtime bundle. It is valid only if it includes the complete runnable closure of the target Skill.

In this mode, `.evozeus` is expected to be absent. The target Skill must continue business execution when wrapper governance files are missing.

## Injection Rules

1. Wrapper-generated content must not change target business semantics.
2. `SKILL.md` must remain runtime-safe.
3. Any wrapper status prelude inside the instruction surface must be explicitly scoped to maintainer mode or full-repo/symlink install mode.
4. Missing `.evozeus/wrapper.json` must not block normal target Skill execution. It means "runtime-only install" unless the current command is a maintainer command.
5. GitHub release checks, `doctor`, `structure`, PR checks, release checks, and harness upgrade checks belong to the maintainer bundle.
6. Start-check belongs to a runtime proxy/hook. It is not a substitute for a runtime-safe `SKILL.md`.
7. Turn-end feedback audit belongs to a runtime proxy or maintainer workflow. It must not be required to complete the user's current business task.
8. The wrapper may append a maintainer section to the instruction surface only if the section states its activation conditions and fallback behavior.

## Status Prelude Rule

A target instruction surface may contain an EvoZeus-wrapper prelude only in this form:

```text
If this is a maintainer/canonical repo session, run wrapper status checks before changing or releasing the Skill.
If `.evozeus/wrapper.json` or wrapper tooling is unavailable, treat this as a runtime-only install and continue with the target Skill business flow.
Do not block normal Skill execution only because wrapper governance files are absent.
```

The following form is invalid for installable Skills:

```text
Only continue into the target Skill main chain after wrapper, release, and source contract checks are all OK.
```

That rule is valid only for maintainer commands, not for runtime invocation.

## Install Contract

Every transformed Skill must declare its install mode and runtime closure.

Recommended manifest shape:

```json
{
  "runtime_bundle": {
    "instruction_surface": "SKILL.md",
    "required_files": [
      "SKILL.md",
      "references/project-config.md",
      "references/state-gates.md",
      "scripts/build-progress-card.mjs"
    ],
    "external_tools": ["lark-cli"]
  },
  "maintainer_bundle": {
    "required_files": [
      ".evozeus/wrapper.json",
      ".evozeus/feedback-policy.json",
      ".evozeus/audit-rule.md",
      "WRAPPER.md",
      "docs/index.md",
      "scripts/evozeus_wrapper_preflight.py"
    ]
  },
  "install_modes": ["symlink", "runtime_copy", "repo_clone"]
}
```

The exact file can live in `.evozeus/wrapper.json` for maintainer mode, but the runtime bundle contract must also be derivable from visible files or a host install manifest. A runtime-copy installer cannot rely on hidden maintainer metadata that it may omit.

## Upgrade Contract

Harness upgrade operates on the maintainer bundle.

It may:

- update `.evozeus/*`;
- update `WRAPPER.md`;
- update `docs/*`;
- update `.github/*`;
- update `scripts/evozeus_wrapper_preflight.py`;
- append migration notes;
- update wrapper-owned version references.
- add a Skill patch release entry for the changed installable artifact.

It must not:

- rewrite target business rules;
- require `.evozeus` for runtime-copy installs;
- inject blocking maintainer checks into `SKILL.md`;
- assume `latest_version` is current when latest is unknown.

If a harness upgrade affects runtime bundle contents, it must explicitly classify the change as a runtime contract change and verify the runtime-copy install path.

Any harness upgrade that changes the installable Skill artifact must also bump the target Skill release version, normally as `PATCH`. This does not merge the Skill release axis with the wrapper harness axis: `.evozeus/wrapper.json` remains the wrapper version source of truth, while `CHANGELOG.md`, GitHub tag, and GitHub release record the installable Skill artifact version.

## Verification Requirements

Wrapper CI should have separate checks:

1. Maintainer bundle check:
   - validates `.evozeus`, docs, GitHub templates, changelog, preflight, migration records.
2. Runtime bundle check:
   - builds or simulates a runtime-copy install containing only runtime files;
   - ensures the target Skill can be loaded without `.evozeus`;
   - ensures wrapper prelude, if present, has runtime-only fallback language.
3. Symlink install check:
   - verifies the host path points to canonical repo.
4. Upgrade check:
   - verifies wrapper-managed files only;
   - verifies latest wrapper version is discovered from a real source or fails as `latest_unknown`.
   - verifies a corresponding Skill patch release entry exists when wrapper migration changes the installable artifact.

## Acceptance Criteria

This problem is fixed only when all are true:

- A target Skill installed as runtime-copy can run without `.evozeus`.
- A target Skill installed as symlink can access maintainer files but does not treat them as business prerequisites.
- `SKILL.md` no longer contains unconditional "wrapper checks must all pass before business flow" language.
- `structure` checks maintainer completeness and runtime completeness separately.
- `publish reinstall` has an apply path or the docs stop claiming symlink install is guaranteed.
- Harness upgrade can update existing wrapped Skills without rerunning bootstrap.
- Latest wrapper version is auto-discovered or explicitly reported as unknown.
- A wrapper harness migration that changes the installable artifact produces a target Skill patch release.

## Non-goals

- Do not move target Skill business logic into EvoZeus-wrapper.
- Do not make every user install the full maintainer repo.
- Do not make GitHub or `gh` mandatory for normal Skill execution.
- Do not use wrapper governance files as hidden runtime dependencies.
