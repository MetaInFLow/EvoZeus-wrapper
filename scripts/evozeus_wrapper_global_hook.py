#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GLOBAL_DISPATCHER_COMMAND = (
    '/usr/bin/python3 "$HOME/.evozeus/hooks/evozeus_wrapper_dispatcher.py"'
)
GLOBAL_HOOK_EVENT = "SessionStart"
GLOBAL_HOOK_MATCHER = "startup|resume"
GLOBAL_HOOKS_CONFIG = Path(".codex/hooks.json")
GLOBAL_DISPATCHER = Path(".evozeus/hooks/evozeus_wrapper_dispatcher.py")
GLOBAL_HOOK_STATE = Path(".evozeus/hooks/state.json")
GLOBAL_HOOK_BACKUPS = Path(".evozeus/backups/global-hooks")


def _utc_transaction_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _paths(home: Path) -> dict[str, Path]:
    home = home.expanduser().resolve()
    return {
        "hooks": home / GLOBAL_HOOKS_CONFIG,
        "dispatcher": home / GLOBAL_DISPATCHER,
        "state": home / GLOBAL_HOOK_STATE,
        "backups": home / GLOBAL_HOOK_BACKUPS,
    }


def _dispatcher_template(wrapper_root: Path) -> Path:
    return wrapper_root.expanduser().resolve() / "templates/global/evozeus_wrapper_dispatcher.py"


def _dispatcher_entry() -> dict[str, Any]:
    return {
        "matcher": GLOBAL_HOOK_MATCHER,
        "hooks": [
            {
                "type": "command",
                "command": GLOBAL_DISPATCHER_COMMAND,
                "timeout": 30,
                "statusMessage": "Checking EvoZeus harnesses",
            }
        ],
    }


def _read_hooks_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"hooks": {}}
    if not path.is_file():
        raise ValueError(f"global hooks config must be a regular JSON file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid global hooks JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("global hooks config must contain a JSON object")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("global hooks config hooks must be a JSON object")
    return data


def _entry_has_dispatcher(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    handlers = entry.get("hooks")
    return isinstance(handlers, list) and any(
        isinstance(handler, dict) and handler.get("command") == GLOBAL_DISPATCHER_COMMAND
        for handler in handlers
    )


def _merge_dispatcher_registration(config: dict[str, Any]) -> tuple[dict[str, Any], str]:
    merged = json.loads(json.dumps(config))
    hooks = merged.setdefault("hooks", {})
    session_start = hooks.setdefault(GLOBAL_HOOK_EVENT, [])
    if not isinstance(session_start, list):
        raise ValueError(f"global hooks {GLOBAL_HOOK_EVENT} must be a list")

    preserved: list[dict[str, Any]] = []
    found = False
    for index, entry in enumerate(session_start):
        if not isinstance(entry, dict):
            raise ValueError(f"global hooks {GLOBAL_HOOK_EVENT}[{index}] must be an object")
        handlers = entry.get("hooks")
        if not isinstance(handlers, list):
            raise ValueError(f"global hooks {GLOBAL_HOOK_EVENT}[{index}].hooks must be a list")
        if _entry_has_dispatcher(entry):
            found = True
        else:
            preserved.append(entry)
    hooks[GLOBAL_HOOK_EVENT] = [*preserved, _dispatcher_entry()]
    if merged == config:
        return merged, "already_registered"
    return merged, "refresh" if found else "merge"


def _without_dispatcher_registration(config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    updated = json.loads(json.dumps(config))
    hooks = updated.setdefault("hooks", {})
    session_start = hooks.get(GLOBAL_HOOK_EVENT, [])
    if not isinstance(session_start, list):
        raise ValueError(f"global hooks {GLOBAL_HOOK_EVENT} must be a list")
    preserved = [entry for entry in session_start if not _entry_has_dispatcher(entry)]
    removed = len(preserved) != len(session_start)
    hooks[GLOBAL_HOOK_EVENT] = preserved
    return updated, removed


def _latest_changelog_version(wrapper_root: Path) -> str | None:
    path = wrapper_root / "CHANGELOG.md"
    if not path.is_file():
        return None
    match = re.search(r"(?m)^## \[(v\d+\.\d+\.\d+)\]", path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def _state_payload(wrapper_root: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "wrapper_source": str(wrapper_root.expanduser().resolve()),
        "installed_version": _latest_changelog_version(wrapper_root),
        "command": GLOBAL_DISPATCHER_COMMAND,
        "installation_status": "installed",
        "trust_status": "pending_review",
        "trust_status_source": "requires_user_confirmation_after_codex_hooks_review",
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def _snapshot(paths: dict[str, Path], backup_root: Path) -> dict[str, bytes | None]:
    snapshots: dict[str, bytes | None] = {}
    backup_root.mkdir(parents=True, exist_ok=False)
    for name in ("hooks", "dispatcher", "state"):
        path = paths[name]
        data = path.read_bytes() if path.is_file() else None
        snapshots[name] = data
        if data is not None:
            destination = backup_root / name
            destination.write_bytes(data)
    (backup_root / "snapshot.json").write_text(
        json.dumps({name: data is not None for name, data in snapshots.items()}, indent=2) + "\n",
        encoding="utf-8",
    )
    return snapshots


def _restore(paths: dict[str, Path], snapshots: dict[str, bytes | None]) -> None:
    for name, data in snapshots.items():
        path = paths[name]
        if data is None:
            if path.is_file() or path.is_symlink():
                path.unlink()
        else:
            _atomic_write(path, data)


def plan_global_hook_install(home: Path, wrapper_root: Path) -> dict[str, Any]:
    paths = _paths(home)
    template = _dispatcher_template(wrapper_root)
    errors: list[str] = []
    action = None
    try:
        config = _read_hooks_config(paths["hooks"])
        _, action = _merge_dispatcher_registration(config)
    except ValueError as exc:
        errors.append(str(exc))
    if not template.is_file():
        errors.append(f"global dispatcher template is missing: {template}")
    return {
        "stage": "global_hook_install",
        "status": "blocked" if errors else "planned",
        "writes": False,
        "approved": False,
        "registration_action": action,
        "hooks_config_exists": paths["hooks"].is_file(),
        "dispatcher_exists": paths["dispatcher"].is_file(),
        "state_exists": paths["state"].is_file(),
        "errors": errors,
    }


def read_global_hook_status(home: Path) -> dict[str, Any]:
    paths = _paths(home)
    errors: list[str] = []
    registered = False
    try:
        config = _read_hooks_config(paths["hooks"])
        session_start = config.get("hooks", {}).get(GLOBAL_HOOK_EVENT, [])
        registered = any(_entry_has_dispatcher(entry) for entry in session_start)
    except ValueError as exc:
        errors.append(str(exc))
    state: dict[str, Any] = {}
    if paths["state"].is_file():
        try:
            loaded = json.loads(paths["state"].read_text(encoding="utf-8"))
            state = loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError as exc:
            errors.append(f"invalid global hook state JSON: {exc}")
    installed = registered and paths["dispatcher"].is_file() and bool(state)
    return {
        "stage": "global_hook_status",
        "status": "installed" if installed else "not_installed",
        "writes": False,
        "mode": "global_session_dispatcher",
        "scope": "all_registered_wrapped_skills",
        "native_enforced": installed and state.get("trust_status") == "trusted",
        "registration_installed": registered,
        "dispatcher_installed": paths["dispatcher"].is_file(),
        "state_installed": bool(state),
        "trust_status": state.get("trust_status", "not_installed"),
        "installed_version": state.get("installed_version"),
        "errors": errors,
    }


def apply_global_hook_install(home: Path, wrapper_root: Path, *, approve: bool = False) -> dict[str, Any]:
    plan = plan_global_hook_install(home, wrapper_root)
    if plan["status"] == "blocked":
        return plan
    if not approve:
        return {**plan, "status": "approval_required"}

    paths = _paths(home)
    template = _dispatcher_template(wrapper_root).read_bytes()
    config = _read_hooks_config(paths["hooks"])
    merged, registration_action = _merge_dispatcher_registration(config)
    status = read_global_hook_status(home)
    if (
        registration_action == "already_registered"
        and paths["dispatcher"].is_file()
        and paths["dispatcher"].read_bytes() == template
        and status["status"] == "installed"
    ):
        return {**plan, "status": "already_installed", "approved": True, "errors": []}

    transaction_id = _utc_transaction_id()
    backup_root = paths["backups"] / transaction_id
    snapshots = _snapshot(paths, backup_root)
    try:
        _atomic_write(paths["dispatcher"], template)
        paths["dispatcher"].chmod(0o755)
        _atomic_write(
            paths["hooks"],
            (json.dumps(merged, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        _atomic_write(
            paths["state"],
            (json.dumps(_state_payload(wrapper_root), ensure_ascii=False, indent=2) + "\n").encode(
                "utf-8"
            ),
        )
    except Exception:
        _restore(paths, snapshots)
        raise
    return {
        **plan,
        "status": "installed",
        "writes": True,
        "approved": True,
        "registration_action": registration_action,
        "backup": str(backup_root),
        "trust_status": "pending_review",
        "errors": [],
    }


def apply_global_hook_uninstall(home: Path, *, approve: bool = False) -> dict[str, Any]:
    paths = _paths(home)
    try:
        config = _read_hooks_config(paths["hooks"])
        updated, removed = _without_dispatcher_registration(config)
    except ValueError as exc:
        return {
            "stage": "global_hook_uninstall",
            "status": "blocked",
            "writes": False,
            "errors": [str(exc)],
        }
    if not approve:
        return {
            "stage": "global_hook_uninstall",
            "status": "approval_required",
            "writes": False,
            "registration_found": removed,
            "errors": [],
        }
    if not removed and not paths["dispatcher"].exists() and not paths["state"].exists():
        return {
            "stage": "global_hook_uninstall",
            "status": "already_uninstalled",
            "writes": False,
            "errors": [],
        }

    backup_root = paths["backups"] / _utc_transaction_id()
    snapshots = _snapshot(paths, backup_root)
    try:
        _atomic_write(
            paths["hooks"],
            (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        for name in ("dispatcher", "state"):
            path = paths[name]
            if path.is_file() or path.is_symlink():
                path.unlink()
    except Exception:
        _restore(paths, snapshots)
        raise
    return {
        "stage": "global_hook_uninstall",
        "status": "uninstalled",
        "writes": True,
        "backup": str(backup_root),
        "errors": [],
    }


def record_global_hook_trust(home: Path, *, status: str, approve: bool = False) -> dict[str, Any]:
    allowed = {"pending_review", "trusted", "rejected"}
    if status not in allowed:
        raise ValueError(f"global hook trust status must be one of: {', '.join(sorted(allowed))}")
    current = read_global_hook_status(home)
    if current["status"] != "installed":
        return {
            "stage": "global_hook_trust",
            "status": "blocked",
            "writes": False,
            "errors": ["global hook must be installed before recording trust"],
        }
    if not approve:
        return {
            "stage": "global_hook_trust",
            "status": "approval_required",
            "writes": False,
            "requested_trust_status": status,
            "errors": [],
        }

    paths = _paths(home)
    state = json.loads(paths["state"].read_text(encoding="utf-8"))
    state["trust_status"] = status
    state["trust_status_source"] = "user_confirmed_after_codex_hooks_review"
    state["trust_status_recorded_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write(
        paths["state"],
        (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return {
        "stage": "global_hook_trust",
        "status": status,
        "writes": True,
        "trust_status": status,
        "errors": [],
    }
