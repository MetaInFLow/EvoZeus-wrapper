#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_LATEST_VERSION = "{{WRAPPER_VERSION}}"
MANIFEST_PATH = ".evozeus_evoinfra/wrapper.json"
LEGACY_MANIFEST_PATH = ".evozeus/wrapper.json"
LATEST_VERSION_ENV = "EVOZEUS_WRAPPER_LATEST_VERSION"
ENFORCEMENT_ENV = "EVOZEUS_WRAPPER_HOOK_ENFORCEMENT"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def version_key(tag: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def block(reason: str, next_action: str) -> int:
    return emit(
        {
            "continue": False,
            "stopReason": reason,
            "systemMessage": reason,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"EvoZeus-wrapper blocked start. next_action={next_action}",
            },
        }
    )


def allow(level: str, message: str, next_action: str) -> int:
    return emit(
        {
            "continue": True,
            "systemMessage": message,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"EvoZeus-wrapper hook_start_check level={level}; next_action={next_action}; {message}"
                ),
            },
        }
    )


def main() -> int:
    try:
        json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        pass

    root = repo_root()
    manifest = read_json(root / MANIFEST_PATH) or read_json(root / LEGACY_MANIFEST_PATH)
    if not manifest:
        return block(
            "EvoZeus wrapper harness manifest is missing or unreadable.",
            "repair_or_adopt_before_wrapper_managed_execution",
        )

    current = str(manifest.get("wrapper_version") or "")
    latest = os.environ.get(LATEST_VERSION_ENV) or DEFAULT_LATEST_VERSION
    if not latest or latest.startswith("{{"):
        latest = current
    enforcement = os.environ.get(ENFORCEMENT_ENV, "advisory").strip().lower()
    if enforcement not in {"advisory", "strict"}:
        enforcement = "advisory"

    current_key = version_key(current)
    latest_key = version_key(latest)
    if not current_key:
        return block("EvoZeus wrapper harness version is missing or invalid.", "repair_wrapper_manifest")
    if not latest_key:
        return block("EvoZeus wrapper latest version is missing or invalid.", f"set_{LATEST_VERSION_ENV}")

    if latest_key == current_key:
        return allow("allow", "EvoZeus wrapper harness is current.", "none")
    if latest_key < current_key:
        return allow("allow", "EvoZeus wrapper harness is ahead of the configured latest version.", "do_not_downgrade")
    if latest_key[0] > current_key[0]:
        return block(
            "EvoZeus wrapper harness has a major upgrade available.",
            "confirm_and_plan_harness_upgrade",
        )
    if enforcement == "strict":
        return block(
            "EvoZeus wrapper harness has a non-breaking upgrade available under strict enforcement.",
            "create_harness_upgrade_pr",
        )
    return allow(
        "warn",
        "EvoZeus wrapper harness has a non-breaking upgrade available; continue in advisory mode.",
        "create_harness_upgrade_pr",
    )


if __name__ == "__main__":
    raise SystemExit(main())
