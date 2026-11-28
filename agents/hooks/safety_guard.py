#!/usr/bin/env python3
"""Safety guard lifecycle hook for Antigravity and Claude Code.

Inspects commands proposed by agents on stdin before execution (PreToolUse)
and blocks destructive operations (force push, commits to main/master,
hard resets, destructive deletions, remote script pipes).
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

PUSH_VALUE_FLAGS = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
COMMIT_MSG_VALUE_FLAGS = {"-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c", "--reedit-message"}
DB_BINARY_RE = re.compile(r"\.(?:sqlite3?|db|duckdb)(?:-(?:wal|shm))?$", re.IGNORECASE)
DECISION_RANK = {"allow": 0, "ask": 1, "force_ask": 2, "deny": 3}

ALLOWED_FF_TARGETS = {
    "origin/main",
    "origin/master",
    "origin/head",
    "@{u}",
    "@{upstream}",
}

BRANCH_NON_CREATION_FLAGS = {
    "-d", "-D", "--delete",
    "-m", "-M", "--move",
    "-c", "-C", "--copy",
    "-a", "--all", "-r", "--remotes",
    "-l", "--list",
    "--show-current",
    "-v", "-vv", "--verbose",
    "-u", "--set-upstream-to",
    "--unset-upstream",
    "--edit-description",
    "-f", "--force",
    "--contains", "--no-contains",
    "--merged", "--no-merged",
    "--points-at",
}

BRANCH_NON_CREATION_PREFIXES = (
    "--set-upstream-to=",
    "--contains=",
    "--no-contains=",
    "--merged=",
    "--no-merged=",
    "--points-at=",
    "--sort=",
    "--format=",
)


def get_current_git_branch(cwd: str | None = None) -> str | None:
    """Retrieve current Git branch name if inside a git repository (including unborn branches)."""
    base = ["git", "-C", cwd] if cwd else ["git"]
    for args in (["symbolic-ref", "--short", "HEAD"], ["rev-parse", "--abbrev-ref", "HEAD"]):
        try:
            res = subprocess.run([*base, *args], capture_output=True, text=True, timeout=1, check=False)
            if res.returncode == 0:
                branch = res.stdout.strip()
                if branch:
                    return branch
        except Exception:
            pass
    return None


def is_memory_repo(cwd: str | None = None) -> bool:
    """Check if target repository is specifically ~/Projects/agent-memory.
    
    agent-memory is an explicitly exempted repository where fast-forward atomic commits
    to main are allowed for cross-session persistent memory logging.
    """
    try:
        cmd = ["git"]
        if cwd:
            cmd.extend(["-C", cwd])
        cmd.extend(["rev-parse", "--show-toplevel"])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1, check=False)
        if res.returncode == 0:
            top_path = Path(res.stdout.strip()).resolve()
            expected_path = (Path.home() / "Projects" / "agent-memory").resolve()
            return top_path == expected_path
    except Exception:
        pass
    return False


def _tokenize(cmd: str) -> list[str]:
    """Split a single command segment respecting shell quotes."""
    try:
        return shlex.split(cmd)
    except ValueError:
        return cmd.strip().split()


def parse_git_command(cmd: str) -> tuple[str | None, str | None, list[str]]:
    """Parse git subcommand, target working directory, and arguments."""
    tokens = _tokenize(cmd)
    if not tokens or tokens[0] != "git":
        return None, None, []

    idx = 1
    target_dir = None
    while idx < len(tokens):
        token = tokens[idx]
        if token == "-C" and idx + 1 < len(tokens):
            target_dir = tokens[idx + 1]
            idx += 2
        elif token.startswith("-C") and len(token) > 2:
            target_dir = token[2:]
            idx += 1
        elif token.startswith("--work-tree="):
            target_dir = token.split("=", 1)[1]
            idx += 1
        elif token in ("-c", "--git-dir"):
            idx += 2
        elif token.startswith("-"):
            idx += 1
        else:
            return token, target_dir, tokens[idx + 1 :]
    return None, target_dir, []


def push_refspecs(args: list[str]) -> list[str]:
    """Return refspecs of a `git push` invocation (positionals after remote)."""
    positionals = []
    rest = iter(args)
    for token in rest:
        if token in ("&&", "||", ";", "|"):
            break
        if token in PUSH_VALUE_FLAGS:
            next(rest, None)
        elif not token.startswith("-"):
            positionals.append(token)
    return [spec.lstrip("+") for spec in positionals[1:]]


def pushes_to_protected(refspecs: list[str]) -> bool:
    """Return True if any refspec's destination is main/master."""
    dests = (spec.split(":")[-1].removeprefix("refs/heads/") for spec in refspecs)
    return any(dest in ("main", "master") for dest in dests)


def pushes_current_branch(refspecs: list[str]) -> bool:
    """Return True if the push would update the checked-out branch."""
    return not refspecs or any(spec in ("HEAD", "@") for spec in refspecs)


def git_ref_exists(ref: str, cwd: str | None = None) -> bool:
    """Check if a git ref exists locally."""
    try:
        cmd = ["git"]
        if cwd:
            cmd.extend(["-C", cwd])
        cmd.extend(["rev-parse", "--verify", ref])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1, check=False)
        return res.returncode == 0
    except Exception:
        return False


def get_branch_behind_count(base_ref: str, upstream_ref: str, cwd: str | None = None) -> int:
    """Return how many commits upstream_ref is ahead of base_ref."""
    try:
        cmd = ["git"]
        if cwd:
            cmd.extend(["-C", cwd])
        cmd.extend(["rev-list", f"{base_ref}..{upstream_ref}", "--count"])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1, check=False)
        if res.returncode == 0:
            return int(res.stdout.strip())
    except Exception:
        pass
    return 0


def is_safe_ff_merge_on_protected(args: list[str]) -> bool:
    """Check if `git merge` represents safe fast-forward remote tracking sync."""
    if "--ff-only" not in args:
        return False
    targets = [arg for arg in args if not arg.startswith("-") and arg not in ("&&", "||", ";", "|")]
    if not targets:
        return True
    return all(target.lower() in ALLOWED_FF_TARGETS for target in targets)


def _parse_checkout_switch(args: list[str]) -> tuple[bool, str | None, str | None]:
    idx = -1
    for i, arg in enumerate(args):
        if arg in ("-b", "-B", "-c", "-C"):
            idx = i
            break
    if idx == -1 or idx + 1 >= len(args):
        return False, None, None
    new_branch = args[idx + 1]
    start_point = None
    for arg in args[idx + 2 :]:
        if not arg.startswith("-") and arg not in ("&&", "||", ";", "|"):
            start_point = arg
            break
    return True, new_branch, start_point


def _parse_branch_creation(args: list[str]) -> tuple[bool, str | None, str | None]:
    if any(arg in BRANCH_NON_CREATION_FLAGS for arg in args):
        return False, None, None
    if any(arg.startswith(BRANCH_NON_CREATION_PREFIXES) for arg in args):
        return False, None, None
    positionals = [arg for arg in args if not arg.startswith("-") and arg not in ("&&", "||", ";", "|")]
    if not positionals:
        return False, None, None
    return True, positionals[0], positionals[1] if len(positionals) > 1 else None


def _parse_worktree_creation(args: list[str]) -> tuple[bool, str | None, str | None]:
    if not args or args[0] != "add":
        return False, None, None
    wt_args = args[1:]
    new_branch = None
    positionals = []
    i = 0
    while i < len(wt_args):
        arg = wt_args[i]
        if arg in ("&&", "||", ";", "|"):
            break
        if arg in ("-b", "-B") and i + 1 < len(wt_args):
            new_branch = wt_args[i + 1]
            i += 2
            continue
        if not arg.startswith("-"):
            positionals.append(arg)
        i += 1
    start_point = positionals[1] if len(positionals) > 1 else None
    return True, new_branch, start_point


def parse_branch_creation(subcmd: str, args: list[str]) -> tuple[bool, str | None, str | None]:
    """Parse branch creation from subcommand and arguments."""
    if subcmd in ("checkout", "switch"):
        return _parse_checkout_switch(args)
    if subcmd == "branch":
        return _parse_branch_creation(args)
    if subcmd == "worktree":
        return _parse_worktree_creation(args)
    return False, None, None


def check_branch_creation_freshness(
    subcmd: str, args: list[str], git_dir: str | None = None
) -> tuple[str, str]:
    """Inspect branch creation to ensure base freshness and prevent nested feature branches."""
    is_creation, new_branch, start_point = parse_branch_creation(subcmd, args)
    if not is_creation:
        return "allow", "Not a branch creation command"

    if start_point and (start_point.startswith("origin/") or start_point.startswith("upstream/")):
        return "allow", f"Branching directly from remote tracking ref '{start_point}'"

    curr_branch = get_current_git_branch(git_dir)
    target_base = start_point if start_point else curr_branch
    branch_label = new_branch if new_branch else "new branch"

    if target_base in ("main", "master"):
        upstream = f"origin/{target_base}"
        if git_ref_exists(upstream, git_dir):
            behind = get_branch_behind_count(target_base if start_point else "HEAD", upstream, git_dir)
            if behind > 0:
                spec_label = f"Specified base '{target_base}'" if start_point else f"Local '{target_base}'"
                return (
                    "deny",
                    f"{spec_label} is {behind} commit(s) behind '{upstream}'. "
                    f"Fast-forward first ('git merge --ff-only {upstream}' or 'git pull --ff-only' with BypassSandbox) "
                    f"or branch directly from remote ('git checkout -b {branch_label} {upstream}').",
                )
        return "allow", f"Branching from up-to-date base '{target_base}'"

    if not start_point and curr_branch and not curr_branch.startswith("HEAD"):
        return (
            "force_ask",
            f"Creating branch '{branch_label}' from feature branch '{curr_branch}'. "
            f"If branching from latest remote main/master was intended, specify 'origin/main' or 'origin/master' as start point.",
        )

    return "allow", "Branch creation passed safety checks"


def _has_db_binary_path(args: list[str]) -> bool:
    """Return True if any non-message argument targets a database binary file."""
    rest = iter(args)
    for token in rest:
        if token in COMMIT_MSG_VALUE_FLAGS:
            next(rest, None)
            continue
        if token.startswith(("--message=", "--file=", "--reuse-message=", "--reedit-message=")):
            continue
        if token.startswith("-"):
            continue
        if DB_BINARY_RE.search(token):
            return True
    return False


def _check_worktree_add(args: list[str]) -> tuple[str, str] | None:
    """Block ad-hoc /tmp worktrees and checking out main/master in a linked worktree."""
    if not args or args[0] != "add":
        return None
    creating_branch = False
    detached = False
    positionals: list[str] = []
    rest = iter(args[1:])
    for arg in rest:
        if arg in ("-b", "-B", "--orphan"):
            creating_branch = True
            next(rest, None)
        elif arg == "--reason":
            next(rest, None)
        elif arg in ("-d", "--detach"):
            detached = True
        elif not arg.startswith("-"):
            positionals.append(arg)
    if not positionals:
        return None
    wt_path = positionals[0]
    if wt_path in ("/tmp", "/private/tmp") or wt_path.startswith(("/tmp/", "/private/tmp/")):
        return (
            "deny",
            "Ad-hoc git worktrees in /tmp are prohibited (Antigravity denies read_file outside workspace). "
            "Use managed worktrees or in-repo branches.",
        )
    commit_ish = positionals[1] if len(positionals) > 1 else None
    if commit_ish in ("main", "master") and not creating_branch and not detached:
        return (
            "deny",
            f"Checking out '{commit_ish}' in a linked worktree is prohibited. "
            f"Detach at 'origin/{commit_ish}' or create a feature branch with '-b'.",
        )
    return None


def eval_git_command(
    git_subcmd: str, git_dir: str | None, git_args: list[str], cmd: str
) -> tuple[str, str]:
    """Evaluate git operations against safety rules."""
    if git_subcmd in ("add", "commit") and _has_db_binary_path(git_args):
        return "deny", "Staging or committing database binaries (*.db, *.sqlite*, *.duckdb) is prohibited."

    if git_subcmd == "worktree":
        wt_result = _check_worktree_add(git_args)
        if wt_result is not None:
            return wt_result

    if git_subcmd in ("checkout", "switch", "branch", "worktree"):
        fresh_decision, fresh_reason = check_branch_creation_freshness(git_subcmd, git_args, git_dir)
        if fresh_decision != "allow":
            return fresh_decision, fresh_reason

    branch = get_current_git_branch(git_dir)
    in_memory_repo = is_memory_repo(git_dir)

    if git_subcmd == "commit" and branch in ("main", "master"):
        if in_memory_repo:
            return "allow", "Direct commit to main permitted for agent-memory repository"
        return "deny", f"Direct commits to '{branch}' are prohibited. Work on feature branches."

    if git_subcmd == "push":
        if re.search(r"\s(--force|-f)(\s|$)", cmd) and "--force-with-lease" not in cmd:
            return "deny", "Destructive 'git push --force' is strictly prohibited. Use standard push."
        if "--force-with-lease" in cmd:
            return "force_ask", "'git push --force-with-lease' rewrites remote history. User confirmation required."
        refspecs = push_refspecs(git_args)
        if pushes_to_protected(refspecs):
            if in_memory_repo:
                return "allow", "Push to main permitted for agent-memory repository"
            return "deny", "Direct push to 'main'/'master' is prohibited. Work on feature branches."
        if branch in ("main", "master") and pushes_current_branch(refspecs):
            if in_memory_repo:
                return "allow", "Push to main permitted for agent-memory repository"
            return "deny", f"Direct push while on '{branch}' branch is prohibited. Work on feature branches."
        return "allow", "Safe git push on feature branch"

    if git_subcmd == "reset" and re.search(r"\s--hard\b", cmd):
        return "deny", "'git reset --hard' destroys uncommitted changes. Use 'git stash' or targeted checkout."
    if git_subcmd == "clean" and re.search(r"\s-[a-zA-Z]*f", cmd):
        return "deny", "'git clean -f' permanently deletes untracked files without recovery."
    if git_subcmd in ("checkout", "restore") and (
        re.search(r"\s(--\s+)?\.\s*$", cmd) or re.search(r"\s(--staged\s+)?\.\s*$", cmd)
    ):
        return "force_ask", "Wholesale discard of all working tree changes. User confirmation required."
    if git_subcmd == "branch" and re.search(r"\s-[a-zA-Z]*D\b", cmd):
        return "force_ask", "Force deleting a git branch ('git branch -D'). User confirmation required."

    if git_subcmd in ("rebase", "merge"):
        if any(arg in ("--abort", "--quit") for arg in git_args):
            return "allow", f"Safe abort of in-progress git {git_subcmd}"
        if branch in ("main", "master"):
            if in_memory_repo:
                return "allow", f"Safe git {git_subcmd} on main in agent-memory repository"
            if git_subcmd == "merge" and is_safe_ff_merge_on_protected(git_args):
                return "allow", f"Safe fast-forward sync of remote tracking branch on {branch}"
            return "deny", f"Direct {git_subcmd} on '{branch}' branch is prohibited. Work on feature branches."
        return "allow", f"Safe git {git_subcmd} on feature branch"

    if git_subcmd == "stash" and re.search(r"\b(drop|clear)\b", cmd):
        return "force_ask", "Wiping stashed changes ('git stash drop/clear'). User confirmation required."

    return "allow", "Safe git command"


def eval_system_command(cmd: str) -> tuple[str, str]:
    """Evaluate non-git system commands against destructive patterns."""
    if re.search(r"\brm\s+-[a-zA-Z]*[rR]", cmd):
        critical_targets = [
            r"(?:^|\s)/+(?:\s|$)",
            r"(?:^|\s)/+\*",
            r"(?:^|\s)~(?:\s|$)",
            r"(?:^|\s)~(/|\*)",
            r"\$HOME\b",
            r"(?:^|\s)\.\.(?:\s|$|/)",
        ]
        for pattern in critical_targets:
            if re.search(pattern, cmd):
                return "deny", f"Dangerous recursive rm targeting critical path ({pattern}). Blocked by safety guard."

    if re.search(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh|fish)\b", cmd):
        return "deny", "Piping untrusted remote scripts directly to shell (curl | sh) is prohibited."

    if re.search(r"\bchmod\s+-[a-zA-Z]*R\s+777\b", cmd):
        return "deny", "Recursive chmod 777 is unsafe and violates security guidelines."

    if re.search(r"\bdd\s+if=.*of=/dev/[a-z]+", cmd) or re.search(r"\bmkfs\b", cmd):
        return "deny", "Direct disk block device write detected. Blocked by safety guard."

    if re.search(r">\s*(\.env|.*id_rsa|.*secret|.*token)", cmd, re.IGNORECASE):
        return "force_ask", "Modifying sensitive credentials/env file via shell redirection."

    return "allow", "Command passed safety checks"


def _resolve_git_dir(git_dir: str | None, cwd: str | None) -> str | None:
    """Resolve effective git working directory from explicit -C and hook cwd."""
    if git_dir:
        path = Path(git_dir).expanduser()
        if not path.is_absolute() and cwd:
            return str(Path(cwd).expanduser() / path)
        return str(path)
    return cwd


def _extract_hook_cwd(payload: dict) -> str | None:
    """Extract agent working directory from Antigravity or Claude Code hook payload."""
    raw_cwd = payload.get("cwd")
    if isinstance(raw_cwd, str) and raw_cwd.strip():
        return raw_cwd.strip()
    workspaces = payload.get("workspacePaths")
    if isinstance(workspaces, list) and workspaces and isinstance(workspaces[0], str) and workspaces[0].strip():
        return workspaces[0].strip()
    return None


def split_command_segments(cmd: str) -> list[str]:
    """Split a shell command on unquoted &&, ||, ;, or newline delimiters."""
    segments: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    escaped = False
    i, n = 0, len(cmd)
    while i < n:
        ch = cmd[i]
        if escaped:
            buf.append(ch)
            escaped = False
        elif ch == "\\" and quote != "'":
            buf.append(ch)
            escaped = True
        elif quote is None and ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif quote == ch:
            quote = None
            buf.append(ch)
        elif quote is None and ch in (";", "\n"):
            if seg := "".join(buf).strip():
                segments.append(seg)
            buf = []
        elif quote is None and ch in ("&", "|") and i + 1 < n and cmd[i + 1] == ch:
            if seg := "".join(buf).strip():
                segments.append(seg)
            buf = []
            i += 1
        else:
            buf.append(ch)
        i += 1
    if tail := "".join(buf).strip():
        segments.append(tail)
    return segments


def _apply_cd_segment(segment: str, cwd: str | None) -> tuple[bool, str | None]:
    """Track working directory changes across compound `cd <dir> && ...` commands."""
    tokens = _tokenize(segment)
    if not tokens or tokens[0] != "cd":
        return False, cwd
    if "-" in tokens[1:]:
        return True, cwd
    targets = [tok for tok in tokens[1:] if not tok.startswith("-")]
    if not targets:
        return True, str(Path.home())
    return True, _resolve_git_dir(targets[0], cwd)


def _evaluate_segment(segment: str, cwd: str | None) -> tuple[str, str]:
    cleaned = segment.strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1].strip()
    git_subcmd, git_dir, git_args = parse_git_command(cleaned)
    if git_subcmd:
        effective_dir = _resolve_git_dir(git_dir, cwd)
        return eval_git_command(git_subcmd, effective_dir, git_args, cleaned)
    return eval_system_command(cleaned)


def evaluate_command(command: str, cwd: str | None = None) -> tuple[str, str]:
    """Evaluate single or compound commands and return strictest (decision, reason)."""
    cmd = command.strip()
    if not cmd:
        return "allow", "Empty command"

    segments = split_command_segments(cmd)
    if not segments:
        return "allow", "Empty command"

    current_cwd = cwd
    worst: tuple[str, str] = ("allow", "Command passed safety checks")
    for seg in segments:
        is_cd, current_cwd = _apply_cd_segment(seg, current_cwd)
        if is_cd:
            continue
        decision, reason = _evaluate_segment(seg, current_cwd)
        if DECISION_RANK.get(decision, 0) >= DECISION_RANK.get(worst[0], 0):
            worst = (decision, reason)
            if decision == "deny":
                return worst
    return worst


def main() -> None:
    if "--test" in sys.argv:
        from test_safety_guard import run_tests
        run_tests()
        return

    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow", "reason": "No input payload"}))
            return
        payload = json.loads(raw_input)
    except Exception as exc:
        print(json.dumps({"decision": "allow", "reason": f"Input parse error: {exc}"}))
        return

    is_claude = "tool_input" in payload or "tool_name" in payload
    command = ""
    if "toolCall" in payload:
        command = payload.get("toolCall", {}).get("args", {}).get("CommandLine", "")
    elif "tool_input" in payload:
        command = payload.get("tool_input", {}).get("command", "")
    elif "CommandLine" in payload:
        command = payload.get("CommandLine", "")
    elif "command" in payload:
        command = payload.get("command", "")

    hook_cwd = _extract_hook_cwd(payload)
    try:
        decision, reason = evaluate_command(command, cwd=hook_cwd)
    except Exception as exc:
        sys.stderr.write(f"SAFETY GUARD WARNING: Hook evaluation exception: {exc}\n")
        decision, reason = "allow", f"Internal guard exception: {exc}"

    if decision == "force_ask" and shutil.which("afplay"):
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Ping.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    if is_claude:
        if decision == "deny":
            sys.stderr.write(f"SAFETY GUARD BLOCKED: {reason}\n")
            sys.exit(2)
        if decision in ("ask", "force_ask"):
            print(json.dumps({"hookSpecificOutput": {"permissionDecision": "ask", "permissionDecisionReason": reason}}))
            return
        print(json.dumps({}))
        return

    print(json.dumps({"decision": decision, "reason": reason}))


if __name__ == "__main__":
    main()
