#!/usr/bin/env python3
"""Unit tests for breadcrumb.py."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import breadcrumb  # noqa: E402


class TestBreadcrumb(unittest.TestCase):
    def test_extract_antigravity_events(self) -> None:
        edit_payload = {
            "conversationId": "conv-123",
            "toolCall": {"name": "edit_file", "args": {"Path": "/repo/app.py"}},
        }
        self.assertEqual(breadcrumb.extract_event(edit_payload), ("edit", "/repo/app.py", False))

        cmd_payload = {
            "conversationId": "conv-123",
            "toolCall": {"name": "run_command", "args": {"CommandLine": "uv run pytest"}},
            "error": "exit status 1",
        }
        self.assertEqual(breadcrumb.extract_event(cmd_payload), ("cmd", "uv run pytest", True))

        read_payload = {"toolCall": {"name": "read_file", "args": {"Path": "/repo/app.py"}}}
        self.assertIsNone(breadcrumb.extract_event(read_payload))

    def test_extract_claude_events(self) -> None:
        write_payload = {
            "session_id": "claude-abc",
            "tool_name": "Write",
            "tool_input": {"file_path": "/repo/new.py"},
        }
        self.assertEqual(breadcrumb.extract_event(write_payload), ("edit", "/repo/new.py", False))

        bash_payload = {
            "session_id": "claude-abc",
            "tool_name": "Bash",
            "tool_input": {"command": "git status -sb"},
            "tool_response": {"is_error": True},
        }
        self.assertEqual(breadcrumb.extract_event(bash_payload), ("cmd", "git status -sb", True))

    def test_format_redacts_secrets_and_truncates(self) -> None:
        raw_cmd = (
            "curl -H 'Authorization: Bot secret123' https://discord.com/api/webhooks/99/tok "
            + ("x" * 150)
        )
        line = breadcrumb.format_entry("cmd", raw_cmd, False, now=datetime(2026, 11, 13, 10, 5, 1))
        self.assertIn("Authorization: Bot <REDACTED>", line)
        self.assertIn("https://discord.com/api/webhooks/<REDACTED>", line)
        self.assertNotIn("secret123", line)
        self.assertTrue(line.startswith("- [10:05:01] cmd `"))

    def test_append_dedups_consecutive_and_caps_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "scratch" / "breadcrumbs.md"
            e1 = breadcrumb.format_entry("edit", "/a.py", False, now=datetime(2026, 11, 13, 10, 0, 1))
            e2 = breadcrumb.format_entry("edit", "/a.py", False, now=datetime(2026, 11, 13, 10, 0, 9))
            breadcrumb.append_entry(log_file, e1, "s1", max_entries=3)
            breadcrumb.append_entry(log_file, e2, "s1", max_entries=3)

            lines = [ln for ln in log_file.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]
            self.assertEqual(len(lines), 1)
            self.assertIn("[10:00:09]", lines[0])

            for i in range(5):
                breadcrumb.append_entry(
                    log_file,
                    breadcrumb.format_entry("cmd", f"echo {i}", False, now=datetime(2026, 11, 13, 10, 1, i)),
                    "s1",
                    max_entries=3,
                )
            lines = [ln for ln in log_file.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]
            self.assertEqual(len(lines), 3)
            self.assertIn("echo 4", lines[-1])

    def test_resolve_log_path_prefers_artifact_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_STATE_HOME"] = tmp
            p1 = breadcrumb._resolve_log_path({"artifactDirectoryPath": "/art/dir", "conversationId": "c1"})
            self.assertEqual(p1, Path("/art/dir/scratch/breadcrumbs.md"))
            p2 = breadcrumb._resolve_log_path({"session_id": "abc/123"})
            self.assertEqual(p2, Path(tmp) / "agent-breadcrumbs" / "abc_123.md")


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestBreadcrumb)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
