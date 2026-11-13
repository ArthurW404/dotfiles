#!/usr/bin/env python3
"""Audible & remote alert lifecycle hook for Antigravity.

Plays a macOS system sound and optionally dispatches Discord notifications
(via webhook URL or Bot token + channel ID) when the agent stops on error or
asks the user a question (PreToolUse on ask_question). Never alters agent
behavior: Stop returns {} and PreToolUse defers to normal permissions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SOUND_DONE = "/System/Library/Sounds/Glass.aiff"
SOUND_PROMPT = "/System/Library/Sounds/Ping.aiff"
SOUND_ERROR = "/System/Library/Sounds/Basso.aiff"

SILENT_STOP_REASONS = {"USER_CANCELED"}
ERROR_STOP_REASONS = {"ERROR", "MAX_TOKEN_BUDGET_EXCEEDED"}

AGENT_DISCORD_CFG = Path.home() / ".config" / "agent" / "discord.json"
MCP_DISCORD_ENV = Path.home() / ".config" / "mcp" / "discord.env"


def _sanitize_cfg_value(raw: str | None) -> str | None:
    """Return stripped value or None if empty or unsafe for curl -K config."""
    if not raw or not isinstance(raw, str):
        return None
    val = raw.strip()
    if not val or any(ch.isspace() or ch in ('"', "\\") for ch in val):
        return None
    return val


def _load_json_config(path: Path = AGENT_DISCORD_CFG) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _load_bot_token(env_path: Path = MCP_DISCORD_ENV) -> str | None:
    """Resolve DISCORD_BOT_TOKEN from env or ~/.config/mcp/discord.env."""
    tok = _sanitize_cfg_value(os.environ.get("DISCORD_BOT_TOKEN"))
    if tok:
        return tok
    if not env_path.is_file():
        return None
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, val = stripped.partition("=")
            if key.strip().removeprefix("export ").strip() == "DISCORD_BOT_TOKEN":
                return _sanitize_cfg_value(val.strip().strip("'\""))
    except OSError:
        pass
    return None


def get_discord_target() -> tuple[str, list[str]] | None:
    """Resolve Discord target (url, extra curl -K lines) for webhook or bot API."""
    cfg = _load_json_config()

    for raw_url in (os.environ.get("DISCORD_WEBHOOK_URL"), cfg.get("webhook_url")):
        url = _sanitize_cfg_value(raw_url)
        if url and url.startswith("https://discord.com/api/webhooks/"):
            return url, []

    raw_ch = os.environ.get("DISCORD_ALERT_CHANNEL_ID") or cfg.get("channel_id")
    ch = raw_ch.strip() if isinstance(raw_ch, str) else ""
    if re.fullmatch(r"\d{17,20}", ch):
        tok = _load_bot_token()
        if tok:
            url = f"https://discord.com/api/v10/channels/{ch}/messages"
            headers = [
                f'header = "Authorization: Bot {tok}"',
                'user-agent = "DiscordBot (https://github.com/ArthurW404/dotfiles, 1.0)"',
            ]
            return url, headers
    return None


def send_discord_notification(message: str, wait: bool = False) -> bool:
    """Dispatch Discord notification via curl -K stdin (keeps secrets off ps)."""
    target = get_discord_target()
    if not target:
        return False

    url, extra_cfg = target
    payload_json = json.dumps({"content": message})
    cfg_lines = [f'url = "{url}"', *extra_cfg]
    cfg_bytes = ("\n".join(cfg_lines) + "\n").encode("utf-8")
    cmd = [
        "curl",
        "-s",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", payload_json,
        "--max-time", "3",
        "-K", "-",
    ]
    if wait:
        cmd.extend(["-o", "/dev/null", "-w", "%{http_code}"])
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if wait else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=not wait,
        )
        if wait:
            out, _ = proc.communicate(input=cfg_bytes, timeout=5)
            code = out.decode("utf-8", errors="ignore").strip()
            return proc.returncode == 0 and code.startswith("2")
        if proc.stdin is not None:
            proc.stdin.write(cfg_bytes)
            proc.stdin.flush()
            proc.stdin.close()
        return True
    except Exception:
        return False


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
        if not get_discord_target():
            print("[warn] No Discord target configured. Set DISCORD_WEBHOOK_URL or ~/.config/agent/discord.json")
            sys.exit(1)
        ok = send_discord_notification(
            "🔔 **Antigravity Alert Hook**: Discord notification test successful.",
            wait=True,
        )
        print("[ok] Dispatched Discord test notification." if ok else "[fail] Discord request failed.")
        sys.exit(0 if ok else 1)

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
