#!/usr/bin/env python3
"""Unit tests for bin/compact-log."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BIN_PATH = Path(__file__).resolve().parent / "compact-log"


def _load_compact_log():
    loader = importlib.machinery.SourceFileLoader("compact_log", str(BIN_PATH))
    spec = importlib.util.spec_from_loader("compact_log", loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


compact_log = _load_compact_log()


class TestCompactLog(unittest.TestCase):
    def test_strips_ansi_and_carriage_return_progress(self) -> None:
        raw = "\x1b[31mFAIL\x1b[0m\n10%\r50%\r100% done\n"
        out = compact_log.compact_text(raw, max_lines=20)
        lines = out.splitlines()
        self.assertEqual(lines, ["FAIL", "100% done"])

    def test_normalizes_and_deduplicates_scattered_errors(self) -> None:
        entries: list[str] = []
        for idx in range(50):
            for step in range(4):
                entries.append(f"2026-11-22T01:{idx:02d}:{step:02d}Z INFO heartbeat ok worker={step}")
            entries.append(
                f"2026-11-22T01:{idx:02d}:59Z ERROR: timeout req=12345678-1234-1234-1234-{idx:012d}"
            )
        out = compact_log.compact_text("\n".join(entries), max_lines=40, context=1)
        self.assertIn("[compact-log: 250 ->", out)
        self.assertIn("50 signal matches", out)
        self.assertIn("(×50)", out)
        self.assertEqual(out.count("ERROR: timeout"), 1)

    def test_preserves_multiline_python_traceback(self) -> None:
        lines = [f"INFO step {i}" for i in range(100)]
        lines.extend(
            [
                "Traceback (most recent call last):",
                '  File "app/worker.py", line 42, in run',
                "    result = parse_payload(data)",
                "ZeroDivisionError: division by zero",
            ]
        )
        lines.extend(f"INFO cleanup {i}" for i in range(20))
        out = compact_log.compact_text("\n".join(lines), max_lines=30, context=1)
        self.assertIn("Traceback (most recent call last):", out)
        self.assertIn('File "app/worker.py", line 42, in run', out)
        self.assertIn("result = parse_payload(data)", out)
        self.assertIn("ZeroDivisionError: division by zero", out)

    def test_caps_non_error_verbose_output_with_head_and_tail(self) -> None:
        raw = "\n".join(f"INFO processing item {i}" for i in range(300))
        out = compact_log.compact_text(raw, max_lines=20)
        out_lines = out.splitlines()
        self.assertTrue(out_lines[0].startswith("[compact-log: 300 -> 20 lines"))
        self.assertEqual(len(out_lines) - 1, 20)
        self.assertIn("INFO processing item 0", out)
        self.assertIn("... [omitted ", out)
        self.assertIn("INFO processing item 299", out)

    def test_errors_only_with_no_matches(self) -> None:
        raw = "\n".join(f"INFO all good {i}" for i in range(25))
        out = compact_log.compact_text(raw, errors_only=True)
        self.assertEqual(out, "[compact-log: 25 lines | 0 error/warn matches]")

    def test_truncates_ultra_long_lines(self) -> None:
        long_line = "X" * 500
        out = compact_log.compact_text(long_line, max_line_len=120)
        self.assertTrue(out.startswith("X" * 120))
        self.assertIn("[+380 chars]", out)

    def test_cli_file_and_stdin_and_missing_file_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "app.log"
            log_path.write_text("INFO start\nERROR boom\n", encoding="utf-8")

            res_file = subprocess.run(
                [sys.executable, str(BIN_PATH), "--errors-only", str(log_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_file.returncode, 0)
            self.assertIn("ERROR boom", res_file.stdout)

            res_stdin = subprocess.run(
                [sys.executable, str(BIN_PATH), "--errors-only", "-"],
                input="INFO ok\nWARN disk nearly full\n",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_stdin.returncode, 0)
            self.assertIn("WARN disk nearly full", res_stdin.stdout)

            res_missing = subprocess.run(
                [sys.executable, str(BIN_PATH), str(Path(tmp) / "missing.log")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_missing.returncode, 2)
            self.assertIn("compact-log:", res_missing.stderr)

    def test_short_log_consecutive_error_dedup_reports_signal_count(self) -> None:
        lines = [f"INFO step {i}" for i in range(20)] + ["ERROR: connection refused"] * 10
        out = compact_log.compact_text("\n".join(lines), max_lines=80)
        self.assertIn("ERROR: connection refused (×10)", out)
        self.assertIn("10 signal matches", out)


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCompactLog)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
