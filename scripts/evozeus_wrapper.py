#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evozeus_wrapper_lifecycle import diagnose_environment, diagnose_skill, stage_label


def print_report(report: dict, as_json: bool, stage: str) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print(stage_label(stage))
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run staged EvoZeus-wrapper lifecycle commands.")
    sub = parser.add_subparsers(dest="group", required=True)

    env = sub.add_parser("env", help="Environment lifecycle commands.")
    env_sub = env.add_subparsers(dest="command", required=True)
    env_diag = env_sub.add_parser("diagnose", help="Diagnose EvoZeus environment readiness.")
    env_diag.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")

    skill = sub.add_parser("skill", help="Target Skill lifecycle commands.")
    skill_sub = skill.add_subparsers(dest="command", required=True)
    skill_diag = skill_sub.add_parser("diagnose", help="Diagnose target Skill state.")
    skill_diag.add_argument("--target", required=True, help="Path to target Skill folder.")
    skill_diag.add_argument("--repo", help="GitHub repo in OWNER/REPO format.")
    skill_diag.add_argument("--skill-name", help="Override Skill name.")
    skill_diag.add_argument("--workspace-root", action="append", default=[], help="Additional local workspace root to inspect.")
    skill_diag.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")

    args = parser.parse_args()
    if args.group == "env" and args.command == "diagnose":
        print_report(diagnose_environment(Path.home()), args.json, "environment")
        return 0
    if args.group == "skill" and args.command == "diagnose":
        report = diagnose_skill(
            target=Path(args.target),
            repo=args.repo,
            skill_name=args.skill_name,
            workspace_roots=[Path(path) for path in args.workspace_root],
        )
        print_report(report, args.json, "target_skill")
        return 0

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
