#!/usr/bin/env python3
"""Audible & remote alert lifecycle hook for Antigravity.

Plays a macOS system sound and optionally dispatches Discord webhook
notifications when the agent finishes a turn (Stop) or asks the user
a question (PreToolUse on ask_question). Never alters agent behavior:
Stop returns {} and PreToolUse defers to normal permissions.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SOUND_DONE = "/System/Library/Sounds/Glass.aiff"
SOUND_PROMPT = "/System/Library/Sounds/Ping.aiff"
SOUND_ERROR = "/System/Library/Sounds/Basso.aiff"

SILENT_STOP_REASONS = {"USER_CANCELED"}
ERROR_STOP_REASONS = {"ERROR", "MAX_TOKEN_BUDGET_EXCEEDED"}


def _valid_webhook_url(raw: str | None) -> str | None:
    """Return sanitized Discord webhook URL or None if invalid/unsafe for curl -K."""
    if not raw:
        return None
    url = raw.strip()
    if not url.startswith("https://discord.com/api/webhooks/"):
        return None
    if any(ch.isspace() or ch in ('"', "\\") for ch in url):
        return None
    return url


def get_discord_webhook_url() -> str | None:
    """Retrieve Discord webhook URL from environment or configuration file."""
    env_url = _valid_webhook_url(os.environ.get("DISCORD_WEBHOOK_URL"))
    if env_url:
        return env_url

    cfg_path = Path.home() / ".config" / "agent" / "discord.json"
    if cfg_path.is_file():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return _valid_webhook_url(data.get("webhook_url"))
        except Exception:
            pass
    return None


def send_discord_notification(message: str) -> None:
    """Send Discord notification asynchronously in the background."""
    webhook_url = get_discord_webhook_url()
    if not webhook_url:
        return

    payload_json = json.dumps({"content": message})
    # Pass the secret webhook URL via curl -K stdin so it stays out of process listings (ps).
    cfg_bytes = f'url = "{webhook_url}"\n'.encode("utf-8")
    cmd = [
        "curl",
        "-s",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", payload_json,
        "--max-time", "3",
        "-K", "-",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        if proc.stdin is not None:
            proc.stdin.write(cfg_bytes)
            proc.stdin.flush()
            proc.stdin.close()
    except Exception:
        pass


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
    parser = argparse.ArgumentParser(description="Antigravity alert lifecycle hook")
    parser.add_argument("--event", choices=["stop", "prompt"], required=False)
    parser.add_argument("--test-discord", action="store_true", help="Send test Discord notification")
    args = parser.parse_args()

    if args.test_discord:
        webhook = get_discord_webhook_url()
        if not webhook:
            print("[warn] No Discord webhook configured. Set DISCORD_WEBHOOK_URL or ~/.config/agent/discord.json")
            sys.exit(1)
        send_discord_notification("🔔 **Antigravity Alert Hook**: Discord notification test successful.")
        print("[ok] Dispatched Discord test notification.")
        return

    if not args.event:
        parser.print_help()
        sys.exit(1)

    payload = read_payload()

    if args.event == "stop":
        sound = stop_sound(payload)
        if sound:
            play_sound(sound)
            reason = payload.get("terminationReason", "COMPLETED")
            if reason in ERROR_STOP_REASONS:
                send_discord_notification(f"❌ **Antigravity Alert**: Stopped with error (`{reason}`).")
        print(json.dumps({}))
    else:
        play_sound(SOUND_PROMPT)
        send_discord_notification("❓ **Antigravity Alert**: Agent is waiting for your input.")
        print(json.dumps({"decision": "ask"}))


if __name__ == "__main__":
    main()
