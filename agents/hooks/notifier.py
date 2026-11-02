#!/usr/bin/env python3
"""Audible alert lifecycle hook for Antigravity.

Plays a macOS system sound when the agent finishes a turn (Stop) or asks
the user a question (PreToolUse on ask_question). Never alters agent
behaviour: Stop returns {} and PreToolUse defers to normal permissions.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

SOUND_DONE = "/System/Library/Sounds/Glass.aiff"
SOUND_PROMPT = "/System/Library/Sounds/Ping.aiff"
SOUND_ERROR = "/System/Library/Sounds/Basso.aiff"

# Stop reasons that warrant no sound (user already at the keyboard).
SILENT_STOP_REASONS = {"USER_CANCELED"}
ERROR_STOP_REASONS = {"ERROR", "MAX_TOKEN_BUDGET_EXCEEDED"}


def play_sound(path: str) -> None:
    """Play a sound without blocking the agent loop (no-op off macOS)."""
    if shutil.which("afplay") is None:
        return
    subprocess.Popen(
        ["afplay", path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def stop_sound(payload: dict) -> str | None:
    """Pick the sound for a Stop event, or None to stay silent."""
    if not payload.get("fullyIdle", True):
        return None  # Background tasks/subagents will wake the agent again.
    reason = payload.get("terminationReason", "")
    if reason in SILENT_STOP_REASONS:
        return None
    if reason in ERROR_STOP_REASONS:
        return SOUND_ERROR
    return SOUND_DONE


def read_payload() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError):
        return {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=["stop", "prompt"], required=True)
    args = parser.parse_args()
    payload = read_payload()

    if args.event == "stop":
        sound = stop_sound(payload)
        if sound:
            play_sound(sound)
        print(json.dumps({}))
    else:
        play_sound(SOUND_PROMPT)
        print(json.dumps({"decision": "ask"}))


if __name__ == "__main__":
    main()
