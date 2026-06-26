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

The target repo must keep two layers separate:

- `~/.evozeus/.projects/OWNER/REPO/SKILL.md`: the local Skill project entry preserved at bootstrap time.
- `SKILL.md`: the repo-ready Skill entry, with an added self-evolution method section.

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

Initial wrapped harness release must be `v0.1.0`.

## Workflow

1. Verify the target folder contains `SKILL.md`.
2. Run dependency and source preflight:

   ```bash
   python3 scripts/evozeus_wrapper_preflight.py doctor --target /absolute/path/to/target-skill --repo OWNER/REPO --allow-missing-repo
   ```

   `git` and `gh` must exist, `gh auth status` must pass, and any existing origin remote must resolve to an accessible GitHub repo. During bootstrap, `--allow-missing-repo` is allowed because the target repo should not exist yet.
3. Ask or confirm repo visibility:
   - `public`: repo and Pages can be publicly inspectable.
   - `private`: repo stays private; GitHub Pages availability depends on plan, and published Pages can still be externally visible. Keep `docs/` sanitized.
4. Verify the target GitHub repo does not already exist:

   ```bash
   gh repo view OWNER/REPO --json nameWithOwner,url,visibility
   ```

   If the repo exists, stop. Do not create a duplicate harness.
5. Run the bootstrap script from this repo:

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
   - `.github/ISSUE_TEMPLATE/skill-feedback.yml`
   - `.github/pull_request_template.md`
   - `.github/workflows/evozeus-wrapper-preflight.yml`
   - `scripts/evozeus_wrapper_preflight.py`
7. Run structure verification from the target folder:

   ```bash
   python3 scripts/evozeus_wrapper_preflight.py structure
   ```

8. Confirm `~/.evozeus/.projects/OWNER/REPO/SKILL.md` contains the original Skill entry.
9. Confirm root `SKILL.md` contains the self-evolution method and still preserves the original Skill's business rules.
10. Initialize or reuse git, commit, create the GitHub repo, and push.
11. Create the initial `v0.1.0` release.
12. Enable GitHub Pages from `main` branch `/docs` when supported by repo visibility and GitHub plan.
13. Run the version check:

   ```bash
   python3 scripts/evozeus_wrapper_preflight.py version --repo OWNER/REPO
   ```

14. Return the repo URL, Pages URL if available, release URL, files added, and preflight result.

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
- The target GitHub repo already exists.
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
