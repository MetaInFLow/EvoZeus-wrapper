#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from evozeus_wrapper_lifecycle import build_wrapper_manifest, write_wrapper_manifest, WRAPPER_MANAGED_FILES


ROOT = Path(__file__).resolve().parents[1]
TARGET_TEMPLATE_DIR = ROOT / "templates" / "target"
PREFLIGHT_SCRIPT = ROOT / "scripts" / "evozeus_wrapper_preflight.py"
STATUS_SECTION_HEADING = "## EvoZeus-wrapper 状态检查"
EVOLUTION_SECTION_HEADING = "## 自进化方法"
WRAPPER_SECTION_HEADING = "## EvoZeus-wrapper"
LOCAL_PROJECTS_DIR = Path.home() / ".evozeus" / ".projects"
INITIAL_VERSION = "v0.1.0"
WRAPPER_VERSION = "v0.4.0"


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


def require_github_cli() -> None:
    if shutil.which("git") is None:
        fail("git CLI is required before bootstrapping a GitHub-backed Skill wrapper")
    if shutil.which("gh") is None:
        fail("gh CLI is required before bootstrapping a GitHub-backed Skill wrapper")
    result = subprocess.run(["gh", "auth", "status"], text=True, capture_output=True)
    if result.returncode != 0:
        fail("gh is installed but not authenticated; run gh auth login")


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


def ensure_project_pointer(target: Path, repo: str, force: bool) -> list[str]:
    project_dir = local_project_dir(repo)
    actions: list[str] = []

    if project_dir.is_symlink():
        if project_dir.resolve() == target:
            actions.append(f"skip existing pointer {project_dir}")
        elif force:
            project_dir.unlink()
            project_dir.symlink_to(target, target_is_directory=True)
            actions.append(f"update pointer {project_dir} -> {target}")
        else:
            actions.append(f"skip existing pointer {project_dir}; points to {project_dir.resolve()}")
        return actions

    if project_dir.exists():
        actions.append(f"skip existing non-symlink {project_dir}; choose canonical repo before replacing")
        return actions

    project_dir.parent.mkdir(parents=True, exist_ok=True)
    project_dir.symlink_to(target, target_is_directory=True)
    actions.append(f"write pointer {project_dir} -> {target}")

    return actions


def build_evolution_section(replacements: dict[str, str]) -> str:
    return f"""\
{EVOLUTION_SECTION_HEADING}

本 Skill 已由 EvoZeus-wrapper 接入自进化闭环。后续任何行为改动都必须先留下可追踪证据，再进入实现。

源头发现顺序：

1. 先读取本 repo 的 `.evozeus/wrapper.json`，以 `canonical_repo` 作为目标 repo。
2. 再检查 `~/.evozeus/.projects/{replacements["REPO_NAME"]}` 是否存在并指向 canonical repo。
3. 验证 canonical repo 的 git origin / GitHub repo 可访问。
4. 再检查 runtime install：`~/.codex/skills/<skill-name>`、`~/.agents/skills/<skill-name>`；它们只能是指向 canonical repo 的安装指针。
5. 只有 wrapper manifest 和 project pointer 都无法确认时，才进入 GitHub user/org/public search。

进化流程：

1. 使用中出现不满意结果时，先提交 Skill Feedback Issue，写清不满意结果、期望结果、复现场景、证据边界和影响程度。
2. 每次运行本 Skill 前，先执行 `python3 scripts/evozeus_wrapper_preflight.py doctor --repo {replacements["REPO_NAME"]}`，确认 wrapper source contract 成立。
3. 再执行 `python3 scripts/evozeus_wrapper_preflight.py version --repo {replacements["REPO_NAME"]}`，确认 GitHub latest release 没有新版本。
4. 开始修改前，在 `docs/designs/` 新建设计文档，明确 Related issue、优化目标、实现计划、验证计划和 release plan。
5. PR 必须同步更新 `SKILL.md` 与 `CHANGELOG.md`，并通过 `python3 scripts/evozeus_wrapper_preflight.py structure` 和 PR 检查。
6. 合并后用 `vMAJOR.MINOR.PATCH` release tag 和 release notes 固化本次进化，保留可回滚记录。

边界：不要把 raw private session、客户资料、secret、未脱敏商业上下文写入公开 Issue、docs 或 release notes；`~/.evozeus/.projects/{replacements["REPO_NAME"]}/` 应指向 canonical repo，runtime install 不能作为 copied install 或第二事实源直接修改。

Target repo: `{replacements["REPO_NAME"]}`
Visibility: `{replacements["VISIBILITY"]}`
Current Skill version: `{replacements["CURRENT_VERSION"]}`
Wrapper harness version: `{replacements["WRAPPER_VERSION"]}`
"""


def build_status_section(replacements: dict[str, str]) -> str:
    return f"""\
{STATUS_SECTION_HEADING}

执行本 Skill 主链路前，先完成状态检查；只有检查结果为 OK，才继续进入下方原 Skill 流程。

1. Skill release 状态
   - 当前记录版本：`{replacements["CURRENT_VERSION"]}`
   - 检查命令：`python3 scripts/evozeus_wrapper_preflight.py version --repo {replacements["REPO_NAME"]}`
   - 如果 GitHub latest release 更新：先更新 canonical repo，并确认 runtime install 仍指向 canonical repo。
   - 如果本地版本领先 GitHub release：先完成 changelog、验证和 `vMAJOR.MINOR.PATCH` release，再把它当作稳定运行版本。
2. Wrapper harness 状态
   - 当前 wrapper 版本：`{replacements["WRAPPER_VERSION"]}`
   - 事实源：`.evozeus/wrapper.json`
   - 检查命令：在 EvoZeus-wrapper repo 运行 `python3 scripts/evozeus_wrapper.py harness upgrade-check --target <this-skill-repo> --latest-version <wrapper-version> --json`
   - 如果 wrapper 落后：先运行 `harness upgrade --dry-run` 生成迁移方案，再按状态检查前置、其他 wrapper 内容 append-only 的规则迁移。
3. Source contract 状态
   - 检查命令：`python3 scripts/evozeus_wrapper_preflight.py doctor --repo {replacements["REPO_NAME"]}`
   - 如果 `.evozeus/.projects`、git origin 或 runtime install 不一致：先修复为同一个 canonical repo，再继续。

解决顺序：先修 source contract，再修 wrapper harness，最后处理 Skill release。全部 OK 后，再进入主链路。
"""


def build_wrapper_section(replacements: dict[str, str]) -> str:
    return f"""\
{WRAPPER_SECTION_HEADING}

本区由 EvoZeus-wrapper 追加，用来说明本 Skill 的 wrapper harness 路由、版本记录和迁移规则。它不覆盖原 Skill 的业务规则；涉及业务行为变化时，仍必须走 Issue、design doc、PR、CHANGELOG 和 release。

调用 wrapper 的场景：

1. 本 Skill 需要 repo 化、adopt/repair wrapper harness、或确认 canonical source。
2. `.evozeus/wrapper.json` 中的 wrapper harness version 落后于 EvoZeus-wrapper 最新版本。
3. `~/.evozeus/.projects/{replacements["REPO_NAME"]}`、`.codex` 或 `.agents` runtime install 疑似不是同一个 source of truth。
4. 使用反馈需要从 Skill Feedback Issue 进入 design doc、PR、CHANGELOG、release 的自进化闭环。
5. 目标 GitHub repo、release tag、GitHub Pages 或 preflight check 需要创建、诊断或修复。

路由规则：

- 目标 Skill 行为问题：先提交 Skill Feedback Issue，不直接改 runtime install。
- 源头/安装问题：先运行 `python3 scripts/evozeus_wrapper_preflight.py doctor --repo {replacements["REPO_NAME"]}`。
- 结构问题：运行 `python3 scripts/evozeus_wrapper_preflight.py structure`。
- Skill release 问题：运行 `python3 scripts/evozeus_wrapper_preflight.py version --repo {replacements["REPO_NAME"]}`。
- wrapper harness 升级：回到 EvoZeus-wrapper repo，运行 `python3 scripts/evozeus_wrapper.py harness upgrade-check --target <this-skill-repo> --latest-version <wrapper-version> --json`，再用 `harness upgrade --dry-run` 生成迁移方案。

Append-only 迁移规则：

- wrapper 升级必须保留 frontmatter 后的状态检查；其他 `SKILL.md` wrapper 内容只能追加本区缺失内容或 migration note，不要重写原 Skill 业务段落。
- 如果本区已存在，升级时追加 migration note，不改写旧文本。
- 每次 wrapper 升级必须记录 from/to wrapper version、planned files、验证命令、回滚方案和是否需要人工 merge review。
- wrapper version 事实源是 `.evozeus/wrapper.json` 的 `wrapper_version`；Skill release 仍以 GitHub release / `CHANGELOG.md` 为准。

Wrapper harness version: `{replacements["WRAPPER_VERSION"]}`
Wrapper manifest: `.evozeus/wrapper.json`
Wrapper migration log: `docs/wrapper-migrations/`
"""


def has_heading(text: str, heading: str) -> bool:
    return any(line.strip() == heading for line in text.splitlines())


def content_insert_index(text: str) -> int:
    if not text.startswith("---\n"):
        return 0
    end = text.find("\n---\n", 4)
    if end == -1:
        return 0
    return end + len("\n---\n")


def prepend_status_section_if_missing(target: Path, section: str) -> str:
    skill_path = target / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    if has_heading(text, STATUS_SECTION_HEADING):
        return f"skip existing {STATUS_SECTION_HEADING} in {skill_path}"

    insert_at = content_insert_index(text)
    prefix = text[:insert_at].rstrip()
    suffix = text[insert_at:].lstrip()
    if prefix:
        updated = prefix + "\n\n" + section.rstrip() + "\n\n" + suffix
    else:
        updated = section.rstrip() + "\n\n" + suffix
    skill_path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return f"prepend {STATUS_SECTION_HEADING} to {skill_path}"


def append_section_if_missing(target: Path, heading: str, section: str) -> str:
    skill_path = target / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    if has_heading(text, heading):
        return f"skip existing {heading} in {skill_path}"

    updated = text.rstrip() + "\n\n" + section.rstrip() + "\n"
    skill_path.write_text(updated, encoding="utf-8")
    return f"append {heading} to {skill_path}"


def inject_evolution_method(target: Path, replacements: dict[str, str]) -> list[str]:
    return [
        prepend_status_section_if_missing(target, build_status_section(replacements)),
        append_section_if_missing(target, EVOLUTION_SECTION_HEADING, build_evolution_section(replacements)),
        append_section_if_missing(target, WRAPPER_SECTION_HEADING, build_wrapper_section(replacements)),
    ]


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
    require_github_cli()
    repo_check = check_github_repo_available(args.repo)

    visibility = args.visibility or ask_visibility()
    skill_name = args.skill_name or infer_skill_name(target)
    replacements = {
        "DATE": date.today().isoformat(),
        "INITIAL_VERSION": INITIAL_VERSION,
        "CURRENT_VERSION": INITIAL_VERSION,
        "REPO_NAME": args.repo,
        "REPO_URL": f"https://github.com/{args.repo}",
        "SKILL_NAME": skill_name,
        "VISIBILITY": visibility,
        "WRAPPER_VERSION": WRAPPER_VERSION,
    }

    actions = [repo_check]
    actions.extend(copy_templates(target, replacements, args.force))
    actions.extend(ensure_project_pointer(target, args.repo, args.force))
    actions.extend(inject_evolution_method(target, replacements))
    actions.append(
        write_wrapper_manifest(
            target,
            build_wrapper_manifest(args.repo, WRAPPER_VERSION, WRAPPER_MANAGED_FILES, []),
            args.force,
        )
    )
    print("EvoZeus-wrapper bootstrap complete.")
    print(f"Target: {target}")
    print(f"Repo: {args.repo}")
    print(f"Visibility: {visibility}")
    print(f"Initial version: {INITIAL_VERSION}")
    print(f"EvoZeus project pointer: {local_project_dir(args.repo)}")
    for action in actions:
        print(f"- {action}")

    visibility_flag = "--public" if visibility == "public" else "--private"
    print("\nNext commands from the target folder:")
    print(f"python3 scripts/evozeus_wrapper_preflight.py doctor --repo {args.repo} --allow-missing-repo")
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
