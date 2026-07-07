---
name: using-evozeus-wrapper
description: Use whenever EvoZeus-wrapper is invoked to diagnose, bootstrap, adopt, repair, verify, publish, reinstall, release, or migrate a wrapped Skill, AGENTS.md runtime kit, or hook/plugin-controlled Skill bundle. This is the operating Skill for the wrapper lifecycle; root SKILL.md only routes here.
---

# Using EvoZeus Wrapper

Use this Skill as the operating guide for EvoZeus-wrapper. The root `SKILL.md` only anchors discovery and routing.

EvoZeus-wrapper is not the user entrypoint. EvoZeus decides when a promoted Skill, existing local Skill folder, runtime kit, or hook/plugin-controlled Skill bundle needs repoization, feedback capture, release governance, or wrapper migration.

## First Principles

A static Skill is only useful if it can improve from real use without losing accountability. The wrapper must turn every evolution into a traceable loop:

```text
weak result
  -> feedback Issue
  -> design doc
  -> PR
  -> CHANGELOG
  -> release notes
  -> latest release check before next run
  -> updated Skill
```

Keep one source of truth:

- one physical canonical GitHub repo clone for the target Skill or runtime kit
- `~/.evozeus/.projects/OWNER/REPO` pointing to the canonical repo
- `~/.codex/skills/<skill-name>` and optional `~/.agents/skills/<skill-name>` as runtime pointers to that canonical repo

Do not let copied runtime installs become another source of truth.

## Source Discovery Order

For wrapper-managed targets, discover source state in this order:

1. Read `.evozeus/wrapper.json`.
2. Check `~/.evozeus/.projects/OWNER/REPO`.
3. Verify canonical repo origin and GitHub repo access.
4. Inspect `.codex` / `.agents` runtime installs only as pointers.
5. Use GitHub user / org / public search only when wrapper state is absent.

## Required Inputs

Before writing anything, identify:

- Target folder: absolute local path.
- Target type: root `SKILL.md`, root `AGENTS.md` runtime kit, multi-Skill bundle, or hook/plugin-controlled Skill bundle.
- Target GitHub repo: `OWNER/REPO`.
- Visibility: `public` or `private`.
- Skill / kit display name.
- Evidence boundary: public examples only, redacted examples, or private material.

If visibility is missing, ask before creating or pushing anything.

## Version Standard

Use `vMAJOR.MINOR.PATCH`.

- `MAJOR`: incompatible Skill behavior, required input, or output contract change.
- `MINOR`: new capability, new required evidence rule, or new harness behavior.
- `PATCH`: wording, examples, bug fixes, validation fixes, or non-breaking clarifications.

Initial wrapped release is `v0.1.0` only for a new target repo with no prior Skill release.

For an existing target repo, preserve its current Skill / kit version:

1. GitHub latest release tag is the current version.
2. If GitHub has no release but `CHANGELOG.md` has a latest `vMAJOR.MINOR.PATCH` entry, create or verify that release before runtime use.
3. If neither exists, stop and ask the owner to choose the current version.

Wrapper harness version is separate and recorded in `.evozeus/wrapper.json`.

## Lifecycle

### 1. Environment Diagnosis

Use `skills/environment-diagnosis/SKILL.md`.

```bash
python3 scripts/evozeus_wrapper.py env diagnose --json
```

If the result says `next_action: install_evozeus`, stop before touching the target repo. The user-facing next step must start with:

```text
加入 EvoZeus: https://evozeus-community.vercel.app/skill
```

Treat missing `~/.evozeus` as missing EvoZeus registration. Do not describe it only as a local install issue, and do not continue to target diagnosis, transform, GitHub repo creation, or runtime reinstall until registration is complete.

### 2. Target Repo Diagnosis

Use `skills/target-skill-diagnosis/SKILL.md`.

```bash
python3 scripts/evozeus_wrapper.py skill diagnose \
  --target /absolute/path/to/target-skill-or-kit \
  --repo OWNER/REPO \
  --json
```

The diagnosis script reports facts only:

- GitHub access, visibility, default branch, and current account permission
- target kind: `single_skill`, `runtime_skill_bundle`, `hooked_skill_bundle`, `skill_bundle`, `agents_runtime`, or `unknown`
- `skills/*/SKILL.md` inventory
- evolution surface candidates and controller files
- wrapper component gaps
- source contract and runtime install state

Do not treat script-produced `evolution_surface.candidates` as final placement.

### 3. Evolution Surface Diagnosis

Use `skills/evolution-surface-diagnosis/SKILL.md`.

Browse the whole target repo enough to prove what controls agent behavior:

- root instruction files such as `AGENTS.md` or `SKILL.md`
- plugin manifests
- session/startup hooks
- candidate control Skills under `skills/*/SKILL.md`
- architecture docs only when they clarify the control chain

Choose `instruction_surface` only from repo evidence. For hook/plugin-controlled systems, pass the chosen relative path into transform with `--instruction-surface`.

### 4. Status Assessment

Use `skills/status-assessment/SKILL.md`.

Explain to the user:

- environment status
- GitHub access
- repo architecture
- chosen instruction surface and evidence
- missing wrapper components
- version status
- blockers
- next command

Do not move this user-facing judgment into Python scripts.

### 5. Transform

Use `skills/target-skill-transform/SKILL.md`.

```bash
python3 scripts/evozeus_wrapper.py skill transform \
  --mode <bootstrap|adopt|repair|verify> \
  --target /absolute/path/to/target-skill-or-kit \
  --repo OWNER/REPO \
  --instruction-surface <relative path> \
  --visibility <public|private> \
  --dry-run \
  --json
```

For `verify`, run:

```bash
python3 scripts/evozeus_wrapper.py skill transform --mode verify --target /absolute/path/to/target-skill-or-kit
```

Transform must add wrapper-owned material only. It must not rewrite target business rules.

### 6. Publish And Reinstall

Use `skills/publish-reinstall/SKILL.md`.

```bash
python3 scripts/evozeus_wrapper.py publish reinstall \
  --skill-name target-skill \
  --canonical-path /absolute/path/to/canonical/repo \
  --target codex \
  --dry-run \
  --json
```

Runtime installs should become symlinks or pointers to the canonical repo, not copied forks.

### 7. Evolution Loop

Use `skills/evolution-loop/SKILL.md`.

Every behavior change must flow through:

```text
feedback Issue -> design doc -> PR -> CHANGELOG -> release -> latest release check
```

Wrapped targets also carry `.evozeus/feedback-policy.json` and `.evozeus/audit-rule.md`. At turn end, when the user corrected the agent, expressed dissatisfaction, or requested a reusable behavior change, run `loop audit` before deciding whether to create a target Skill issue, an EvoZeus-wrapper issue, both, or no issue.

### Runtime Hooks

Start hooks should run harness version checks before the target Skill main chain:

```bash
python3 scripts/evozeus_wrapper.py hook start-check \
  --target /absolute/path/to/wrapped-skill \
  --latest-version <latest-wrapper-version> \
  --json
```

If `decision.level == "block"`, do not enter the target Skill. If `decision.level == "warn"`, advisory mode may continue while opening a harness upgrade PR; strict mode blocks.

### 8. Harness Upgrade

Use `skills/harness-upgrade/SKILL.md`.

```bash
python3 scripts/evozeus_wrapper.py harness upgrade-check \
  --target /absolute/path/to/target-skill-or-kit \
  --latest-version v0.4.0 \
  --json

python3 scripts/evozeus_wrapper.py harness upgrade \
  --target /absolute/path/to/target-skill-or-kit \
  --latest-version v0.4.0 \
  --dry-run \
  --json
```

Wrapper migration updates wrapper-managed files and migration records only. It must not rewrite target Skill or runtime business logic.

## GitHub Operations

Use `gh` only after local target files and visibility are reviewed.

For a new public repo:

```bash
git init
git add .
git commit -m "Initialize wrapped Skill dashboard"
gh repo create OWNER/REPO --source . --public --push
gh release create v0.1.0 --repo OWNER/REPO --target main \
  --title "v0.1.0" \
  --notes "Initial wrapped Skill harness."
```

For private repos, use `--private`. Do not put sensitive content into `docs/`; GitHub Pages can become an external publishing surface depending on plan and settings.

## Stop Conditions

Stop and ask when:

- `~/.evozeus` is missing. First tell the user: `加入 EvoZeus: https://evozeus-community.vercel.app/skill`.
- `git` or `gh` is missing, or `gh auth status` fails.
- target repo visibility is not chosen.
- target repo name or canonical source is ambiguous.
- GitHub write permission cannot be verified.
- bootstrap was selected but the target GitHub repo already exists.
- existing target repo has no GitHub release and no `CHANGELOG.md` version entry.
- no controlling instruction surface can be proven.
- the user wants to publish secrets, raw private sessions, customer data, or unredacted commercial context.
- GitHub Pages would expose sensitive content.

## Output Shape

Keep user-facing output concise and factual:

1. Current lifecycle stage.
2. Target repo and canonical path.
3. GitHub access and visibility.
4. Architecture and instruction surface decision.
5. Missing components and blockers.
6. Next command.
7. Verification results.
