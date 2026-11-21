#!/usr/bin/env python3
"""Unit tests for sync_permissions.py."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_permissions  # noqa: E402


class TestSyncPermissions(unittest.TestCase):
    def test_sync_claude_migrates_legacy_flat_pretool_hook_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_dir = root / "hooks"
            settings_path = root / "settings.json"
            safety_cmd = f"python3 {hooks_dir / 'safety_guard.py'}"
            breadcrumb_cmd = f"python3 {hooks_dir / 'breadcrumb.py'}"
            settings_path.write_text(
                json.dumps(
                    {
                        "permissions": {"allow": ["command(custom)"], "deny": []},
                        "hooks": {
                            "PreToolUse": [
                                {"matcher": "Bash", "command": safety_cmd},
                                {"matcher": "Custom", "hooks": [{"type": "command", "command": "echo ok"}]},
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            baseline = {"allow": ["command(git status)"], "deny": ["command(rm -rf /)"]}

            changed = sync_permissions.sync_claude(settings_path, baseline, hooks_dir=hooks_dir)
            self.assertTrue(changed)

            data = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(data["permissions"]["allow"], ["command(custom)", "command(git status)"])
            self.assertEqual(data["permissions"]["deny"], ["command(rm -rf /)"])

            pre = data["hooks"]["PreToolUse"]
            self.assertEqual(len(pre), 2)
            self.assertEqual(pre[0]["matcher"], "Custom")
            self.assertEqual(
                pre[1],
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": safety_cmd, "timeout": 5}],
                },
            )
            post = data["hooks"]["PostToolUse"]
            self.assertEqual(
                post,
                [
                    {
                        "matcher": "Bash|Edit|Write|MultiEdit",
                        "hooks": [{"type": "command", "command": breadcrumb_cmd, "timeout": 5}],
                    }
                ],
            )

            # Second pass must be a strict no-op
            self.assertFalse(sync_permissions.sync_claude(settings_path, baseline, hooks_dir=hooks_dir))

    def test_sync_antigravity_merges_without_clobbering_user_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "plugins": {"keep": True},
                        "permissions": {"allow": ["command(ls)"], "deny": []},
                        "userSettings": {"globalPermissionGrants": {"allow": ["read_file(/repo)"]}},
                    }
                ),
                encoding="utf-8",
            )
            baseline = {"allow": ["command(git status)"], "deny": ["command(rm -rf /)"]}

            self.assertTrue(sync_permissions.sync_antigravity(cfg_path, baseline))
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertEqual(data["plugins"], {"keep": True})
            self.assertEqual(data["permissions"]["allow"], ["command(git status)", "command(ls)"])
            self.assertEqual(
                data["userSettings"]["globalPermissionGrants"]["allow"],
                ["command(git status)", "read_file(/repo)"],
            )
            self.assertFalse(sync_permissions.sync_antigravity(cfg_path, baseline))


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSyncPermissions)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
