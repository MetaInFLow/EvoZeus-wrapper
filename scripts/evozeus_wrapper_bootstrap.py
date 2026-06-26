#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_TEMPLATE_DIR = ROOT / "templates" / "target"
PREFLIGHT_SCRIPT = ROOT / "scripts" / "evozeus_wrapper_preflight.py"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def ask_visibility() -> str:
    while True:
        value = input("Choose GitHub repo visibility [public/private]: ").strip().lower()
        if value in {"public", "private"}:
            return value
        print("Please type public or private.")


def infer_skill_name(target: Path) -> str:
    skill = target / "SKILL.md"
    if not skill.exists():
        return target.name
    for line in skill.read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"')
    return target.name


def render_text(text: str, replacements: dict[str, str]) -> str:
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def copy_template_file(src: Path, dst: Path, replacements: dict[str, str], force: bool) -> str:
    if dst.exists() and not force:
        return f"skip existing {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_text(encoding="utf-8")
    dst.write_text(render_text(data, replacements), encoding="utf-8")
    return f"write {dst}"


def copy_templates(target: Path, replacements: dict[str, str], force: bool) -> list[str]:
    actions: list[str] = []
    for src in sorted(TARGET_TEMPLATE_DIR.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(TARGET_TEMPLATE_DIR)
        actions.append(copy_template_file(src, target / rel, replacements, force))

    script_dst = target / "scripts" / "evozeus_wrapper_preflight.py"
    if script_dst.exists() and not force:
        actions.append(f"skip existing {script_dst}")
    else:
        script_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PREFLIGHT_SCRIPT, script_dst)
        script_dst.chmod(0o755)
        actions.append(f"write {script_dst}")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap an EvoZeus-wrapper dashboard into a local Skill folder.")
    parser.add_argument("target", help="Path to the local Skill folder.")
    parser.add_argument("--skill-name", help="Display name for the Skill.")
    parser.add_argument("--repo", required=True, help="Target GitHub repo in OWNER/REPO format.")
    parser.add_argument("--visibility", choices=["public", "private"], help="GitHub repo visibility.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing wrapper files.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        fail(f"target folder does not exist: {target}")
    if not (target / "SKILL.md").exists():
        fail(f"target folder must contain SKILL.md: {target}")
    if "/" not in args.repo:
        fail("--repo must use OWNER/REPO format")
    if not TARGET_TEMPLATE_DIR.exists():
        fail(f"template folder missing: {TARGET_TEMPLATE_DIR}")
    if not PREFLIGHT_SCRIPT.exists():
        fail(f"preflight script missing: {PREFLIGHT_SCRIPT}")

    visibility = args.visibility or ask_visibility()
    skill_name = args.skill_name or infer_skill_name(target)
    replacements = {
        "DATE": date.today().isoformat(),
        "REPO_NAME": args.repo,
        "REPO_URL": f"https://github.com/{args.repo}",
        "SKILL_NAME": skill_name,
        "VISIBILITY": visibility,
    }

    actions = copy_templates(target, replacements, args.force)
    print("EvoZeus-wrapper bootstrap complete.")
    print(f"Target: {target}")
    print(f"Repo: {args.repo}")
    print(f"Visibility: {visibility}")
    for action in actions:
        print(f"- {action}")

    visibility_flag = "--public" if visibility == "public" else "--private"
    print("\nNext commands from the target folder:")
    print("python3 scripts/evozeus_wrapper_preflight.py structure")
    print("git init")
    print("git add .")
    print('git commit -m "Initialize wrapped Skill dashboard"')
    print(f"gh repo create {args.repo} --source . {visibility_flag} --push")
    print(f"gh api --method POST repos/{args.repo}/pages -f build_type=legacy -f 'source[branch]=main' -f 'source[path]=/docs'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
