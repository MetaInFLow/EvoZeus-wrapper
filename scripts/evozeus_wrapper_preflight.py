#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_FILES = [
    "SKILL.md",
    "CHANGELOG.md",
    "WRAPPER.md",
    "docs/index.md",
    "docs/_config.yml",
    "docs/design-doc-template.md",
    "docs/designs/README.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/skill-feedback.yml",
    ".github/pull_request_template.md",
    ".github/workflows/evozeus-wrapper-preflight.yml",
    "scripts/evozeus_wrapper_preflight.py",
]

ISSUE_TERMS = [
    ["不满意", "unsatisfactory", "bad result"],
    ["期望", "expected"],
    ["复现", "reproduction", "scenario", "场景"],
    ["证据边界", "evidence boundary"],
    ["影响", "impact"],
]

DESIGN_TERMS = [
    ["related issue", "修复", "issue"],
    ["optimization goal", "优化目标"],
    ["direction", "优化方向"],
    ["implementation plan", "怎么优化", "实现"],
    ["verification plan", "验证"],
    ["release plan", "release", "发布"],
]

SKILL_EVOLUTION_TERMS = [
    ["自进化"],
    ["~/.evozeus/.projects", ".evozeus/.projects"],
    ["version --repo"],
    ["Skill Feedback Issue", "feedback issue"],
    ["docs/designs", "design doc"],
    ["CHANGELOG.md"],
    ["release tag", "release notes"],
]

PLACEHOLDER_PATTERNS = [
    r"\{\{[A-Z_]+\}\}",
    r"<short title>",
    r"<path>",
    r"<design-doc>",
    r"\bTBD\b",
    r"待填写",
]

VERSION_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"OK: {message}")


def read_text(path: Path) -> str:
    if not path.exists():
        fail(f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def has_any(text: str, terms: list[str]) -> bool:
    low = normalize(text)
    return any(term.lower() in low for term in terms)


def has_real_content(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 40:
        return False
    return not any(re.search(pattern, stripped, re.IGNORECASE) for pattern in PLACEHOLDER_PATTERNS)


def version_key(tag: str) -> tuple[int, int, int]:
    match = VERSION_RE.fullmatch(tag)
    if not match:
        fail(f"release tag must use vMAJOR.MINOR.PATCH format: {tag}")
    return tuple(int(part) for part in match.groups())


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def require_command(command: str) -> None:
    if shutil.which(command) is None:
        fail(f"missing required dependency: {command}")


def repo_from_remote(remote_url: str) -> str | None:
    remote_url = remote_url.strip()
    match = re.match(r"^https://github\.com/([^/]+/[^/.]+)(?:\.git)?$", remote_url)
    if match:
        return match.group(1)
    match = re.match(r"^git@github\.com:([^/]+/[^/.]+)(?:\.git)?$", remote_url)
    if match:
        return match.group(1)
    return None


def gh_current_login() -> str | None:
    result = run_command(["gh", "api", "user", "--jq", ".login"])
    return result.stdout.strip() if result.returncode == 0 else None


def gh_orgs() -> list[str]:
    result = run_command(["gh", "api", "user/orgs", "--jq", ".[].login"])
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def gh_search_repos(query: str) -> list[str]:
    result = run_command(["gh", "search", "repos", query, "--json", "fullName", "--limit", "10"])
    if result.returncode != 0:
        return []
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return [row["fullName"] for row in rows if row.get("fullName")]


def discover_repo_candidates(skill_name: str) -> list[str]:
    candidates: list[str] = []
    login = gh_current_login()
    if login:
        candidates.extend(gh_search_repos(f"{skill_name} user:{login}"))
    for org in gh_orgs():
        for repo in gh_search_repos(f"{skill_name} org:{org}"):
            if repo not in candidates:
                candidates.append(repo)
    if candidates:
        return candidates
    for repo in gh_search_repos(skill_name):
        if repo not in candidates:
            candidates.append(repo)
    return candidates


def is_repo_not_found(output: str) -> bool:
    markers = [
        "Could not resolve to a Repository",
        "Not Found",
        "HTTP 404",
        "repository not found",
    ]
    return any(marker.lower() in output.lower() for marker in markers)


def check_terms(text: str, term_groups: list[list[str]], label: str) -> None:
    missing = []
    for group in term_groups:
        if not has_any(text, group):
            missing.append("/".join(group))
    if missing:
        fail(f"{label} missing required concepts: {', '.join(missing)}")


def check_doctor(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    require_command("git")
    require_command("gh")

    auth = run_command(["gh", "auth", "status"])
    if auth.returncode != 0:
        fail("gh is installed but not authenticated; run gh auth login")
    ok("gh authenticated")

    repo = args.repo
    if repo and not GITHUB_REPO_RE.match(repo):
        fail(f"--repo must use OWNER/REPO format: {repo}")

    git_root_result = run_command(["git", "-C", str(target), "rev-parse", "--show-toplevel"])
    if git_root_result.returncode == 0:
        git_root = Path(git_root_result.stdout.strip())
        remote_result = run_command(["git", "-C", str(git_root), "remote", "get-url", "origin"])
        if remote_result.returncode == 0:
            remote_repo = repo_from_remote(remote_result.stdout)
            if remote_repo:
                repo = repo or remote_repo
                ok(f"origin GitHub repo detected: {remote_repo}")
            else:
                fail(f"origin remote is not a GitHub repo: {remote_result.stdout.strip()}")
        elif not repo:
            fail("target is a git repo but origin remote is missing; pass --repo OWNER/REPO")
    elif not repo:
        candidates = discover_repo_candidates(target.name)
        if candidates:
            repo = candidates[0]
            ok(f"target is not a git repo; discovered candidate repo: {repo}")
        else:
            fail("target is not a git repo and no --repo was provided")

    if repo:
        view = run_command(["gh", "repo", "view", repo, "--json", "nameWithOwner,url,visibility"])
        if view.returncode != 0:
            detail = (view.stderr or view.stdout or "").strip()
            if args.allow_missing_repo and is_repo_not_found(detail):
                ok(f"GitHub repo is available to create: {repo}")
                return
            fail(f"cannot access GitHub repo {repo}: {detail}")
        ok(f"GitHub repo accessible: {repo}")


def check_structure(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    missing = [path for path in REQUIRED_FILES if not (target / path).exists()]
    if missing:
        fail("missing required wrapper files:\n" + "\n".join(f"- {path}" for path in missing))
    skill_text = read_text(target / "SKILL.md")
    check_terms(skill_text, SKILL_EVOLUTION_TERMS, "SKILL.md self-evolution method")
    ok("structure contains required wrapper files")


def check_issue(args: argparse.Namespace) -> None:
    body = read_text(Path(args.file))
    check_terms(body, ISSUE_TERMS, "issue")
    if not has_real_content(body):
        fail("issue body looks empty or placeholder-only")
    ok("issue body satisfies feedback template concepts")


def find_design_doc(target: Path) -> Path:
    docs_dir = target / "docs" / "designs"
    candidates = [
        path
        for path in docs_dir.glob("*.md")
        if path.name.lower() != "readme.md" and "template" not in path.name.lower()
    ]
    if not candidates:
        fail("no design doc found under docs/designs/*.md")
    return sorted(candidates)[-1]


def changelog_has_unreleased_entry(changelog: str) -> bool:
    match = re.search(r"^## \[?Unreleased\]?.*?(?=^## |\Z)", changelog, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not match:
        return False
    section = match.group(0)
    lines = [
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith("-") and "none yet" not in line.lower()
    ]
    return bool(lines)


def check_design_doc(path: Path) -> None:
    text = read_text(path)
    check_terms(text, DESIGN_TERMS, f"design doc {path}")
    if not has_real_content(text):
        fail(f"design doc looks placeholder-only: {path}")
    ok(f"design doc has required concepts: {path}")


def check_pr(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    design_doc = Path(args.design_doc).resolve() if args.design_doc else find_design_doc(target)
    check_design_doc(design_doc)

    changelog = read_text(target / "CHANGELOG.md")
    if not changelog_has_unreleased_entry(changelog):
        fail("CHANGELOG.md must contain a non-empty Unreleased entry for the PR")
    ok("CHANGELOG.md has an Unreleased entry")

    if args.pr_body:
        body = read_text(Path(args.pr_body))
        if "design doc" not in normalize(body) and "设计" not in body:
            fail("PR body should reference the design doc")
        if "CHANGELOG.md" not in body:
            fail("PR body should confirm CHANGELOG.md was updated")
        ok("PR body references design doc and changelog")


def changelog_has_tag(changelog: str, tag: str) -> bool:
    escaped = re.escape(tag)
    return bool(re.search(rf"^##\s+\[?{escaped}\]?\b", changelog, re.MULTILINE))


def latest_changelog_tag(changelog: str) -> str | None:
    for match in re.finditer(r"^##\s+\[?(v\d+\.\d+\.\d+)\]?\b", changelog, re.MULTILINE):
        return match.group(1)
    return None


def release_body_from_gh(tag: str, repo: str | None) -> str | None:
    cmd = ["gh", "release", "view", tag, "--json", "body", "-q", ".body"]
    if repo:
        cmd.extend(["--repo", repo])
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout


def latest_release_from_gh(repo: str) -> dict[str, str]:
    cmd = ["gh", "release", "view", "--repo", repo, "--json", "tagName,url,publishedAt"]
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    except FileNotFoundError:
        fail("gh CLI is required to check the latest GitHub release")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        fail(f"could not read latest GitHub release for {repo}: {detail}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        fail(f"could not parse gh release output for {repo}")
    if not data.get("tagName"):
        fail(f"latest GitHub release for {repo} has no tagName")
    return data


def check_release(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    version_key(args.tag)
    changelog = read_text(target / "CHANGELOG.md")
    if not changelog_has_tag(changelog, args.tag):
        fail(f"CHANGELOG.md must contain a release entry for {args.tag}")
    ok(f"CHANGELOG.md contains {args.tag}")

    body = ""
    if args.release_notes:
        body = read_text(Path(args.release_notes))
    elif not args.skip_gh:
        body = release_body_from_gh(args.tag, args.repo) or ""

    if not has_real_content(body):
        fail("release description is missing, too short, or placeholder-only")
    ok("release description is present")


def check_version(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    changelog = read_text(target / "CHANGELOG.md")
    current_tag = args.current_tag or latest_changelog_tag(changelog)
    if not current_tag:
        fail("could not infer current version from CHANGELOG.md; pass --current-tag vMAJOR.MINOR.PATCH")
    current_key = version_key(current_tag)

    latest = latest_release_from_gh(args.repo)
    latest_tag = latest["tagName"]
    latest_key = version_key(latest_tag)
    if latest_key > current_key:
        fail(f"newer Skill release available: {latest_tag} > local {current_tag}. Update before running.")
    if latest_key < current_key:
        ok(f"local changelog version {current_tag} is ahead of latest GitHub release {latest_tag}")
        return
    ok(f"local Skill version matches latest GitHub release: {current_tag}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checks for an EvoZeus-wrapper Skill repo.")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check local git/gh dependencies and source repo access.")
    doctor.add_argument("--target", default=".", help="Target wrapped Skill repo path.")
    doctor.add_argument("--repo", help="GitHub repo in OWNER/REPO format. Defaults to origin remote or discovered candidate.")
    doctor.add_argument("--allow-missing-repo", action="store_true", help="Allow --repo to be absent on GitHub when bootstrapping a new repo.")

    structure = sub.add_parser("structure", help="Check required wrapper files.")
    structure.add_argument("--target", default=".", help="Target wrapped Skill repo path.")

    issue = sub.add_parser("issue", help="Check a Skill feedback issue body.")
    issue.add_argument("--target", default=".", help="Target wrapped Skill repo path.")
    issue.add_argument("--file", required=True, help="Markdown file containing the issue body.")

    pr = sub.add_parser("pr", help="Check Skill evolution PR readiness.")
    pr.add_argument("--target", default=".", help="Target wrapped Skill repo path.")
    pr.add_argument("--design-doc", help="Path to the design doc for this PR.")
    pr.add_argument("--pr-body", help="Optional PR body markdown file.")

    release = sub.add_parser("release", help="Check release readiness.")
    release.add_argument("--target", default=".", help="Target wrapped Skill repo path.")
    release.add_argument("--tag", required=True, help="Release tag, such as v0.1.0.")
    release.add_argument("--release-notes", help="Markdown file containing release notes.")
    release.add_argument("--repo", help="GitHub repo in OWNER/REPO format for gh release lookup.")
    release.add_argument("--skip-gh", action="store_true", help="Do not call gh release view when release notes are omitted.")

    version = sub.add_parser("version", help="Check whether GitHub has a newer Skill release.")
    version.add_argument("--target", default=".", help="Target wrapped Skill repo path.")
    version.add_argument("--repo", required=True, help="GitHub repo in OWNER/REPO format.")
    version.add_argument("--current-tag", help="Current local Skill version. Defaults to latest release tag in CHANGELOG.md.")

    args = parser.parse_args()
    if args.command == "doctor":
        check_doctor(args)
    elif args.command == "structure":
        check_structure(args)
    elif args.command == "issue":
        check_issue(args)
    elif args.command == "pr":
        check_pr(args)
    elif args.command == "release":
        check_release(args)
    elif args.command == "version":
        check_version(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
