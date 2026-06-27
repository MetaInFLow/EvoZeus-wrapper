#!/usr/bin/env python3
from __future__ import annotations

import re
import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any


STAGE_LABELS = {
    "environment": "[1/5] Environment Diagnosis",
    "target_skill": "[2/5] Target Skill Diagnosis",
    "transform": "[3/5] Target Skill Transform",
    "publish": "[4/5] Publish & Reinstall",
    "loop": "[5/5] Continuous Evolution Loop",
}

REQUIRED_WRAPPER_FILES = [
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

WRAPPER_MANAGED_FILES = [
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

WRAPPER_REPO = "MetaInFLow/EvoZeus-wrapper"


def stage_label(stage: str) -> str:
    try:
        return STAGE_LABELS[stage]
    except KeyError:
        raise ValueError(f"unknown lifecycle stage: {stage}") from None


def path_kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "missing"


def repo_from_remote(remote_url: str) -> str | None:
    remote_url = remote_url.strip()
    match = re.match(r"^https://github\.com/([^/]+/[^/.]+)(?:\.git)?$", remote_url)
    if match:
        return match.group(1)
    match = re.match(r"^git@github\.com:([^/]+/[^/.]+)(?:\.git)?$", remote_url)
    if match:
        return match.group(1)
    return None


def skill_name_from_skill_md(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(args: list[str], cwd: Path | None = None) -> dict[str, Any]:
    try:
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    except FileNotFoundError:
        return {"returncode": 127, "stdout": "", "stderr": "command not found"}
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def command_status(args: list[str], runner=run_command) -> str:
    result = runner(args)
    return "ok" if result["returncode"] == 0 else "failed"


def diagnose_environment(home: Path = Path.home(), runner=run_command) -> dict[str, Any]:
    home = home.expanduser().resolve()
    evozeus_home = home / ".evozeus"
    runtime_dir = evozeus_home / "runtime"
    projects_dir = evozeus_home / ".projects"

    git_status = command_status(["git", "--version"], runner)
    gh_status = command_status(["gh", "--version"], runner)
    gh_auth_status = command_status(["gh", "auth", "status"], runner) if gh_status == "ok" else "failed"
    mother_repo_access = "unknown"
    if gh_status == "ok" and gh_auth_status == "ok":
        mother_view = runner(["gh", "repo", "view", "MetaInFLow/EvoZeus", "--json", "nameWithOwner,url,visibility"])
        mother_repo_access = "ok" if mother_view["returncode"] == 0 else "failed"

    return {
        "stage": "environment_diagnosis",
        "evozeus_home": {
            "exists": evozeus_home.exists(),
            "path": str(evozeus_home),
            "runtime_exists": runtime_dir.exists(),
            "projects_exists": projects_dir.exists(),
        },
        "mother_repo": {
            "remote": "MetaInFLow/EvoZeus",
            "candidates": [],
            "canonical_path": None,
            "needs_user_choice": False,
            "remote_access": mother_repo_access,
        },
        "dependencies": {
            "git": git_status,
            "gh": gh_status,
            "gh_auth": gh_auth_status,
        },
    }


def repo_projects_pointer(home: Path, repo: str | None) -> Path | None:
    if not repo or "/" not in repo:
        return None
    owner, name = repo.split("/", 1)
    return home / ".evozeus" / ".projects" / owner / name


def describe_install_path(path: Path, target: Path) -> dict[str, Any]:
    target_skill_hash = file_sha256(target / "SKILL.md")
    install_skill_hash = file_sha256(path / "SKILL.md")
    resolved = None
    if path.exists() or path.is_symlink():
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = None
    return {
        "path": str(path),
        "kind": path_kind(path),
        "resolved_path": resolved,
        "has_skill_md": (path / "SKILL.md").exists(),
        "skill_md_hash": install_skill_hash,
        "matches_target_skill_md": bool(target_skill_hash and install_skill_hash and target_skill_hash == install_skill_hash),
    }


def diagnose_harness_state(target: Path) -> dict[str, Any]:
    present = [rel for rel in REQUIRED_WRAPPER_FILES if (target / rel).exists()]
    missing = [rel for rel in REQUIRED_WRAPPER_FILES if not (target / rel).exists()]
    manifest = load_wrapper_manifest(target)
    if not present:
        state = "missing"
    elif not missing:
        state = "complete"
    else:
        state = "partial"
    return {
        "state": state,
        "present_files": present,
        "missing_files": missing,
        "wrapper_version": manifest.get("wrapper_version") if manifest else None,
    }


def diagnose_repo_state(target: Path, repo: str | None, home: Path, workspace_roots: list[Path], runner=run_command) -> dict[str, Any]:
    exists_on_github: bool | None = None
    if repo:
        view = runner(["gh", "repo", "view", repo, "--json", "nameWithOwner,url,visibility"])
        exists_on_github = view["returncode"] == 0

    git_root = None
    git_root_result = runner(["git", "-C", str(target), "rev-parse", "--show-toplevel"])
    if git_root_result["returncode"] == 0 and git_root_result.get("stdout"):
        git_root = git_root_result["stdout"].strip()

    pointer = repo_projects_pointer(home, repo)
    candidates = []
    if git_root:
        candidates.append(git_root)
    if pointer and (pointer.exists() or pointer.is_symlink()):
        candidates.append(str(pointer))
    for root in workspace_roots:
        if root.exists():
            candidates.append(str(root.expanduser().resolve()))

    unique_candidates = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)

    return {
        "name": repo,
        "exists_on_github": exists_on_github,
        "candidates": unique_candidates,
        "canonical_path": unique_candidates[0] if len(unique_candidates) == 1 else None,
        "needs_user_choice": len(unique_candidates) > 1,
        "projects_pointer": str(pointer) if pointer else None,
    }


def diagnose_skill(
    target: Path,
    repo: str | None,
    skill_name: str | None,
    home: Path = Path.home(),
    workspace_roots: list[Path] | None = None,
    runner=run_command,
) -> dict[str, Any]:
    home = home.expanduser().resolve()
    target = target.expanduser().resolve()
    skill_md = target / "SKILL.md"
    inferred_name = skill_name or skill_name_from_skill_md(skill_md) or target.name

    install_paths = [
        home / ".codex" / "skills" / inferred_name,
        home / ".agents" / "skills" / inferred_name,
    ]
    installs = [
        describe_install_path(path, target)
        for path in install_paths
        if path.exists() or path.is_symlink()
    ]

    return {
        "stage": "target_skill_diagnosis",
        "skill": {
            "name": inferred_name,
            "target_path": str(target),
            "has_skill_md": skill_md.exists(),
        },
        "repo": diagnose_repo_state(target, repo, home, workspace_roots or [], runner),
        "installs": installs,
        "harness": diagnose_harness_state(target),
        "publication": {
            "visibility": None,
            "sensitive_risk": "unknown",
        },
    }


def wrapper_manifest_path(target: Path) -> Path:
    return target / ".evozeus" / "wrapper.json"


def load_wrapper_manifest(target: Path) -> dict[str, Any] | None:
    path = wrapper_manifest_path(target)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_wrapper_manifest(
    repo: str,
    wrapper_version: str,
    managed_files: list[str],
    install_links: list[str],
) -> dict[str, Any]:
    return {
        "wrapper_repo": WRAPPER_REPO,
        "wrapper_version": wrapper_version,
        "applied_at": date.today().isoformat(),
        "canonical_repo": repo,
        "managed_files": managed_files,
        "install_links": install_links,
    }


def write_wrapper_manifest(target: Path, manifest: dict[str, Any], force: bool = False) -> str:
    path = wrapper_manifest_path(target)
    if path.exists() and not force:
        return f"skip existing {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"write {path}"


def plan_transform_action(harness_state: str, repo_exists: bool | None) -> str:
    if harness_state == "complete":
        return "verify"
    if harness_state == "partial":
        return "repair"
    if harness_state != "missing":
        raise ValueError(f"unknown harness state: {harness_state}")
    if repo_exists is None:
        return "needs_repo_check"
    return "adopt" if repo_exists else "bootstrap"


def classify_install_action(install_path: Path, canonical_path: Path) -> dict[str, Any]:
    canonical_path = canonical_path.expanduser().resolve()
    kind = path_kind(install_path)
    resolved_path = None
    if install_path.exists() or install_path.is_symlink():
        try:
            resolved_path = str(install_path.resolve())
        except OSError:
            resolved_path = None

    if kind == "missing":
        action = "create_symlink"
        reason = "install path is missing"
    elif kind == "symlink" and resolved_path == str(canonical_path):
        action = "already_linked"
        reason = "install path already points to canonical repo"
    elif kind == "symlink":
        action = "relink_symlink"
        reason = "install symlink points somewhere else"
    elif kind == "directory":
        canonical_hash = file_sha256(canonical_path / "SKILL.md")
        install_hash = file_sha256(install_path / "SKILL.md")
        if canonical_hash and install_hash and canonical_hash == install_hash:
            action = "archive_then_symlink"
            reason = "real directory install has identical SKILL.md"
        else:
            action = "needs_user_confirmation"
            reason = "real directory install differs from canonical repo"
    else:
        action = "needs_user_confirmation"
        reason = "install path is not a directory or symlink"

    return {
        "path": str(install_path),
        "kind": kind,
        "resolved_path": resolved_path,
        "canonical_path": str(canonical_path),
        "action": action,
        "reason": reason,
    }


def plan_reinstall(skill_name: str, canonical_path: Path, home: Path, targets: list[str]) -> dict[str, Any]:
    home = home.expanduser().resolve()
    canonical_path = canonical_path.expanduser().resolve()
    runtime_roots = {
        "codex": home / ".codex" / "skills",
        "agents": home / ".agents" / "skills",
    }
    selected = ["codex", "agents"] if "all" in targets else targets
    actions = []
    for target_name in selected:
        root = runtime_roots[target_name] if target_name in runtime_roots else Path(target_name).expanduser()
        install_path = root / skill_name if target_name in runtime_roots else root
        actions.append(classify_install_action(install_path, canonical_path))
    return {
        "stage": "publish_reinstall",
        "skill_name": skill_name,
        "canonical_path": str(canonical_path),
        "actions": actions,
    }


def version_key(tag: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        raise ValueError(f"version tag must use vMAJOR.MINOR.PATCH format: {tag}")
    return tuple(int(part) for part in match.groups())


def classify_pr_permission(write: bool, fork: bool) -> str:
    if write:
        return "direct_pr"
    if fork:
        return "fork_pr"
    return "local_patch"


def classify_wrapper_upgrade(current: str, latest: str, managed_dirty: bool) -> str:
    current_key = version_key(current)
    latest_key = version_key(latest)
    if latest_key == current_key:
        return "up_to_date"
    if latest_key < current_key:
        return "local_ahead"
    if latest_key[0] > current_key[0]:
        return "requires_confirmation"
    if managed_dirty:
        return "needs_merge_review"
    return "auto_pr"
