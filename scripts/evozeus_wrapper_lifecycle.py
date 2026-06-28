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
    "docs/wrapper-migrations/README.md",
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
    "docs/wrapper-migrations/README.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/skill-feedback.yml",
    ".github/pull_request_template.md",
    ".github/workflows/evozeus-wrapper-preflight.yml",
    "scripts/evozeus_wrapper_preflight.py",
]

WRAPPER_REPO = "MetaInFLow/EvoZeus-wrapper"
INITIAL_SKILL_VERSION = "v0.1.0"
VERSION_HEADER_RE = re.compile(r"^##\s+\[?(v\d+\.\d+\.\d+)\]?\b", re.MULTILINE)
SKILL_STATUS_SECTION = "SKILL.md EvoZeus-wrapper status check section (front matter prelude)"
SKILL_WRAPPER_SECTION = "SKILL.md EvoZeus-wrapper section or migration note (append only)"
WRAPPER_MIGRATION_README = "docs/wrapper-migrations/README.md"
CONTROL_SKILL_NAME_TOKENS = (
    "bootstrap",
    "control",
    "controller",
    "entry",
    "index",
    "init",
    "loader",
    "loading",
    "orchestrator",
    "router",
    "routing",
    "runtime",
    "session",
    "start",
    "startup",
)
CONTROL_SKILL_TEXT_TERMS = (
    "available skills",
    "bootstrap",
    "control",
    "hook",
    "invoke",
    "load skills",
    "loaded by",
    "plugin",
    "route",
    "routing",
    "session start",
    "session-start",
    "skill usage",
    "startup",
    "启动",
    "入口",
    "加载",
    "路由",
    "控制",
)


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


def latest_changelog_tag_from_text(changelog: str) -> str | None:
    match = VERSION_HEADER_RE.search(changelog)
    return match.group(1) if match else None


def latest_changelog_tag(target: Path) -> str | None:
    changelog = target / "CHANGELOG.md"
    if not changelog.exists():
        return None
    return latest_changelog_tag_from_text(changelog.read_text(encoding="utf-8"))


def read_latest_release(repo: str | None, runner=run_command) -> dict[str, Any] | None:
    if not repo:
        return None
    result = runner(["gh", "release", "view", "--repo", repo, "--json", "tagName,url,publishedAt"])
    if result["returncode"] != 0:
        return {
            "exists": False,
            "tag": None,
            "url": None,
            "published_at": None,
            "error": (result.get("stderr") or result.get("stdout") or "").strip() or "latest release not found",
        }
    try:
        data = json.loads(result.get("stdout") or "{}")
    except json.JSONDecodeError:
        return {
            "exists": False,
            "tag": None,
            "url": None,
            "published_at": None,
            "error": "could not parse latest release response",
        }
    tag = data.get("tagName")
    if not tag:
        return {
            "exists": False,
            "tag": None,
            "url": data.get("url"),
            "published_at": data.get("publishedAt"),
            "error": "latest release response has no tagName",
        }
    return {
        "exists": True,
        "tag": tag,
        "url": data.get("url"),
        "published_at": data.get("publishedAt"),
        "error": None,
    }


def diagnose_skill_version(
    target: Path,
    repo_exists: bool | None,
    latest_release: dict[str, Any] | None,
) -> dict[str, Any]:
    changelog_tag = latest_changelog_tag(target)

    if repo_exists is False:
        return {
            "status": "new_repo_initial_release",
            "current_tag": INITIAL_SKILL_VERSION,
            "changelog_tag": changelog_tag,
            "latest_release_tag": None,
            "rule": "new bootstrap repos use v0.1.0 as the first Skill release",
            "requires_owner_choice": False,
        }

    if repo_exists is None:
        return {
            "status": "repo_state_unknown",
            "current_tag": changelog_tag,
            "changelog_tag": changelog_tag,
            "latest_release_tag": None,
            "rule": "verify GitHub repo state before choosing the Skill version",
            "requires_owner_choice": True,
        }

    latest_tag = latest_release.get("tag") if latest_release and latest_release.get("exists") else None
    if latest_tag:
        status = "adopt_existing_release"
        requires_owner_choice = False
        current_tag = latest_tag
        rule = "existing repos keep GitHub latest release as the Skill version"
        if changelog_tag:
            try:
                latest_key = version_key(latest_tag)
                changelog_key = version_key(changelog_tag)
            except ValueError:
                return {
                    "status": "invalid_version_tag",
                    "current_tag": changelog_tag or latest_tag,
                    "changelog_tag": changelog_tag,
                    "latest_release_tag": latest_tag,
                    "rule": "Skill releases must use vMAJOR.MINOR.PATCH",
                    "requires_owner_choice": True,
                }
            if changelog_key == latest_key:
                status = "local_matches_latest_release"
                current_tag = changelog_tag
            elif changelog_key < latest_key:
                status = "local_changelog_behind_release"
                current_tag = changelog_tag
            else:
                status = "local_changelog_ahead_of_release"
                current_tag = changelog_tag
        return {
            "status": status,
            "current_tag": current_tag,
            "changelog_tag": changelog_tag,
            "latest_release_tag": latest_tag,
            "rule": rule,
            "requires_owner_choice": False,
        }

    if changelog_tag:
        return {
            "status": "github_release_missing_create_from_changelog",
            "current_tag": changelog_tag,
            "changelog_tag": changelog_tag,
            "latest_release_tag": None,
            "rule": "existing repos without GitHub releases should create a release for the latest changelog tag before runtime use",
            "requires_owner_choice": False,
        }

    return {
        "status": "missing_version_requires_owner_choice",
        "current_tag": None,
        "changelog_tag": None,
        "latest_release_tag": None,
        "rule": "existing repos must not be reset to v0.1.0; choose or recover the current Skill version first",
        "requires_owner_choice": True,
    }


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
        "next_action": "continue_to_target_repo_diagnosis" if evozeus_home.exists() else "install_evozeus",
        "evozeus_home": {
            "exists": evozeus_home.exists(),
            "path": str(evozeus_home),
            "runtime_exists": runtime_dir.exists(),
            "projects_exists": projects_dir.exists(),
            "required_action": "none" if evozeus_home.exists() else "install_evozeus",
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


def resolve_path(path: Path) -> str | None:
    if not (path.exists() or path.is_symlink()):
        return None
    try:
        return str(path.resolve())
    except OSError:
        return None


def target_canonical_path(target: Path, runner=run_command) -> str:
    git_root_result = runner(["git", "-C", str(target), "rev-parse", "--show-toplevel"])
    if git_root_result["returncode"] == 0 and git_root_result.get("stdout"):
        return str(Path(git_root_result["stdout"].strip()).expanduser().resolve())
    return str(target.expanduser().resolve())


def git_origin_repo(path: Path, runner=run_command) -> str | None:
    remote_result = runner(["git", "-C", str(path), "remote", "get-url", "origin"])
    if remote_result["returncode"] != 0:
        return None
    return repo_from_remote(remote_result.get("stdout", ""))


def describe_install_path(path: Path, target: Path) -> dict[str, Any]:
    target_skill_hash = file_sha256(target / "SKILL.md")
    install_skill_hash = file_sha256(path / "SKILL.md")
    resolved = resolve_path(path)
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
    latest_release: dict[str, Any] | None = None
    repo_info: dict[str, Any] = {}
    access: dict[str, Any] = {
        "checked": bool(repo),
        "status": "not_requested" if not repo else "unknown",
        "viewer_permission": None,
        "can_read": False,
        "can_write": False,
        "can_admin": False,
    }
    if repo:
        view = runner(
            [
                "gh",
                "repo",
                "view",
                repo,
                "--json",
                "nameWithOwner,url,visibility,viewerPermission,defaultBranchRef",
            ]
        )
        exists_on_github = view["returncode"] == 0
        if exists_on_github:
            repo_info = parse_repo_view(view.get("stdout") or "")
            permission = repo_info.get("viewerPermission")
            access = {
                "checked": True,
                "status": "ok",
                "viewer_permission": permission,
                "can_read": True,
                "can_write": permission in {"ADMIN", "MAINTAIN", "WRITE"},
                "can_admin": permission == "ADMIN",
            }
            latest_release = read_latest_release(repo, runner)
        else:
            access = {
                "checked": True,
                "status": "failed",
                "viewer_permission": None,
                "can_read": False,
                "can_write": False,
                "can_admin": False,
                "error": (view.get("stderr") or view.get("stdout") or "").strip() or "repo access check failed",
            }

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
        "info": repo_info,
        "visibility": repo_info.get("visibility"),
        "default_branch": (repo_info.get("defaultBranchRef") or {}).get("name"),
        "access": access,
        "latest_release": latest_release,
        "candidates": unique_candidates,
        "canonical_path": unique_candidates[0] if len(unique_candidates) == 1 else None,
        "needs_user_choice": len(unique_candidates) > 1,
        "projects_pointer": str(pointer) if pointer else None,
    }


def parse_repo_view(stdout: str) -> dict[str, Any]:
    if not stdout.strip():
        return {}
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def skill_entries(target: Path) -> list[dict[str, Any]]:
    skills_dir = target / "skills"
    if not skills_dir.exists():
        return []
    entries = []
    for path in sorted(skills_dir.glob("*/SKILL.md")):
        entries.append(
            {
                "path": str(path.relative_to(target)),
                "directory": str(path.parent.relative_to(target)),
                "name": skill_name_from_skill_md(path) or path.parent.name,
            }
        )
    return entries


def existing_relative_files(target: Path, paths: list[str]) -> list[str]:
    return [path for path in paths if (target / path).is_file()]


def plugin_manifest_files(target: Path) -> list[str]:
    candidates = [
        ".codex-plugin/plugin.json",
        ".claude-plugin/plugin.json",
        ".cursor-plugin/plugin.json",
        ".kimi-plugin/plugin.json",
        ".opencode/INSTALL.md",
        "gemini-extension.json",
        "package.json",
    ]
    return existing_relative_files(target, candidates)


def hook_files(target: Path) -> list[str]:
    hooks_dir = target / "hooks"
    if not hooks_dir.is_dir():
        return []
    return [
        str(path.relative_to(target))
        for path in sorted(hooks_dir.iterdir())
        if path.is_file()
    ]


def normalize_match_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def read_text_if_small(path: Path, limit: int = 200_000) -> str:
    if not path.is_file():
        return ""
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def controller_corpus(target: Path, controllers: list[str]) -> str:
    parts: list[str] = []
    for controller in controllers:
        path = target / controller
        parts.append(controller)
        parts.append(read_text_if_small(path, limit=80_000))
    return normalize_match_text("\n".join(parts))


def skill_entry_identifiers(entry: dict[str, Any]) -> list[str]:
    values = [
        entry.get("path", ""),
        entry.get("directory", ""),
        Path(entry.get("directory", "")).name,
        entry.get("name", ""),
    ]
    identifiers = []
    for value in values:
        item = str(value).strip().strip('"').strip("'").lower()
        if len(item) >= 3 and item not in identifiers:
            identifiers.append(item)
    return identifiers


def hook_loaded_skill_candidate_facts(
    target: Path,
    skill_inventory: list[dict[str, Any]],
    hooks: list[str],
    plugins: list[str],
) -> list[dict[str, Any]]:
    controllers = hooks + plugins
    if not controllers:
        return []

    corpus = controller_corpus(target, controllers)
    candidates: list[dict[str, Any]] = []
    for entry in skill_inventory:
        skill_path = entry["path"]
        full_path = target / skill_path
        skill_text = normalize_match_text(read_text_if_small(full_path, limit=80_000))
        name_basis = normalize_match_text(
            f"{entry.get('name', '')} {entry.get('directory', '')} {entry.get('path', '')}"
        )
        referenced_identifiers = [
            identifier
            for identifier in skill_entry_identifiers(entry)
            if identifier in corpus
        ]
        name_hints = [token for token in CONTROL_SKILL_NAME_TOKENS if token in name_basis]
        text_hints = [term for term in CONTROL_SKILL_TEXT_TERMS if term in skill_text]
        is_only_skill = len(skill_inventory) == 1

        if not (referenced_identifiers or name_hints or text_hints or is_only_skill):
            continue
        candidates.append(
            {
                "path": skill_path,
                "role": "hook_loaded_skill_instruction",
                "reason": "script-surfaced hook/plugin candidate; final placement requires diagnosis Skill review",
                "evidence": {
                    "controller_referenced_identifiers": referenced_identifiers,
                    "name_or_path_hints": name_hints,
                    "instruction_text_hints": text_hints,
                    "only_skill_in_bundle": is_only_skill,
                },
                "controlled_by": controllers,
                "has_wrapper_status_check": surface_has_status_check(full_path),
            }
        )

    return sorted(candidates, key=lambda item: item["path"])


def surface_has_status_check(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + len("\n---\n") :]
    stripped = text.lstrip()
    if stripped.startswith("## EvoZeus-wrapper 状态检查"):
        return True
    lines = stripped.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).lstrip().startswith("## EvoZeus-wrapper 状态检查")
    return False


def collect_evolution_surface_facts(target: Path, skill_inventory: list[dict[str, Any]]) -> dict[str, Any]:
    plugins = plugin_manifest_files(target)
    hooks = hook_files(target)
    candidates: list[dict[str, Any]] = []

    def add_candidate(path: str, role: str, reason: str, controlled_by: list[str] | None = None) -> None:
        full_path = target / path
        if not full_path.is_file():
            return
        candidates.append(
            {
                "path": path,
                "role": role,
                "reason": reason,
                "controlled_by": controlled_by or [],
                "has_wrapper_status_check": surface_has_status_check(full_path),
            }
        )

    add_candidate(
        "SKILL.md",
        "root_skill_instruction",
        "root SKILL.md is the direct Skill instruction surface",
    )
    add_candidate(
        "AGENTS.md",
        "root_agent_instruction",
        "root AGENTS.md controls repository-level agent behavior",
    )
    candidates.extend(hook_loaded_skill_candidate_facts(target, skill_inventory, hooks, plugins))

    if not candidates and len(skill_inventory) == 1:
        add_candidate(
            skill_inventory[0]["path"],
            "only_skill_instruction",
            "single discovered skills/*/SKILL.md is the only available Skill instruction surface",
        )

    return {
        "status": "needs_skill_diagnosis" if candidates else "needs_owner_choice",
        "selected": None,
        "candidates": candidates,
        "instruction_placement": None,
        "controller_files": hooks + plugins,
        "diagnosis_skill": "skills/evolution-surface-diagnosis/SKILL.md",
        "selection_rule": (
            "scripts collect facts and candidate instruction surfaces only; "
            "the evolution-surface diagnosis Skill must browse the whole repo and decide the controlling surface"
        ),
        "script_fact_boundary": (
            "do not treat candidates as final placement; use them as evidence for the diagnosis Skill"
        ),
    }


def assess_component_gaps(target: Path, evolution_surface: dict[str, Any]) -> dict[str, Any]:
    required = REQUIRED_WRAPPER_FILES + [".evozeus/wrapper.json"]
    missing_files = [rel for rel in required if not (target / rel).exists()]
    present_files = [rel for rel in required if (target / rel).exists()]
    missing_concepts = []
    selected = evolution_surface.get("selected")
    if not selected:
        missing_concepts.append("evolution surface diagnosis result")
    elif not selected.get("has_wrapper_status_check"):
        missing_concepts.append(f"{selected['path']} EvoZeus-wrapper status check")
    if not (target / "CHANGELOG.md").exists():
        missing_concepts.append("Skill or kit release changelog")
    if not (target / ".evozeus" / "wrapper.json").exists():
        missing_concepts.append("wrapper manifest")

    return {
        "present_files": present_files,
        "missing_files": missing_files,
        "missing_concepts": missing_concepts,
    }


def detect_target_architecture(target: Path) -> dict[str, Any]:
    target = target.expanduser().resolve()
    has_root_skill = (target / "SKILL.md").exists()
    has_agents = (target / "AGENTS.md").exists()
    entries = skill_entries(target)
    plugins = plugin_manifest_files(target)
    hooks = hook_files(target)
    dir_names = [
        "runtime",
        "agents",
        "skills",
        "automation",
        "cases",
        "knowledge",
        "templates",
        "state",
        "config",
    ]
    present_dirs = [name for name in dir_names if (target / name).is_dir()]
    file_names = [
        "AGENTS.md",
        "SKILL.md",
        "ARCHITECTURE.md",
        "MAINTENANCE.md",
        "README.md",
        "ONLINE-DOCS.md",
        "CLAUDE.md",
        "OPENCLAW.md",
        "HERMES.md",
    ]
    present_files = [name for name in file_names if (target / name).is_file()]
    evolution_surface = collect_evolution_surface_facts(target, entries)

    if hooks and plugins and entries:
        target_kind = "hooked_skill_bundle"
    elif has_root_skill and not entries:
        target_kind = "single_skill"
    elif has_agents and entries and {"runtime", "agents", "automation"}.issubset(set(present_dirs)):
        target_kind = "runtime_skill_bundle"
    elif entries:
        target_kind = "skill_bundle"
    elif has_agents:
        target_kind = "agents_runtime"
    else:
        target_kind = "unknown"

    if target_kind == "hooked_skill_bundle":
        architecture_style = "plugin_hook_controlled_skill_system"
    elif target_kind == "runtime_skill_bundle":
        architecture_style = "managed_runtime_skill_bundle"
    elif target_kind == "skill_bundle":
        architecture_style = "multi_skill_bundle"
    elif target_kind == "single_skill":
        architecture_style = "single_skill_repo"
    elif target_kind == "agents_runtime":
        architecture_style = "agent_runtime"
    else:
        architecture_style = "unknown"

    root_entry = "SKILL.md" if has_root_skill else "AGENTS.md" if has_agents else None
    verification_candidates = [
        str(path.relative_to(target))
        for path in sorted((target / "automation").glob("*.py"))
    ] if (target / "automation").is_dir() else []
    component_gaps = assess_component_gaps(target, evolution_surface)

    return {
        "target_kind": target_kind,
        "architecture_style": architecture_style,
        "root_entry": root_entry,
        "evolution_surface": evolution_surface,
        "component_gaps": component_gaps,
        "root_files": present_files,
        "top_level_dirs": present_dirs,
        "plugin_manifests": plugins,
        "hook_files": hooks,
        "skill_inventory": {
            "count": len(entries),
            "entries": entries,
        },
        "verification_candidates": verification_candidates,
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
    architecture = detect_target_architecture(target)
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

    manifest = load_wrapper_manifest(target)
    manifest_repo = manifest.get("canonical_repo") if manifest else None
    effective_repo = repo or manifest_repo
    repo_state = diagnose_repo_state(target, effective_repo, home, workspace_roots or [], runner)
    version = diagnose_skill_version(target, repo_state["exists_on_github"], repo_state["latest_release"])
    harness = diagnose_harness_state(target)
    source_contract = diagnose_source_contract(
        target=target,
        requested_repo=repo,
        skill_name=inferred_name,
        home=home,
        installs=installs,
        runner=runner,
    )
    return {
        "stage": "target_skill_diagnosis",
        "skill": {
            "name": inferred_name,
            "target_path": str(target),
            "has_skill_md": skill_md.exists(),
            "root_entry": architecture["root_entry"],
            "target_kind": architecture["target_kind"],
            "architecture_style": architecture["architecture_style"],
            "evolution_surface": architecture["evolution_surface"],
            "component_gaps": architecture["component_gaps"],
            "root_files": architecture["root_files"],
            "top_level_dirs": architecture["top_level_dirs"],
            "plugin_manifests": architecture["plugin_manifests"],
            "hook_files": architecture["hook_files"],
            "skill_inventory": architecture["skill_inventory"],
            "verification_candidates": architecture["verification_candidates"],
        },
        "repo": repo_state,
        "version": version,
        "installs": installs,
        "harness": harness,
        "source_contract": source_contract,
        "publication": {
            "visibility": repo_state.get("visibility"),
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


def diagnose_source_contract(
    target: Path,
    requested_repo: str | None,
    skill_name: str,
    home: Path,
    installs: list[dict[str, Any]],
    runner=run_command,
) -> dict[str, Any]:
    manifest = load_wrapper_manifest(target)
    discovery_order = [
        ".evozeus/wrapper.json",
        "~/.evozeus/.projects/OWNER/REPO",
        "canonical repo git origin / GitHub repo",
        "~/.codex/skills/<skill-name> and ~/.agents/skills/<skill-name>",
        "current user/org/public GitHub search fallback",
    ]
    if not manifest:
        return {
            "managed": False,
            "status": "unmanaged",
            "discovery_order": discovery_order,
            "errors": [],
            "warnings": [],
            "canonical_repo": requested_repo,
            "canonical_path": target_canonical_path(target, runner),
            "projects_pointer": None,
            "runtime_installs": installs,
        }

    errors: list[str] = []
    warnings: list[str] = []
    manifest_repo = manifest.get("canonical_repo")
    if not manifest_repo:
        errors.append(".evozeus/wrapper.json is missing canonical_repo")
    if requested_repo and manifest_repo and requested_repo != manifest_repo:
        errors.append(f"--repo {requested_repo} does not match wrapper canonical_repo {manifest_repo}")

    canonical_repo = manifest_repo or requested_repo
    canonical_path = target_canonical_path(target, runner)
    pointer = repo_projects_pointer(home, canonical_repo)
    pointer_info = {
        "path": str(pointer) if pointer else None,
        "kind": path_kind(pointer) if pointer else "missing",
        "resolved_path": resolve_path(pointer) if pointer else None,
    }

    if not pointer:
        errors.append("cannot derive ~/.evozeus/.projects pointer because canonical_repo is missing")
    elif not pointer.exists() and not pointer.is_symlink():
        errors.append(f"project pointer is missing: {pointer}")
    elif not pointer.is_symlink():
        errors.append(f"project pointer must be a symlink to the canonical repo: {pointer}")
    elif pointer_info["resolved_path"] != canonical_path:
        errors.append(
            "project pointer does not resolve to canonical repo: "
            f"{pointer} -> {pointer_info['resolved_path']} expected {canonical_path}"
        )

    origin_repo = git_origin_repo(Path(canonical_path), runner)
    if origin_repo and canonical_repo and origin_repo != canonical_repo:
        errors.append(f"canonical repo origin {origin_repo} does not match wrapper canonical_repo {canonical_repo}")
    elif not origin_repo:
        warnings.append("canonical repo has no GitHub origin yet; this is only acceptable before first publish")

    runtime_reports = []
    for install in installs:
        report = dict(install)
        if install["kind"] == "symlink" and install.get("resolved_path") == canonical_path:
            report["source_contract"] = "runtime_pointer_ok"
        elif install["kind"] == "directory":
            report["source_contract"] = "runtime_real_directory_warning"
            warnings.append(
                f"runtime install is a real directory, not a canonical repo symlink: {install['path']}"
            )
        elif install["kind"] == "symlink":
            report["source_contract"] = "runtime_pointer_mismatch"
            errors.append(
                f"runtime symlink does not resolve to canonical repo: "
                f"{install['path']} -> {install.get('resolved_path')} expected {canonical_path}"
            )
        else:
            report["source_contract"] = "runtime_install_unusable"
            warnings.append(f"runtime install is not a symlink directory: {install['path']}")
        runtime_reports.append(report)

    status = "error" if errors else "warning" if warnings else "ok"
    return {
        "managed": True,
        "status": status,
        "discovery_order": discovery_order,
        "errors": errors,
        "warnings": warnings,
        "canonical_repo": canonical_repo,
        "canonical_path": canonical_path,
        "canonical_origin_repo": origin_repo,
        "projects_pointer": pointer_info,
        "runtime_installs": runtime_reports,
    }


def build_wrapper_manifest(
    repo: str,
    wrapper_version: str,
    managed_files: list[str],
    install_links: list[str],
    instruction_surface: str | None = None,
) -> dict[str, Any]:
    manifest = {
        "wrapper_repo": WRAPPER_REPO,
        "wrapper_version": wrapper_version,
        "applied_at": date.today().isoformat(),
        "canonical_repo": repo,
        "managed_files": managed_files,
        "install_links": install_links,
    }
    if instruction_surface:
        manifest["instruction_surface"] = instruction_surface
    return manifest


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


def wrapper_migration_doc_path(current: str | None, latest: str | None, today: date | None = None) -> str | None:
    if not latest:
        return None
    day = today or date.today()
    current_label = current or "unknown"
    return f"docs/wrapper-migrations/{day.isoformat()}-{current_label}-to-{latest}.md"


def plan_harness_upgrade(
    target: Path,
    latest_version: str | None = None,
    managed_dirty: bool = False,
    today: date | None = None,
    instruction_surface: str | None = None,
) -> dict[str, Any]:
    target = target.expanduser().resolve()
    manifest = load_wrapper_manifest(target)
    architecture = detect_target_architecture(target)
    manifest_surface = manifest.get("instruction_surface") if manifest else None
    instruction_surface = instruction_surface or manifest_surface or architecture["root_entry"] or "SKILL.md"
    if instruction_surface == "SKILL.md":
        root_status_section = SKILL_STATUS_SECTION
        root_wrapper_section = SKILL_WRAPPER_SECTION
    else:
        root_status_section = f"{instruction_surface} EvoZeus-wrapper status check section (instruction surface prelude)"
        root_wrapper_section = f"{instruction_surface} EvoZeus-wrapper section or migration note (append only)"
    current = manifest.get("wrapper_version") if manifest else None
    latest = latest_version or current

    if not current:
        status = "missing_manifest"
    elif not latest:
        status = "latest_unknown"
    else:
        status = classify_wrapper_upgrade(current, latest, managed_dirty)

    migration_doc = wrapper_migration_doc_path(current, latest, today)
    needs_upgrade = status in {"auto_pr", "needs_merge_review", "requires_confirmation"}
    needs_repair = status in {"missing_manifest", "latest_unknown"}

    planned_files: list[str] = []
    if needs_upgrade or needs_repair:
        planned_files.extend(
            [
                root_status_section,
                root_wrapper_section,
                ".evozeus/wrapper.json",
                WRAPPER_MIGRATION_README,
            ]
        )
        if migration_doc:
            planned_files.append(migration_doc)
        planned_files.extend(WRAPPER_MANAGED_FILES)

    deduped_planned_files = []
    for path in planned_files:
        if path not in deduped_planned_files:
            deduped_planned_files.append(path)

    if status == "up_to_date":
        recommended_action = "none"
    elif status == "local_ahead":
        recommended_action = "do_not_downgrade"
    elif status == "missing_manifest":
        recommended_action = "repair_or_adopt_before_upgrade"
    elif status == "latest_unknown":
        recommended_action = "provide_latest_wrapper_version"
    elif status == "needs_merge_review":
        recommended_action = "review_managed_file_diffs_before_upgrade"
    elif status == "requires_confirmation":
        recommended_action = "confirm_major_upgrade_and_migration_plan"
    else:
        recommended_action = "create_harness_upgrade_pr"

    canonical_repo = manifest.get("canonical_repo") if manifest else None
    validation = [
        "python3 scripts/evozeus_wrapper_preflight.py structure",
    ]
    if canonical_repo:
        validation.append(f"python3 scripts/evozeus_wrapper_preflight.py doctor --repo {canonical_repo}")
    if latest:
        validation.append(
            "python3 scripts/evozeus_wrapper.py harness upgrade-check "
            f"--target {target} --latest-version {latest} --json"
        )

    return {
        "stage": "harness_upgrade",
        "target": str(target),
        "writes": False,
        "current_version": current,
        "latest_version": latest,
        "managed_dirty": managed_dirty,
        "upgrade_status": status,
        "recommended_action": recommended_action,
        "requires_confirmation": status in {"missing_manifest", "latest_unknown", "needs_merge_review", "requires_confirmation"},
        "status_check_first": True,
        "append_only": True,
        "evolution_surface_policy": (
            f"add or refresh the wrapper-owned status prelude in {instruction_surface} before the main chain, then append "
            "the EvoZeus-wrapper section or a migration note; never rewrite target business rules"
        ),
        "skill_md_policy": (
            "single Skill targets use SKILL.md; AGENTS.md-root targets use AGENTS.md; hook-controlled bundles use the hook-loaded control Skill"
        ),
        "migration": {
            "from_wrapper_version": current,
            "to_wrapper_version": latest,
            "doc_path": migration_doc,
            "log_dir": "docs/wrapper-migrations",
            "records_wrapper_version_in": ".evozeus/wrapper.json",
        },
        "planned_files": deduped_planned_files,
        "migration_steps": [
            "Read .evozeus/wrapper.json and confirm canonical_repo before touching runtime installs.",
            "Diff wrapper-managed files; if they contain local edits, stop for merge review.",
            "Copy or merge wrapper-managed files only.",
            f"Add the EvoZeus-wrapper status check in {instruction_surface} before the target main chain if missing.",
            f"Append the EvoZeus-wrapper section in {instruction_surface} if missing; otherwise append a migration note instead of editing old text.",
            "Write a migration record under docs/wrapper-migrations/ with from/to wrapper versions, validation, and rollback.",
            "Update .evozeus/wrapper.json wrapper_version after validation passes.",
        ],
        "validation": validation,
    }
