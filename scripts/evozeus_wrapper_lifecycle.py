#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


STAGE_LABELS = {
    "environment": "[1/5] Environment Diagnosis",
    "target_skill": "[2/5] Target Skill Diagnosis",
    "transform": "[3/5] Target Skill Transform",
    "publish": "[4/5] Publish & Reinstall",
    "loop": "[5/5] Continuous Evolution Loop",
}


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
