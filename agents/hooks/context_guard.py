#!/usr/bin/env python3
"""Zero-token PreInvocation context-guard hook for Antigravity.

Inspects session transcript size, step count, and idle gaps between turns and
surfaces a user-only inline markdown nudge (`systemMessage` left empty) when a
session grows large or its prompt cache has likely expired. Fails open (`{}`).
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

STEP_THRESHOLD = 150
STEP_REWARN_DELTA = 100
BYTES_THRESHOLD = 350_000
BYTES_REWARN_DELTA = 250_000
IDLE_MIN_STEPS = 20
IDLE_MINUTES_THRESHOLD = 45.0
TAIL_READ_BYTES = 65_536


@dataclass(frozen=True, slots=True)
class TranscriptStats:
    """Compact telemetry extracted from the tail of a session transcript."""

    steps: int
    size_bytes: int
    latest_user_step: int | None
    idle_minutes: float | None


def _sanitize_session_id(raw: str | None) -> str:
    if not raw or not isinstance(raw, str):
        return "default"
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw.strip()).strip("._")
    return cleaned[:64] or "default"


def _parse_iso_utc(raw: str | None) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _read_tail_entries(transcript_path: Path, size_bytes: int) -> list[dict[str, Any]]:
    offset = max(0, size_bytes - TAIL_READ_BYTES)
    with open(transcript_path, "rb") as fh:
        if offset > 0:
            fh.seek(offset)
        raw_chunk = fh.read()
    lines = raw_chunk.decode("utf-8", errors="ignore").splitlines()
    if offset > 0 and lines:
        lines = lines[1:]  # Drop potentially truncated leading line from byte seek.
    entries: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            entries.append(obj)
    return entries


def inspect_transcript(transcript_path: Path | None, initial_num_steps: int) -> TranscriptStats:
    """Inspect transcript tail for total steps, file size, and pre-turn idle time."""
    base_steps = max(0, initial_num_steps)
    if transcript_path is None or not transcript_path.is_file():
        return TranscriptStats(base_steps, 0, None, None)
    size_bytes = transcript_path.stat().st_size
    entries = _read_tail_entries(transcript_path, size_bytes)
    steps = max(base_steps, len(entries))
    if entries and isinstance(entries[-1].get("step_index"), int):
        steps = max(steps, entries[-1]["step_index"] + 1)

    latest_user_step: int | None = None
    idle_minutes: float | None = None
    for idx in range(len(entries) - 1, -1, -1):
        if entries[idx].get("type") != "USER_INPUT":
            continue
        raw_step = entries[idx].get("step_index")
        latest_user_step = raw_step if isinstance(raw_step, int) else None
        if idx > 0:
            t_user = _parse_iso_utc(entries[idx].get("created_at"))
            t_prev = _parse_iso_utc(entries[idx - 1].get("created_at"))
            if t_user is not None and t_prev is not None and t_user >= t_prev:
                idle_minutes = (t_user - t_prev).total_seconds() / 60.0
        break
    return TranscriptStats(steps, size_bytes, latest_user_step, idle_minutes)


def _state_path(conversation_id: str, state_dir: Path | None = None) -> Path:
    sid = _sanitize_session_id(conversation_id)
    if state_dir is not None:
        return state_dir / f"{sid}.json"
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base) if base else Path.home() / ".local" / "state"
    return root / "agent-context-guard" / f"{sid}.json"


def _load_state(path: Path, using_default_dir: bool) -> dict[str, Any]:
    candidates = [path]
    if using_default_dir and not path.is_file():
        candidates.append(Path("/tmp") / "agent-context-guard" / path.name)
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            continue
    return {}


def _save_state(path: Path, state: dict[str, Any], using_default_dir: bool) -> None:
    payload = json.dumps(state) + "\n"
    targets = [path] + ([Path("/tmp") / "agent-context-guard" / path.name] if using_default_dir else [])
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload, encoding="utf-8")
            return
        except OSError:
            continue


def _collect_reasons(stats: TranscriptStats, state: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    last_bs, last_bb = state.get("last_bloat_step"), state.get("last_bloat_bytes")
    bloat_due = last_bs is None or stats.steps >= last_bs + STEP_REWARN_DELTA or (
        last_bb is not None and stats.size_bytes >= last_bb + BYTES_REWARN_DELTA
    )
    if (stats.steps >= STEP_THRESHOLD or stats.size_bytes >= BYTES_THRESHOLD) and bloat_due:
        reasons.append(f"Long session ({stats.steps} steps, {stats.size_bytes // 1024} KB)")
        state["last_bloat_step"] = stats.steps
        state["last_bloat_bytes"] = stats.size_bytes
    if stats.steps >= IDLE_MIN_STEPS and stats.idle_minutes is not None and stats.idle_minutes >= IDLE_MINUTES_THRESHOLD:
        reasons.append(f"Idle {int(round(stats.idle_minutes))}m (prompt cache likely expired)")
    return reasons


def evaluate_payload(payload: dict[str, Any], state_dir: Path | None = None) -> dict[str, Any]:
    """Return a zero-token user notice if bloat or idle thresholds fire, else `{}`."""
    inv_num = payload.get("invocationNum")
    if isinstance(inv_num, int) and inv_num > 1:
        return {}
    raw_tp = payload.get("transcriptPath")
    transcript_path = Path(raw_tp) if isinstance(raw_tp, str) and raw_tp.strip() else None
    initial_steps = payload.get("initialNumSteps") if isinstance(payload.get("initialNumSteps"), int) else 0
    stats = inspect_transcript(transcript_path, initial_steps)

    conv_id = payload.get("conversationId") or payload.get("session_id")
    using_default_dir = state_dir is None
    state_file = _state_path(conv_id if isinstance(conv_id, str) else "default", state_dir)
    state = _load_state(state_file, using_default_dir)
    if stats.latest_user_step is not None and state.get("last_user_step") == stats.latest_user_step:
        return {}

    reasons = _collect_reasons(stats, state)
    if stats.latest_user_step is not None:
        state["last_user_step"] = stats.latest_user_step
    if not reasons:
        if state_file.is_file():
            _save_state(state_file, state, using_default_dir)
        return {}

    _save_state(state_file, state, using_default_dir)
    notice = f"> **Context guard**: {' · '.join(reasons)}. Consider `/compact` or starting a new chat."
    return {"injectSteps": [{"systemMessage": {"systemMessage": "", "metadata": {"user_markdown": notice}}}]}


def main() -> None:
    if "--test" in sys.argv:
        from test_context_guard import run_tests

        run_tests()
        return

    try:
        raw = sys.stdin.read()
        if raw.strip():
            payload = json.loads(raw)
            if isinstance(payload, dict):
                print(json.dumps(evaluate_payload(payload)))
                return
    except Exception:
        pass
    print("{}")


if __name__ == "__main__":
    main()
