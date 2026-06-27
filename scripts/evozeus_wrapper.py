#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evozeus_wrapper_lifecycle import (
    REQUIRED_WRAPPER_FILES,
    diagnose_environment,
    diagnose_skill,
    plan_reinstall,
    run_command,
    stage_label,
)


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
    skill_transform = skill_sub.add_parser("transform", help="Plan or verify target Skill transform.")
    skill_transform.add_argument("--mode", required=True, choices=["bootstrap", "adopt", "repair", "verify"])
    skill_transform.add_argument("--target", required=True, help="Path to target Skill folder.")
    skill_transform.add_argument("--repo", help="GitHub repo in OWNER/REPO format.")
    skill_transform.add_argument("--visibility", choices=["public", "private"], help="Target repo visibility.")
    skill_transform.add_argument("--dry-run", action="store_true", help="Print planned transform without writing.")
    skill_transform.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")

    publish = sub.add_parser("publish", help="Publish and reinstall lifecycle commands.")
    publish_sub = publish.add_subparsers(dest="command", required=True)
    reinstall = publish_sub.add_parser("reinstall", help="Plan runtime symlink reinstall.")
    reinstall.add_argument("--skill-name", required=True)
    reinstall.add_argument("--canonical-path", required=True)
    reinstall.add_argument("--target", action="append", required=True, help="codex, agents, all, or an explicit install path.")
    reinstall.add_argument("--dry-run", action="store_true", help="Only print planned reinstall actions.")
    reinstall.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")

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
    if args.group == "skill" and args.command == "transform":
        target = Path(args.target)
        if args.mode == "verify":
            preflight = Path(__file__).resolve().parent / "evozeus_wrapper_preflight.py"
            result = run_command([sys.executable, str(preflight), "structure", "--target", str(target)])
            if args.json:
                print(
                    json.dumps(
                        {
                            "stage": "target_skill_transform",
                            "mode": "verify",
                            "target": str(target),
                            "returncode": result["returncode"],
                            "stdout": result["stdout"],
                            "stderr": result["stderr"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print(stage_label("transform"))
                print(result["stdout"], end="")
                print(result["stderr"], end="", file=sys.stderr)
            return int(result["returncode"])

        if not args.dry_run:
            print("write operations are only implemented through dry-run planning for this mode", file=sys.stderr)
            return 1
        planned_files = REQUIRED_WRAPPER_FILES + [".evozeus/wrapper.json", "SKILL.md self-evolution section"]
        report = {
            "stage": "target_skill_transform",
            "mode": args.mode,
            "target": str(target),
            "repo": args.repo,
            "visibility": args.visibility,
            "writes": False,
            "planned_files": planned_files,
        }
        print_report(report, args.json, "transform")
        return 0
    if args.group == "publish" and args.command == "reinstall":
        if not args.dry_run:
            print("write operations are not implemented until archive confirmation is added", file=sys.stderr)
            return 1
        report = plan_reinstall(args.skill_name, Path(args.canonical_path), Path.home(), args.target)
        print_report(report, args.json, "publish")
        return 0

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
