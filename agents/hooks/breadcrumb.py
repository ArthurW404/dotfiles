#!/usr/bin/env python3
"""PostToolUse session breadcrumb accumulator for Antigravity and Claude Code.

Appends a compact, deduplicated trail of mutated files and executed shell
commands to a session-scoped Markdown file so state survives context
compaction and session handoffs. Never blocks tool execution.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

MAX_ENTRIES = 200
MAX_CMD_LEN = 120

_SECRET_PATTERNS = (
    (re.compile(r"https://discord\.com/api/webhooks/[^\s\"']+"), "https://discord.com/api/webhooks/<REDACTED>"),
    (re.compile(r"\b(sk-ant-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{10,}|glpat-[A-Za-z0-9_-]{10,}|AIza[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16})\b"), "<REDACTED_TOKEN>"),
    (re.compile(r"(Authorization:\s*(?:Bearer|Bot)\s+)[^\s\"']+", re.IGNORECASE), r"\1<REDACTED>"),
)


def _sanitize_session_id(raw: str | None) -> str:
    if not raw or not isinstance(raw, str):
        return "default"
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw.strip()).strip("._")
    return cleaned[:64] or "default"


def _redact_secrets(text: str) -> str:
    for pattern, repl in _SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def _state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base) if base else Path.home() / ".local" / "state"
    return root / "agent-breadcrumbs"


def _resolve_log_path(payload: dict) -> Path:
    artifact_dir = payload.get("artifactDirectoryPath")
    if isinstance(artifact_dir, str) and artifact_dir.strip():
        return Path(artifact_dir.strip()) / "scratch" / "breadcrumbs.md"
    session_id = _sanitize_session_id(payload.get("conversationId") or payload.get("session_id"))
    return _state_dir() / f"{session_id}.md"


def extract_event(payload: dict) -> tuple[str, str, bool] | None:
    """Return (kind, detail, failed) for mutating/command tools, else None."""
    if isinstance(payload.get("toolCall"), dict):
        tc = payload["toolCall"]
        name = tc.get("name", "")
        args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
        failed = bool(payload.get("error"))
        if name in ("write_file", "edit_file") and args.get("Path"):
            return "edit", str(args["Path"]), failed
        if name == "run_command" and args.get("CommandLine"):
            return "cmd", str(args["CommandLine"]), failed
        return None

    name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    resp = payload.get("tool_response")
    failed = bool(payload.get("error")) or (
        isinstance(resp, dict) and bool(resp.get("is_error") or resp.get("interrupted"))
    )
    if name in ("Write", "Edit", "MultiEdit") and tool_input.get("file_path"):
        return "edit", str(tool_input["file_path"]), failed
    if name == "Bash" and tool_input.get("command"):
        return "cmd", str(tool_input["command"]), failed
    return None


def format_entry(kind: str, detail: str, failed: bool, now: datetime | None = None) -> str:
    """Format a compact single-line Markdown breadcrumb entry."""
    ts = (now or datetime.now()).strftime("%H:%M:%S")
    clean = _redact_secrets(" ".join(detail.split())).replace("`", "'")
    if kind == "cmd" and len(clean) > MAX_CMD_LEN:
        clean = clean[: MAX_CMD_LEN - 3] + "..."
    suffix = " [ERR]" if failed else ""
    return f"- [{ts}] {kind} `{clean}`{suffix}"


def _entry_signature(line: str) -> str:
    return re.sub(r"^- \[\d{2}:\d{2}:\d{2}\]\s+", "", line)


def append_entry(path: Path, entry: str, session_id: str, max_entries: int = MAX_ENTRIES) -> Path:
    """Append entry to path with consecutive-duplicate collapsing and size cap."""
    header = f"# Session Breadcrumbs ({session_id})"
    target = path
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        target = Path("/tmp") / "agent-breadcrumbs" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)

    existing_lines: list[str] = []
    if target.is_file():
        existing_lines = [ln for ln in target.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]

    if existing_lines and _entry_signature(existing_lines[-1]) == _entry_signature(entry):
        existing_lines[-1] = entry
    else:
        existing_lines.append(entry)

    bounded = existing_lines[-max_entries:]
    target.write_text(header + "\n\n" + "\n".join(bounded) + "\n", encoding="utf-8")
    return target


def print_latest() -> int:
    """Print the most recently updated breadcrumb file across default dirs."""
    candidates: list[Path] = []
    for directory in (_state_dir(), Path("/tmp/agent-breadcrumbs")):
        if directory.is_dir():
            candidates.extend(directory.glob("*.md"))
    if not candidates:
        print("No session breadcrumbs recorded yet.")
        return 0
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f"<!-- {latest} -->")
    print(latest.read_text(encoding="utf-8"), end="")
    return 0


def main() -> None:
    if "--test" in sys.argv:
        from test_breadcrumb import run_tests

        run_tests()
        return
    if "--latest" in sys.argv:
        sys.exit(print_latest())

    try:
        raw = sys.stdin.read()
        if raw.strip():
            payload = json.loads(raw)
            event = extract_event(payload)
            if event:
                kind, detail, failed = event
                session_id = _sanitize_session_id(payload.get("conversationId") or payload.get("session_id"))
                append_entry(_resolve_log_path(payload), format_entry(kind, detail, failed), session_id)
    except Exception:
        pass
    print("{}")


if __name__ == "__main__":
    main()
