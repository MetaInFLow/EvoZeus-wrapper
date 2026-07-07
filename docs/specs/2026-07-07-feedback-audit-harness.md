# Feedback Audit Harness Design

## Problem

The wrapper currently scaffolds feedback Issues and release governance, but it does not force a wrapped Skill to decide whether a user's correction or dissatisfaction should become reusable experience. The result is a prompt-level convention: agents may continue the current task and forget to capture the learning.

## Goal

Add a configurable feedback audit harness that can be invoked by a turn-end hook or agent closeout:

```text
current user input
  -> check existing capture evidence
  -> apply target .evozeus/audit-rule.md
  -> return should_capture / reason / route / severity
  -> route to target Skill issue, wrapper issue, both, or none
```

## Non-Goal

The audit command does not directly publish raw private context. Full-managed mode means the hook's write layer may create an Issue after the audit result and redaction boundary are satisfied.

## Configuration

`.evozeus/feedback-policy.json` defines:

- `management_mode`: `full_managed`, `semi_managed`, or `manual`.
- `strictness`: `weak`, `medium`, or `strong`.
- `audit_rule`: path to the semantic audit rule, default `.evozeus/audit-rule.md`.
- `capture_evidence_regex`: patterns that prove an Issue, lesson, or equivalent experience upload already happened.
- `routing`: target Skill, wrapper, or both ownership conditions.

`.evozeus/audit-rule.md` defines the model-facing audit requirements and return schema.

## CLI

```bash
python3 scripts/evozeus_wrapper.py loop audit \
  --target /absolute/path/to/wrapped-skill \
  --user-input "<current user input>" \
  --context "<redacted recent context>" \
  --capture-log "<recent assistant/tool summary>" \
  --json
```

If a hook or model has already applied the audit rule, pass the result:

```bash
python3 scripts/evozeus_wrapper.py loop audit \
  --target /absolute/path/to/wrapped-skill \
  --user-input "<current user input>" \
  --audit-json '{"should_capture":true,"reason":"...","route":"wrapper","severity":"P1"}' \
  --json
```

## Decision Contract

The result always includes:

- `decision.should_capture`
- `decision.reason`
- `decision.route`: `target_skill`, `wrapper`, `both`, or `none`
- `decision.next_action`: `pass`, `dry_run_prompt_for_submission`, `report_only`, or `create_issue`
- `semantic_audit_required`: true when no explicit semantic judgment was passed and the policy requires medium/strong audit.

## Safety

The command can inspect raw input locally but does not write external Issues. A write hook must enforce evidence boundary and redaction before creating GitHub Issues.

## Verification

- Unit tests cover existing capture evidence, wrapper-route fallback, and full-managed audit JSON.
- CLI smoke tests should cover default policy, custom policy, and capture evidence skip.
