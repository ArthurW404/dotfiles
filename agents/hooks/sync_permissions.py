#!/usr/bin/env python3
"""Idempotently syncs baseline permissions from agents/permissions.json
into Antigravity (~/.gemini/config/config.json) and Claude Code (~/.claude/settings.json).

Preserves all existing user-defined settings, keys, and grants while ensuring
standard tools and whitelisted URLs are active.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[warn] Failed to read {path}: {exc}")
        return {}


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as tmp:
        json.dump(data, tmp, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    shutil.move(tmp_name, path)


def sync_antigravity(config_path: Path, baseline: dict, dry_run: bool = False) -> bool:
    if not config_path.is_file():
        return False

    config = load_json(config_path)
    changed = False

    base_allow = baseline.get("allow", [])
    base_deny = baseline.get("deny", [])

    # 1. Update top-level permissions
    perms = config.setdefault("permissions", {})
    existing_allow = set(perms.get("allow", []))
    new_allow = sorted(list(existing_allow.union(base_allow)))
    if new_allow != perms.get("allow", []):
        perms["allow"] = new_allow
        changed = True

    existing_deny = set(perms.get("deny", []))
    new_deny = sorted(list(existing_deny.union(base_deny)))
    if new_deny != perms.get("deny", []):
        perms["deny"] = new_deny
        changed = True

    # 2. Update userSettings.globalPermissionGrants
    user_settings = config.setdefault("userSettings", {})
    grants = user_settings.setdefault("globalPermissionGrants", {})
    existing_grant_allow = set(grants.get("allow", []))
    new_grant_allow = sorted(list(existing_grant_allow.union(base_allow)))
    if new_grant_allow != grants.get("allow", []):
        grants["allow"] = new_grant_allow
        changed = True

    existing_grant_deny = set(grants.get("deny", []))
    new_grant_deny = sorted(list(existing_grant_deny.union(base_deny)))
    if new_grant_deny != grants.get("deny", []):
        grants["deny"] = new_grant_deny
        changed = True

    if changed:
        if dry_run:
            print(f"[dry-run] Would update permissions in {config_path}")
        else:
            atomic_write_json(config_path, config)
            print(f"[sync] Updated permissions in {config_path}")
    else:
        print(f"[ok]   {config_path} permissions already up to date")

    return changed


def sync_claude(settings_path: Path, baseline: dict, dry_run: bool = False) -> bool:
    settings = load_json(settings_path)
    changed = False

    base_allow = baseline.get("allow", [])
    base_deny = baseline.get("deny", [])

    perms = settings.setdefault("permissions", {})
    existing_allow = set(perms.get("allow", []))
    new_allow = sorted(list(existing_allow.union(base_allow)))
    if new_allow != perms.get("allow", []):
        perms["allow"] = new_allow
        changed = True

    existing_deny = set(perms.get("deny", []))
    new_deny = sorted(list(existing_deny.union(base_deny)))
    if new_deny != perms.get("deny", []):
        perms["deny"] = new_deny
        changed = True

    # Configure PreToolUse safety hook
    hooks = settings.setdefault("hooks", {})
    pre_tool_use = hooks.setdefault("PreToolUse", [])
    hook_script = str(Path.home() / "Projects" / "dotfiles" / "agents" / "hooks" / "safety_guard.py")
    expected_hook = {
        "matcher": "Bash",
        "command": f"python3 {hook_script}",
    }
    if not any(h.get("command") == expected_hook["command"] for h in pre_tool_use):
        pre_tool_use.append(expected_hook)
        changed = True

    if changed:
        if dry_run:
            print(f"[dry-run] Would update permissions & hooks in {settings_path}")
        else:
            atomic_write_json(settings_path, settings)
            print(f"[sync] Updated permissions & hooks in {settings_path}")
    else:
        print(f"[ok]   {settings_path} permissions already up to date")

    return changed


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    repo_root = Path(__file__).resolve().parent.parent.parent
    baseline_path = repo_root / "agents" / "permissions.json"

    if not baseline_path.is_file():
        print(f"[skip] Baseline permissions not found: {baseline_path}")
        return

    baseline = load_json(baseline_path)

    # Sync Antigravity
    gemini_config = Path.home() / ".gemini" / "config" / "config.json"
    sync_antigravity(gemini_config, baseline, dry_run=dry_run)

    # Sync Claude Code
    claude_settings = Path.home() / ".claude" / "settings.json"
    sync_claude(claude_settings, baseline, dry_run=dry_run)


if __name__ == "__main__":
    main()
