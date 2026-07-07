# Feedback Audit Rule

## Goal

Judge whether the current user input exposes a reusable target Skill or EvoZeus-wrapper defect that should be captured as a lesson or GitHub Issue.

## Required Return Schema

Return only JSON:

```json
{
  "should_capture": true,
  "reason": "The user explicitly said the current direction is wrong, and the failure can repeat without a reusable rule.",
  "route": "target_skill",
  "severity": "P1",
  "evidence_boundary": "redacted_private"
}
```

## Capture When True

- The user clearly expresses dissatisfaction, correction, or direction change.
- The user says an earlier instruction, profile, permission, link, deliverable gate, or workflow was handled wrong.
- The user identifies a repeated failure mode that can be turned into a reusable rule.
- The user asks for wrapper, hook, harness, issue routing, dry-run/full-managed mode, or audit behavior to change.
- The problem is not only a one-off fact update.

## Capture When False

- The user only provides new task facts.
- The user only asks to continue an existing task.
- The issue is a one-off state change with no reusable rule.
- A feedback issue, lesson, or equivalent experience upload was already created in this turn.

## Route

- `target_skill`: the target Skill lacks a domain/business/tool rule.
- `wrapper`: EvoZeus-wrapper lacks capture, routing, hook, mode, or governance mechanics.
- `both`: the target Skill missed a rule and the wrapper failed to capture/route it.
- `none`: no capture is needed.

## Severity

- `P0`: unsafe or blocks reliable Skill use.
- `P1`: misleads important work or causes wrong writes/actions.
- `P2`: repeated friction or missed learning.
- `P3`: minor wording or clarity issue.
