#!/usr/bin/env python3
"""Safety guard lifecycle hook for Antigravity and Claude Code.

Inspects commands proposed by agents on stdin before execution (PreToolUse)
and blocks destructive operations (force push, commits to main/master,
hard resets, destructive deletions, remote script pipes).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys


def get_current_git_branch() -> str | None:
    """Retrieve current Git branch name if inside a git repository."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        if res.returncode == 0:
            branch = res.stdout.strip()
            return branch if branch else None
    except Exception:
        pass
    return None


def evaluate_command(command: str) -> tuple[str, str]:
    """Evaluate command and return (decision, reason).

    Decisions:
    - 'allow': Safe to proceed.
    - 'deny': Hard block destructive command.
    - 'force_ask': Always require explicit user confirmation.
    """
    cmd = command.strip()
    if not cmd:
        return "allow", "Empty command"

    # Git command inspection
    git_match = re.match(r"^git\s+([a-zA-Z0-9_-]+)", cmd)
    if git_match:
        git_subcmd = git_match.group(1)

        # 1. Block commits directly on main or master
        if git_subcmd == "commit":
            branch = get_current_git_branch()
            if branch in ("main", "master"):
                return (
                    "deny",
                    f"Direct commits to '{branch}' are prohibited by global agent rules. "
                    "Always create a descriptive feature branch (feat/..., fix/...) first.",
                )
            return "allow", "Safe git commit on feature branch"

        # 2. Block force pushing and direct pushes to main/master
        if git_subcmd == "push":
            if re.search(r"\s(--force|-f)(\s|$)", cmd) and "--force-with-lease" not in cmd:
                return (
                    "deny",
                    "Destructive 'git push --force' is strictly prohibited. "
                    "Use standard push or negotiate with the user.",
                )
            if "--force-with-lease" in cmd:
                return (
                    "force_ask",
                    "'git push --force-with-lease' rewrites remote history. User confirmation required.",
                )
            # Block pushing to main or master directly
            if re.search(r"\b(origin\s+)?(main|master)(\s|$)", cmd):
                return (
                    "deny",
                    "Direct push to 'main'/'master' is prohibited by global agent rules. "
                    "Push feature branches and merge via pull request.",
                )
            branch = get_current_git_branch()
            if branch in ("main", "master") and ":" not in cmd:
                return (
                    "deny",
                    f"Direct push while on '{branch}' branch is prohibited. "
                    "Always work and push on descriptive feature branches.",
                )
            return "allow", "Safe git push on feature branch"

        # 3. Block destructive git reset / clean
        if git_subcmd == "reset" and re.search(r"\s--hard\b", cmd):
            return (
                "deny",
                "'git reset --hard' destroys uncommitted changes. "
                "Use 'git stash' or targeted checkout instead.",
            )

        if git_subcmd == "clean" and re.search(r"\s-[a-zA-Z]*f", cmd):
            return (
                "deny",
                "'git clean -f' permanently deletes untracked files without recovery. "
                "Inspect files manually before removal.",
            )

        if git_subcmd in ("checkout", "restore") and (
            re.search(r"\s(--\s+)?\.\s*$", cmd) or re.search(r"\s(--staged\s+)?\.\s*$", cmd)
        ):
            return (
                "force_ask",
                "Wholesale discard of all working tree changes. User confirmation required.",
            )

        # 4. Require confirmation for branch deletion or history rebase/merge
        if git_subcmd == "branch" and re.search(r"\s-[a-zA-Z]*D\b", cmd):
            return "force_ask", "Force deleting a git branch ('git branch -D'). User confirmation required."

        if git_subcmd in ("rebase", "merge"):
            return "force_ask", "Branch rebase/merge rewrites branch topology. User confirmation required."

    # 4. Block destructive recursive deletions of critical paths
    rm_match = re.search(r"\brm\s+-[a-zA-Z]*[rR]", cmd)
    if rm_match:
        # Check targets
        critical_targets = [
            r"/\s*$",
            r"/\*",
            r"~\s*$",
            r"~/\*",
            r"\$HOME\b",
            r"\.\.\s*$",
            r"\.\./",
        ]
        for pattern in critical_targets:
            if re.search(pattern, cmd):
                return (
                    "deny",
                    f"Dangerous recursive rm targeting critical path ({pattern}). Blocked by safety guard.",
                )

    # 5. Block pipe-to-shell remote execution (curl/wget | sh/bash)
    if re.search(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh|fish)\b", cmd):
        return (
            "deny",
            "Piping untrusted remote scripts directly to shell (curl | sh) is prohibited.",
        )

    # 6. Block dangerous disk & full permission commands
    if re.search(r"\bchmod\s+-[a-zA-Z]*R\s+777\b", cmd):
        return "deny", "Recursive chmod 777 is unsafe and violates security guidelines."

    if re.search(r"\bdd\s+if=.*of=/dev/[a-z]+", cmd) or re.search(r"\bmkfs\b", cmd):
        return "deny", "Direct disk block device write detected. Blocked by safety guard."

    # 7. Require confirmation for branch deletion or history rebase/merge
    if re.search(r"\bgit\s+branch\s+-[a-zA-Z]*D\b", cmd):
        return "force_ask", "Force deleting a git branch ('git branch -D'). User confirmation required."

    if re.search(r"\bgit\s+(rebase|merge)\b", cmd):
        # We allow merge/rebase on feature branches with user confirmation
        return "force_ask", "Branch rebase/merge rewrites branch topology. User confirmation required."

    # 8. Modifying sensitive environment / token files via redirection
    if re.search(r">\s*(\.env|.*id_rsa|.*secret|.*token)", cmd, re.IGNORECASE):
        return "force_ask", "Modifying sensitive credentials/env file via shell redirection."

    return "allow", "Command passed safety checks"


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            # Nothing to evaluate, allow
            print(json.dumps({"decision": "allow", "reason": "No input payload"}))
            return

        payload = json.loads(raw_input)
    except Exception as exc:
        # Fail safe if JSON is malformed
        print(json.dumps({"decision": "allow", "reason": f"Input parse error: {exc}"}))
        return

    # Determine command string based on caller (Antigravity vs Claude Code)
    is_claude = "tool_input" in payload or "tool_name" in payload
    command = ""

    if "toolCall" in payload:
        # Antigravity format
        command = payload.get("toolCall", {}).get("args", {}).get("CommandLine", "")
    elif "tool_input" in payload:
        # Claude Code format
        command = payload.get("tool_input", {}).get("command", "")
    elif "CommandLine" in payload:
        command = payload.get("CommandLine", "")
    elif "command" in payload:
        command = payload.get("command", "")

    decision, reason = evaluate_command(command)

    if is_claude:
        # Claude Code output format
        if decision == "deny":
            # For Claude Code, output error to stderr and exit code 2 to hard block
            sys.stderr.write(f"SAFETY GUARD BLOCKED: {reason}\n")
            sys.exit(2)
        elif decision in ("ask", "force_ask"):
            # Request confirmation
            output = {
                "hookSpecificOutput": {
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
            print(json.dumps(output))
            return
        else:
            # Allow
            print(json.dumps({}))
            return

    # Antigravity format
    output = {
        "decision": decision,
        "reason": reason,
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
