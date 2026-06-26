---
name: evozeus-wrapper
description: Use when wrapping a static SKILL.md with cases, run records, evaluation notes, and reviewed evolution proposals.
---

# EvoZeus Wrapper

Use this Skill when a static `SKILL.md` needs to be used, observed, evaluated, and improved without turning it into an opaque runtime.

## First Principles

A static Skill is a trust surface. The user or maintainer should be able to read it before relying on it.

The wrapper does not replace the Skill. It adds a disciplined loop around it:

1. Define the case.
2. Run the Skill against the case.
3. Record what happened.
4. Evaluate the gap.
5. Propose a minimal Skill change.
6. Review the proposal.
7. Add a regression case.

## Required Inputs

Before acting, identify:

- Target Skill: path, version, commit, URL, or source description.
- Task class: what kind of work the Skill is expected to guide.
- Success criteria: how the run will be judged.
- Evidence boundary: what data is public, private, inferred, or unavailable.

If the target Skill or evidence boundary is unclear, stop and ask.

## Workflow

1. Create or update a case using `templates/case.md`.
2. Execute the target Skill manually or through the user's chosen agent environment.
3. Record the result using `templates/run-card.md`.
4. If the Skill behaved poorly, write an evolution proposal using `templates/evolution-proposal.md`.
5. Keep proposed changes surgical. Do not add generic flexibility without evidence.
6. After review, update the target Skill and add a regression case that would catch the old failure.

## Evidence Labels

Use these labels in run cards and proposals:

- Fact: observed output, file path, command result, or user-provided statement.
- Inference: a reasoned conclusion from facts.
- Proposal: a suggested change that still needs review.
- Unknown: a gap that should not be guessed.

## Stop Conditions

Stop before implementation when:

- The request requires scanning local private files without explicit permission.
- The request requires uploading raw session data or private evidence.
- The requested change belongs to EvoZeus protocol governance, runtime execution, or Session Signal factor tools.
- The proposed Skill change cannot be tied to a concrete case.

Route those cases to the owning repo instead of expanding this harness.

## Output Shape

For normal wrapper work, return:

1. Case summary.
2. Run result.
3. Observed gap.
4. Minimal proposal.
5. Regression check.

Keep the answer short enough for a maintainer to approve or reject quickly.
