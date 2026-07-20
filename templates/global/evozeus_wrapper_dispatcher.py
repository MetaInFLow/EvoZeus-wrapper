#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        pass
    print(
        json.dumps(
            {
                "continue": True,
                "systemMessage": "EvoZeus global dispatcher is installed.",
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "evozeus_global_dispatcher=installed",
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
