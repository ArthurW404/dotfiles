#!/usr/bin/env python3
"""Unit tests for context_guard.py."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_guard  # noqa: E402


def _write_transcript(
    path: Path,
    total_steps: int,
    idle_minutes: float = 1.0,
    pad_bytes: int = 0,
) -> None:
    """Write a synthetic Antigravity transcript ending in a USER_INPUT entry."""
    base = datetime(2026, 11, 22, 1, 0, 0, tzinfo=timezone.utc)
    lines: list[str] = []
    last_idx = max(0, total_steps - 1)
    pad = ("x" * pad_bytes) if pad_bytes > 0 else ""

    for idx in range(last_idx):
        ts = (base + timedelta(seconds=idx)).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = {
            "step_index": idx,
            "type": "PLANNER_RESPONSE" if idx % 2 else "GENERIC",
            "created_at": ts,
        }
        if idx == 0 and pad:
            entry["content"] = pad
        lines.append(json.dumps(entry))

    user_ts = (base + timedelta(seconds=max(0, last_idx - 1), minutes=idle_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append(
        json.dumps(
            {
                "step_index": last_idx,
                "type": "USER_INPUT",
                "created_at": user_ts,
                "content": "Next prompt",
            }
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestContextGuard(unittest.TestCase):
    def test_fresh_session_is_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tp = root / "transcript.jsonl"
            _write_transcript(tp, total_steps=5, idle_minutes=1.0)
            res = context_guard.evaluate_payload(
                {"conversationId": "c1", "invocationNum": 1, "initialNumSteps": 5, "transcriptPath": str(tp)},
                state_dir=root / "state",
            )
            self.assertEqual(res, {})

    def test_skips_mid_turn_invocations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tp = root / "transcript.jsonl"
            _write_transcript(tp, total_steps=200, idle_minutes=1.0)
            res = context_guard.evaluate_payload(
                {"conversationId": "c2", "invocationNum": 2, "initialNumSteps": 200, "transcriptPath": str(tp)},
                state_dir=root / "state",
            )
            self.assertEqual(res, {})

    def test_long_session_step_threshold_and_throttling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            tp = root / "transcript.jsonl"

            _write_transcript(tp, total_steps=150, idle_minutes=1.0)
            res1 = context_guard.evaluate_payload(
                {"conversationId": "c3", "invocationNum": 1, "initialNumSteps": 150, "transcriptPath": str(tp)},
                state_dir=state_dir,
            )
            msg = res1["injectSteps"][0]["systemMessage"]
            self.assertEqual(msg["systemMessage"], "")
            md = msg["metadata"]["user_markdown"]
            self.assertIn("150 steps", md)
            self.assertIn("/compact", md)

            _write_transcript(tp, total_steps=170, idle_minutes=1.0)
            res2 = context_guard.evaluate_payload(
                {"conversationId": "c3", "invocationNum": 1, "initialNumSteps": 170, "transcriptPath": str(tp)},
                state_dir=state_dir,
            )
            self.assertEqual(res2, {})

            _write_transcript(tp, total_steps=255, idle_minutes=1.0)
            res3 = context_guard.evaluate_payload(
                {"conversationId": "c3", "invocationNum": 1, "initialNumSteps": 255, "transcriptPath": str(tp)},
                state_dir=state_dir,
            )
            self.assertIn("255 steps", res3["injectSteps"][0]["systemMessage"]["metadata"]["user_markdown"])

    def test_long_session_byte_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tp = root / "transcript.jsonl"
            _write_transcript(tp, total_steps=40, idle_minutes=1.0, pad_bytes=360_000)
            res = context_guard.evaluate_payload(
                {"conversationId": "c4", "invocationNum": 1, "initialNumSteps": 40, "transcriptPath": str(tp)},
                state_dir=root / "state",
            )
            md = res["injectSteps"][0]["systemMessage"]["metadata"]["user_markdown"]
            self.assertIn("40 steps", md)
            self.assertIn("KB", md)

    def test_idle_gap_triggers_on_established_session_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            tp_small = root / "small.jsonl"
            _write_transcript(tp_small, total_steps=5, idle_minutes=60.0)
            res_small = context_guard.evaluate_payload(
                {"conversationId": "c5a", "invocationNum": 1, "initialNumSteps": 5, "transcriptPath": str(tp_small)},
                state_dir=state_dir,
            )
            self.assertEqual(res_small, {})

            tp_est = root / "established.jsonl"
            _write_transcript(tp_est, total_steps=25, idle_minutes=60.0)
            res_est = context_guard.evaluate_payload(
                {"conversationId": "c5b", "invocationNum": 1, "initialNumSteps": 25, "transcriptPath": str(tp_est)},
                state_dir=state_dir,
            )
            md = res_est["injectSteps"][0]["systemMessage"]["metadata"]["user_markdown"]
            self.assertIn("Idle 60m", md)
            self.assertIn("prompt cache", md)

    def test_deduplicates_same_user_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            tp = root / "transcript.jsonl"
            _write_transcript(tp, total_steps=160, idle_minutes=1.0)
            payload = {"conversationId": "c6", "initialNumSteps": 160, "transcriptPath": str(tp)}

            first = context_guard.evaluate_payload(payload, state_dir=state_dir)
            self.assertIn("injectSteps", first)

            second = context_guard.evaluate_payload(payload, state_dir=state_dir)
            self.assertEqual(second, {})

    def test_tail_read_handles_large_transcript_and_partial_first_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tp = root / "large_tail.jsonl"
            _write_transcript(tp, total_steps=30, idle_minutes=52.0, pad_bytes=75_000)
            res = context_guard.evaluate_payload(
                {"conversationId": "c7", "invocationNum": 1, "initialNumSteps": 30, "transcriptPath": str(tp)},
                state_dir=root / "state",
            )
            md = res["injectSteps"][0]["systemMessage"]["metadata"]["user_markdown"]
            self.assertIn("Idle 52m", md)

    def test_fails_open_on_missing_or_corrupt_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "state"
            res_missing = context_guard.evaluate_payload(
                {"conversationId": "c8a", "initialNumSteps": 5, "transcriptPath": str(root / "missing.jsonl")},
                state_dir=state_dir,
            )
            self.assertEqual(res_missing, {})

            corrupt = root / "corrupt.jsonl"
            corrupt.write_text("{not json\nstill broken\n", encoding="utf-8")
            res_corrupt = context_guard.evaluate_payload(
                {"conversationId": "c8b", "initialNumSteps": 5, "transcriptPath": str(corrupt)},
                state_dir=state_dir,
            )
            self.assertEqual(res_corrupt, {})


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestContextGuard)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
