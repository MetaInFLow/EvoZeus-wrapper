#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evozeus_wrapper_lifecycle import (
    REQUIRED_WRAPPER_FILES,
    detect_target_architecture,
    diagnose_environment,
    diagnose_skill,
    plan_reinstall,
    plan_harness_upgrade,
    classify_pr_permission,
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
    skill_transform.add_argument(
        "--instruction-surface",
        help="Instruction surface selected by skills/evolution-surface-diagnosis/SKILL.md.",
    )
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

    loop = sub.add_parser("loop", help="Continuous evolution loop commands.")
    loop_sub = loop.add_subparsers(dest="command", required=True)
    lesson = loop_sub.add_parser("lesson", help="Plan lesson candidate intake.")
    lesson.add_argument("--dry-run", action="store_true", help="Only print next action.")
    lesson.add_argument("--json", action="store_true")
    issue_to_pr = loop_sub.add_parser("issue-to-pr", help="Plan Issue-to-PR flow.")
    issue_to_pr.add_argument("--write-permission", action="store_true")
    issue_to_pr.add_argument("--fork-permission", action="store_true")
    issue_to_pr.add_argument("--dry-run", action="store_true", help="Only print next action.")
    issue_to_pr.add_argument("--json", action="store_true")

    harness = sub.add_parser("harness", help="Wrapper harness maintenance commands.")
    harness_sub = harness.add_subparsers(dest="command", required=True)
    upgrade_check = harness_sub.add_parser("upgrade-check", help="Check target wrapper harness version.")
    upgrade_check.add_argument("--target", required=True)
    upgrade_check.add_argument("--latest-version", help="Latest wrapper version, such as v0.4.0.")
    upgrade_check.add_argument("--managed-dirty", action="store_true")
    upgrade_check.add_argument("--json", action="store_true")
    upgrade = harness_sub.add_parser("upgrade", help="Plan wrapper harness upgrade.")
    upgrade.add_argument("--target", required=True)
    upgrade.add_argument("--latest-version", required=True)
    upgrade.add_argument("--managed-dirty", action="store_true")
    upgrade.add_argument("--dry-run", action="store_true")
    upgrade.add_argument("--json", action="store_true")

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
        architecture = detect_target_architecture(target)
        instruction_surface = args.instruction_surface or architecture["root_entry"]
        requires_surface_diagnosis = not args.instruction_surface and architecture["target_kind"] == "hooked_skill_bundle"
        surface_planned_files = []
        if instruction_surface:
            surface_planned_files = [
                f"{instruction_surface} EvoZeus-wrapper status check section",
                f"{instruction_surface} self-evolution section",
                f"{instruction_surface} EvoZeus-wrapper section",
            ]
        planned_files = REQUIRED_WRAPPER_FILES + [
            ".evozeus/wrapper.json",
        ] + surface_planned_files
        report = {
            "stage": "target_skill_transform",
            "mode": args.mode,
            "target": str(target),
            "repo": args.repo,
            "visibility": args.visibility,
            "writes": False,
            "target_kind": architecture["target_kind"],
            "requires_surface_diagnosis": requires_surface_diagnosis,
            "instruction_surface": instruction_surface,
            "instruction_surface_source": "diagnosis_skill" if args.instruction_surface else "root_entry_fallback",
            "integration": architecture["integration"],
            "evolution_surface": architecture["evolution_surface"],
            "planned_files": planned_files,
            "version_rule": (
                "bootstrap uses v0.1.0 as the first Skill release; adopt/repair must preserve the existing "
                "GitHub latest release or owner-confirmed CHANGELOG version"
            ),
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
    if args.group == "loop" and args.command == "lesson":
        if not args.dry_run:
            print("lesson submission requires explicit confirmation and is not implemented in this command yet", file=sys.stderr)
            return 1
        report = {
            "stage": "continuous_evolution_loop",
            "flow": "lesson_intake",
            "writes": False,
            "next_action": "ask_user_whether_to_submit_lesson",
        }
        print_report(report, args.json, "loop")
        return 0
    if args.group == "loop" and args.command == "issue-to-pr":
        if not args.dry_run:
            print("Issue-to-PR writes require explicit confirmation and are not implemented yet", file=sys.stderr)
            return 1
        report = {
            "stage": "continuous_evolution_loop",
            "flow": "issue_to_pr",
            "writes": False,
            "permission_mode": classify_pr_permission(args.write_permission, args.fork_permission),
        }
        print_report(report, args.json, "loop")
        return 0
    if args.group == "harness" and args.command == "upgrade-check":
        report = plan_harness_upgrade(
            target=Path(args.target),
            latest_version=args.latest_version,
            managed_dirty=args.managed_dirty,
        )
        print_report(report, args.json, "loop")
        return 0
    if args.group == "harness" and args.command == "upgrade":
        if not args.dry_run:
            print("harness upgrade writes require explicit confirmation and are not implemented yet", file=sys.stderr)
            return 1
        report = plan_harness_upgrade(
            target=Path(args.target),
            latest_version=args.latest_version,
            managed_dirty=args.managed_dirty,
        )
        print_report(report, args.json, "loop")
        return 0

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
