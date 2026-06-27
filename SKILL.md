---
name: evozeus-wrapper
description: Use when EvoZeus routes a promoted or existing local SKILL.md folder into a GitHub-backed self-evolving Skill dashboard with Pages, feedback Issues, design docs, changelog, and preflight checks.
---

# EvoZeus Wrapper

Use this Skill when EvoZeus routes a promoted Skill or existing local Skill folder into a minimal self-evolving dashboard. EvoZeus is the installed root protocol and orchestration layer; this wrapper is a component capability, not a standalone user entrypoint.

## First Principles

A static Skill is only useful if it can improve from real use without losing accountability. The wrapper must turn every evolution into a traceable loop:

```text
bad or weak Skill result
  -> feedback Issue
  -> design doc
  -> PR
  -> CHANGELOG
  -> release notes
  -> latest release check before next run
  -> updated Skill
```

Do not turn this into a runtime, scanner, general prompt platform, or parallel entrypoint to EvoZeus. The output is a GitHub-backed dashboard around one existing local Skill folder.

The local system must keep one source of truth:

- one physical canonical GitHub repo clone for the target Skill.
- `~/.evozeus/.projects/OWNER/REPO`: a pointer to the canonical repo.
- `~/.codex/skills/<skill-name>` and optional `~/.agents/skills/<skill-name>`: runtime pointers to the same canonical repo.

Do not let copied runtime installs become a second source of truth.

For wrapper-managed Skills, source discovery order is fixed:

1. Read `.evozeus/wrapper.json`.
2. Check `~/.evozeus/.projects/OWNER/REPO`.
3. Verify the canonical repo git origin and GitHub repo access.
4. Inspect `.codex` / `.agents` runtime installs only as pointers.
5. Use GitHub user/org/public search only when wrapper state is absent.

## Required Inputs

Before acting, identify:

- Target Skill folder: absolute local path.
- Target GitHub repo: `OWNER/REPO`.
- Visibility: `public` or `private`.
- Skill display name.
- Evidence boundary: whether docs and issues may contain public examples only, redacted examples, or private material.

If visibility is not provided, ask the user to choose `public` or `private` before creating or pushing anything.

## Release Version Standard

Use `vMAJOR.MINOR.PATCH`.

- `MAJOR`: incompatible Skill behavior, required input, or output contract change.
- `MINOR`: new capability, new required evidence rule, or new harness behavior.
- `PATCH`: wording, examples, bug fixes, validation fixes, or non-breaking clarifications.

Initial wrapped release is `v0.1.0` only for a new target repo with no prior Skill release.
If the target Skill already has a GitHub repo, preserve its existing Skill version:

1. GitHub latest release tag is the current Skill version.
2. If GitHub has no release but `CHANGELOG.md` has a latest `vMAJOR.MINOR.PATCH` entry, create or verify that release before runtime use.
3. If neither exists, stop and ask the owner to choose the first Skill version; do not silently reset an existing repo to `v0.1.0`.

Wrapper harness version is a separate axis recorded in `.evozeus/wrapper.json`.
When the wrapper harness version changes, target Skills migrate by wrapper-owned harness records: keep the `EvoZeus-wrapper 状态检查` section immediately after `SKILL.md` frontmatter, add or append the `EvoZeus-wrapper` section, record the migration under `docs/wrapper-migrations/`, and update wrapper-managed files only. Do not rewrite target Skill business rules during wrapper migration.

## Staged Workflow

1. Environment diagnosis:

   ```bash
   python3 scripts/evozeus_wrapper.py env diagnose --json
   ```

2. Target Skill diagnosis:

   ```bash
   python3 scripts/evozeus_wrapper.py skill diagnose --target /absolute/path/to/target-skill --repo OWNER/REPO --json
   ```

   If `.evozeus/wrapper.json` exists, the diagnosis must honor the wrapper-managed source discovery order before checking runtime installs or GitHub search.

3. Ask or confirm repo visibility:
   - `public`: repo and Pages can be publicly inspectable.
   - `private`: repo stays private; GitHub Pages availability depends on plan, and published Pages can still be externally visible. Keep `docs/` sanitized.
4. Transform target Skill using the diagnosed mode:

   ```bash
   python3 scripts/evozeus_wrapper.py skill transform --mode bootstrap --target /absolute/path/to/target-skill --repo OWNER/REPO --visibility private --dry-run --json
   python3 scripts/evozeus_wrapper.py skill transform --mode verify --target /absolute/path/to/target-skill
   ```

5. When bootstrap is appropriate, run the compatibility bootstrap script:

   ```bash
   python3 scripts/evozeus_wrapper_bootstrap.py /absolute/path/to/target-skill \
     --skill-name "Target Skill Name" \
     --repo "OWNER/REPO" \
     --visibility public
   ```

6. Review the generated files in the target folder:
   - `CHANGELOG.md`
   - `WRAPPER.md`
   - `docs/index.md`
   - `docs/design-doc-template.md`
   - `docs/designs/README.md`
   - `docs/wrapper-migrations/README.md`
   - `.github/ISSUE_TEMPLATE/skill-feedback.yml`
   - `.github/pull_request_template.md`
   - `.github/workflows/evozeus-wrapper-preflight.yml`
   - `scripts/evozeus_wrapper_preflight.py`
   - `.evozeus/wrapper.json`
7. Run publish reinstall dry-run:

   ```bash
   python3 scripts/evozeus_wrapper.py publish reinstall --skill-name target-skill --canonical-path /absolute/path/to/canonical/repo --target codex --dry-run --json
   ```

8. Confirm root `SKILL.md` starts with `EvoZeus-wrapper 状态检查` after frontmatter, then contains the self-evolution method and the `EvoZeus-wrapper` section without rewriting the original Skill's business rules.
9. Initialize or reuse git, commit, create the GitHub repo, and push when the user confirms.
10. Create the initial `v0.1.0` release only for a new bootstrap repo; for adopt, keep the existing GitHub latest release or owner-confirmed changelog tag.
11. Enable GitHub Pages from `main` branch `/docs` when supported by repo visibility and GitHub plan.
12. Run the version checks:

   ```bash
   python3 scripts/evozeus_wrapper_preflight.py version --repo OWNER/REPO
   python3 scripts/evozeus_wrapper.py harness upgrade-check --target /absolute/path/to/target-skill --latest-version v0.3.0 --json
   python3 scripts/evozeus_wrapper.py harness upgrade --target /absolute/path/to/target-skill --latest-version v0.3.0 --dry-run --json
   ```

13. Return the repo URL, Pages URL if available, release URL, files added, preflight result, and reinstall plan.

## GitHub Commands

Use `gh` after the target folder has been reviewed:

```bash
git init
git add .
git commit -m "Initialize wrapped Skill dashboard"
gh repo create OWNER/REPO --source . --public --push
gh release create v0.1.0 --repo OWNER/REPO --target main \
  --title "v0.1.0" \
  --notes "Initial wrapped Skill harness."
gh api --method POST repos/OWNER/REPO/pages \
  -f build_type=legacy \
  -f 'source[branch]=main' \
  -f 'source[path]=/docs'
```

For a private repo, use `--private` instead of `--public`.

## Stop Conditions

Stop and ask when:

- The target folder does not contain `SKILL.md`.
- `git` or `gh` is missing, or `gh auth status` fails.
- The target repo name is missing or ambiguous.
- Bootstrap was selected but the target GitHub repo already exists; route to `adopt` instead.
- An existing repo has no GitHub release and no `CHANGELOG.md` version entry.
- GitHub repo existence cannot be verified.
- Visibility is not chosen.
- The user wants to publish raw private session data, secrets, customer data, or unredacted commercial context.
- GitHub Pages would expose sensitive content.

Do not silently choose public/private. That choice changes privacy and contribution boundaries.

## Output Shape

After wrapping a Skill, report:

1. Target Skill folder.
2. GitHub repo URL.
3. Visibility selected.
4. Initial release tag and URL.
5. GitHub Pages URL or Pages setup status.
6. Files added.
7. Preflight check result, including version check.

Keep the answer concise and factual.
