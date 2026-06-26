#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_TEMPLATE_DIR = ROOT / "templates" / "target"
PREFLIGHT_SCRIPT = ROOT / "scripts" / "evozeus_wrapper_preflight.py"
EVOLUTION_SECTION_HEADING = "## 自进化方法"
LOCAL_PROJECTS_DIR = Path.home() / ".evozeus" / ".projects"
INITIAL_VERSION = "v0.1.0"


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


def validate_repo(repo: str) -> None:
    parts = repo.split("/")
    if len(parts) != 2 or any(part in {"", ".", ".."} for part in parts):
        fail("--repo must use OWNER/REPO format")


def check_github_repo_available(repo: str) -> str:
    cmd = ["gh", "repo", "view", repo, "--json", "nameWithOwner,url,visibility"]
    try:
        result = subprocess.run(cmd, text=True, capture_output=True)
    except FileNotFoundError:
        fail("gh CLI is required to verify whether the target GitHub repo already exists")

    if result.returncode == 0:
        fail(f"GitHub repo already exists: {repo}. Stop before creating a new harness.")

    output = f"{result.stdout}\n{result.stderr}"
    not_found_markers = [
        "Could not resolve to a Repository",
        "Not Found",
        "HTTP 404",
        "repository not found",
    ]
    if any(marker.lower() in output.lower() for marker in not_found_markers):
        return f"verified GitHub repo is available: {repo}"

    fail(f"could not verify whether GitHub repo exists: {repo}\n{output.strip()}")


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


def local_project_dir(repo: str) -> Path:
    owner, name = repo.split("/")
    return LOCAL_PROJECTS_DIR / owner / name


def preserve_project_skill(target: Path, repo: str, replacements: dict[str, str], force: bool) -> list[str]:
    src = target / "SKILL.md"
    project_dir = local_project_dir(repo)
    skill_dst = project_dir / "SKILL.md"
    readme_dst = project_dir / "README.md"
    actions: list[str] = []

    if skill_dst.exists() and not force:
        actions.append(f"skip existing {skill_dst}")
    else:
        skill_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, skill_dst)
        actions.append(f"write {skill_dst}")

    readme = f"""\
# {replacements["SKILL_NAME"]} 本地项目镜像

这个目录是 EvoZeus-wrapper 使用的本地 Skill 项目镜像。

- Repo: `{replacements["REPO_NAME"]}`
- Repo URL: {replacements["REPO_URL"]}
- Bootstrap 时的来源目录：`{target}`
- 保留的 Skill 入口：`SKILL.md`

除非本地 workspace 策略明确允许，不要在这里保存 raw private session、secret、客户资料或未脱敏商业上下文。
"""
    if readme_dst.exists() and not force:
        actions.append(f"skip existing {readme_dst}")
    else:
        readme_dst.parent.mkdir(parents=True, exist_ok=True)
        readme_dst.write_text(readme, encoding="utf-8")
        actions.append(f"write {readme_dst}")

    return actions


def build_evolution_section(replacements: dict[str, str]) -> str:
    return f"""\
{EVOLUTION_SECTION_HEADING}

本 Skill 已由 EvoZeus-wrapper 接入自进化闭环。后续任何行为改动都必须先留下可追踪证据，再进入实现。

1. 使用中出现不满意结果时，先提交 Skill Feedback Issue，写清不满意结果、期望结果、复现场景、证据边界和影响程度。
2. 每次运行本 Skill 前，先执行 `python3 scripts/evozeus_wrapper_preflight.py version --repo {replacements["REPO_NAME"]}`，确认 GitHub latest release 没有新版本。
3. 开始修改前，在 `docs/designs/` 新建设计文档，明确 Related issue、优化目标、实现计划、验证计划和 release plan。
4. PR 必须同步更新 `SKILL.md` 与 `CHANGELOG.md`，并通过 `python3 scripts/evozeus_wrapper_preflight.py structure` 和 PR 检查。
5. 合并后用 `vMAJOR.MINOR.PATCH` release tag 和 release notes 固化本次进化，保留可回滚记录。

边界：不要把 raw private session、客户资料、secret、未脱敏商业上下文写入公开 Issue、docs 或 release notes；repo 化前的本地 Skill 项目镜像放在 `~/.evozeus/.projects/{replacements["REPO_NAME"]}/`。

Target repo: `{replacements["REPO_NAME"]}`
Visibility: `{replacements["VISIBILITY"]}`
Current version: `{replacements["INITIAL_VERSION"]}`
"""


def inject_evolution_method(target: Path, replacements: dict[str, str]) -> str:
    skill_path = target / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    if EVOLUTION_SECTION_HEADING in text:
        return f"skip existing {EVOLUTION_SECTION_HEADING} in {skill_path}"

    section = build_evolution_section(replacements)
    stop_headings = ["## Stop Conditions", "## 停止条件", "## Output Shape", "## 输出格式"]
    insert_at = -1
    for heading in stop_headings:
        marker = f"\n{heading}"
        pos = text.find(marker)
        if pos != -1 and (insert_at == -1 or pos < insert_at):
            insert_at = pos

    if insert_at == -1:
        updated = text.rstrip() + "\n\n" + section + "\n"
    else:
        updated = text[:insert_at].rstrip() + "\n\n" + section + text[insert_at:]

    skill_path.write_text(updated, encoding="utf-8")
    return f"update {skill_path} with {EVOLUTION_SECTION_HEADING}"


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
    validate_repo(args.repo)
    if not TARGET_TEMPLATE_DIR.exists():
        fail(f"template folder missing: {TARGET_TEMPLATE_DIR}")
    if not PREFLIGHT_SCRIPT.exists():
        fail(f"preflight script missing: {PREFLIGHT_SCRIPT}")
    repo_check = check_github_repo_available(args.repo)

    visibility = args.visibility or ask_visibility()
    skill_name = args.skill_name or infer_skill_name(target)
    replacements = {
        "DATE": date.today().isoformat(),
        "INITIAL_VERSION": INITIAL_VERSION,
        "REPO_NAME": args.repo,
        "REPO_URL": f"https://github.com/{args.repo}",
        "SKILL_NAME": skill_name,
        "VISIBILITY": visibility,
    }

    actions = [repo_check]
    actions.extend(copy_templates(target, replacements, args.force))
    actions.extend(preserve_project_skill(target, args.repo, replacements, args.force))
    actions.append(inject_evolution_method(target, replacements))
    print("EvoZeus-wrapper bootstrap complete.")
    print(f"Target: {target}")
    print(f"Repo: {args.repo}")
    print(f"Visibility: {visibility}")
    print(f"Initial version: {INITIAL_VERSION}")
    print(f"Local project mirror: {local_project_dir(args.repo)}")
    for action in actions:
        print(f"- {action}")

    visibility_flag = "--public" if visibility == "public" else "--private"
    print("\nNext commands from the target folder:")
    print("python3 scripts/evozeus_wrapper_preflight.py structure")
    print("git init")
    print("git add .")
    print('git commit -m "Initialize wrapped Skill dashboard"')
    print(f"gh repo create {args.repo} --source . {visibility_flag} --push")
    print(f'gh release create {INITIAL_VERSION} --repo {args.repo} --target main --title "{INITIAL_VERSION}" --notes "Initial wrapped Skill harness for {skill_name}."')
    print(f"gh api --method POST repos/{args.repo}/pages -f build_type=legacy -f 'source[branch]=main' -f 'source[path]=/docs'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
