---
name: evozeus-wrapper
description: Use when turning a local SKILL.md folder into a GitHub-backed self-evolving Skill dashboard with Pages, feedback Issues, design docs, changelog, and preflight checks.
---

# EvoZeus Wrapper

Use this Skill when the user wants to wrap a local Skill folder into a minimal self-evolving dashboard.

## First Principles

A static Skill is only useful if it can improve from real use without losing accountability. The wrapper must turn every evolution into a traceable loop:

```text
bad or weak Skill result
  -> feedback Issue
  -> design doc
  -> PR
  -> CHANGELOG
  -> release notes
  -> updated Skill
```

Do not turn this into a runtime, scanner, or general prompt platform. The output is a GitHub-backed dashboard around one existing local Skill folder.

## Required Inputs

Before acting, identify:

- Target Skill folder: absolute local path.
- Target GitHub repo: `OWNER/REPO`.
- Visibility: `public` or `private`.
- Skill display name.
- Evidence boundary: whether docs and issues may contain public examples only, redacted examples, or private material.

If visibility is not provided, ask the user to choose `public` or `private` before creating or pushing anything.

## Workflow

1. Verify the target folder contains `SKILL.md`.
2. Ask or confirm repo visibility:
   - `public`: repo and Pages can be publicly inspectable.
   - `private`: repo stays private; GitHub Pages availability depends on plan, and published Pages can still be externally visible. Keep `docs/` sanitized.
3. Run the bootstrap script from this repo:

   ```bash
   python3 scripts/evozeus_wrapper_bootstrap.py /absolute/path/to/target-skill \
     --skill-name "Target Skill Name" \
     --repo "OWNER/REPO" \
     --visibility public
   ```

4. Review the generated files in the target folder:
   - `CHANGELOG.md`
   - `WRAPPER.md`
   - `docs/index.md`
   - `docs/design-doc-template.md`
   - `docs/designs/README.md`
   - `.github/ISSUE_TEMPLATE/skill-feedback.yml`
   - `.github/pull_request_template.md`
   - `.github/workflows/evozeus-wrapper-preflight.yml`
   - `scripts/evozeus_wrapper_preflight.py`
5. Run structure verification from the target folder:

   ```bash
   python3 scripts/evozeus_wrapper_preflight.py structure
   ```

6. Initialize or reuse git, commit, create the GitHub repo, and push.
7. Enable GitHub Pages from `main` branch `/docs`.
8. Return the repo URL, Pages URL if available, and the files added.

## GitHub Commands

Use `gh` after the target folder has been reviewed:

```bash
git init
git add .
git commit -m "Initialize wrapped Skill dashboard"
gh repo create OWNER/REPO --source . --public --push
gh api --method POST repos/OWNER/REPO/pages \
  -f build_type=legacy \
  -f 'source[branch]=main' \
  -f 'source[path]=/docs'
```

For a private repo, use `--private` instead of `--public`.

## Stop Conditions

Stop and ask when:

- The target folder does not contain `SKILL.md`.
- The target repo name is missing or ambiguous.
- Visibility is not chosen.
- The user wants to publish raw private session data, secrets, customer data, or unredacted commercial context.
- GitHub Pages would expose sensitive content.

Do not silently choose public/private. That choice changes privacy and contribution boundaries.

## Output Shape

After wrapping a Skill, report:

1. Target Skill folder.
2. GitHub repo URL.
3. Visibility selected.
4. GitHub Pages URL or Pages setup status.
5. Files added.
6. Preflight check result.

Keep the answer concise and factual.
