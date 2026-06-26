#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
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

PLACEHOLDER_PATTERNS = [
    r"\{\{[A-Z_]+\}\}",
    r"<short title>",
    r"<path>",
    r"<design-doc>",
    r"\bTBD\b",
    r"待填写",
]


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


def check_terms(text: str, term_groups: list[list[str]], label: str) -> None:
    missing = []
    for group in term_groups:
        if not has_any(text, group):
            missing.append("/".join(group))
    if missing:
        fail(f"{label} missing required concepts: {', '.join(missing)}")


def check_structure(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    missing = [path for path in REQUIRED_FILES if not (target / path).exists()]
    if missing:
        fail("missing required wrapper files:\n" + "\n".join(f"- {path}" for path in missing))
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


def release_body_from_gh(tag: str, repo: str | None) -> str | None:
    cmd = ["gh", "release", "view", tag, "--json", "body", "-q", ".body"]
    if repo:
        cmd.extend(["--repo", repo])
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout


def check_release(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checks for an EvoZeus-wrapper Skill repo.")
    parser.add_argument("--target", default=".", help="Target wrapped Skill repo path.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("structure", help="Check required wrapper files.")

    issue = sub.add_parser("issue", help="Check a Skill feedback issue body.")
    issue.add_argument("--file", required=True, help="Markdown file containing the issue body.")

    pr = sub.add_parser("pr", help="Check Skill evolution PR readiness.")
    pr.add_argument("--design-doc", help="Path to the design doc for this PR.")
    pr.add_argument("--pr-body", help="Optional PR body markdown file.")

    release = sub.add_parser("release", help="Check release readiness.")
    release.add_argument("--tag", required=True, help="Release tag, such as v0.1.0.")
    release.add_argument("--release-notes", help="Markdown file containing release notes.")
    release.add_argument("--repo", help="GitHub repo in OWNER/REPO format for gh release lookup.")
    release.add_argument("--skip-gh", action="store_true", help="Do not call gh release view when release notes are omitted.")

    args = parser.parse_args()
    if args.command == "structure":
        check_structure(args)
    elif args.command == "issue":
        check_issue(args)
    elif args.command == "pr":
        check_pr(args)
    elif args.command == "release":
        check_release(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
