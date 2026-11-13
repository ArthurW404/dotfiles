#!/usr/bin/env python3
"""Static security & structure linter for agent skills and persistent memory.

Inspects SKILL.md and agent-memory Markdown files for hidden Unicode/ANSI
characters, prompt-injection directives, remote-exec/exfiltration snippets,
literal secrets, and missing SKILL.md YAML frontmatter.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

HIDDEN_CHAR_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069]|\x1b\[")

LINE_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "prompt-injection",
        re.compile(
            r"\b(?:ignore\s+(?:all\s+|any\s+)?(?:previous|prior)\s+instructions"
            r"|disregard\s+(?:the\s+)?(?:system|prior)\s+prompt"
            r"|override\s+safety(?:_guard)?"
            r"|bypass\s+(?:the\s+)?sandbox)\b",
            re.IGNORECASE,
        ),
        "Instruction-override / policy-bypass phrasing detected",
    ),
    (
        "remote-exec",
        re.compile(
            r"(?:\b(?:curl|wget)\b[^|\n]*\|\s*(?:sh|bash|zsh|fish)\b"
            r"|\bbase64\s+(?:-d|--decode)\b[^|\n]*\|\s*(?:sh|bash|zsh|fish)\b)"
        ),
        "Remote script pipe-to-shell pattern detected",
    ),
    (
        "secret-exfil",
        re.compile(
            r"(?:\b(?:sk-ant-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{10,}|glpat-[A-Za-z0-9_-]{10,}"
            r"|AIza[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})\b"
            r"|-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----"
            r"|https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+)"
        ),
        "Literal credential, private key, or webhook URL detected",
    ),
    (
        "credential-read",
        re.compile(
            r"(?:cat|head|tail|curl\s+[^|\n]*-d\s+@)\s*[^\s]*(?:/|\$HOME/|~/)"
            r"\.(?:ssh/id_|aws/credentials|config/mcp/[^\s]*\.env)"
        ),
        "Direct credential file read/upload pattern detected",
    ),
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str


def check_frontmatter(path: Path, text: str) -> list[Finding]:
    """Verify SKILL.md starts with YAML frontmatter containing name and description."""
    if path.name != "SKILL.md":
        return []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [Finding(str(path), 1, "frontmatter", "Missing opening YAML frontmatter '---'")]
    end_idx = next((i for i, ln in enumerate(lines[1:], start=1) if ln.strip() == "---"), None)
    if end_idx is None:
        return [Finding(str(path), 1, "frontmatter", "Unclosed YAML frontmatter block")]
    block = "\n".join(lines[1:end_idx])
    missing = [key for key in ("name:", "description:") if not re.search(rf"(?m)^{key}\s*\S", block)]
    if missing:
        return [Finding(str(path), 1, "frontmatter", f"Frontmatter missing required field(s): {', '.join(missing)}")]
    return []


def lint_text(path: Path, text: str) -> list[Finding]:
    """Run all static checks on a single Markdown document."""
    findings = check_frontmatter(path, text)
    if "\ufeff" in text[1:]:
        findings.append(Finding(str(path), 1, "hidden-unicode", "Unexpected mid-file BOM character (U+FEFF)"))

    for idx, line in enumerate(text.splitlines(), start=1):
        if HIDDEN_CHAR_RE.search(line):
            findings.append(Finding(str(path), idx, "hidden-unicode", "Hidden zero-width/bidi or ANSI escape character"))
        for rule, pattern, msg in LINE_RULES:
            if pattern.search(line):
                findings.append(Finding(str(path), idx, rule, msg))
    return findings


def collect_default_targets(
    dotfiles_root: Path | None = None,
    memory_root: Path | None = None,
    include_external: bool = False,
) -> list[Path]:
    """Collect custom skills and agent-memory Markdown files for scanning."""
    df_root = dotfiles_root or Path(__file__).resolve().parent.parent.parent
    mem_root = memory_root or (Path.home() / "Projects" / "agent-memory")
    targets: list[Path] = []

    skills_dir = df_root / "agents" / "skills"
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            skill_md = entry / "SKILL.md"
            if not skill_md.is_file():
                continue
            if not include_external and entry.is_symlink() and "external" in os_readlink_str(entry):
                continue
            targets.append(skill_md)

    if mem_root.is_dir():
        for md in sorted(mem_root.rglob("*.md")):
            if ".git" not in md.parts:
                targets.append(md)
    return targets


def os_readlink_str(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def expand_paths(raw_paths: list[str]) -> list[Path]:
    """Expand file/directory CLI arguments into Markdown targets."""
    targets: list[Path] = []
    for raw in raw_paths:
        p = Path(raw).expanduser()
        if p.is_file():
            targets.append(p)
        elif p.is_dir():
            targets.extend(sorted(md for md in p.rglob("*.md") if ".git" not in md.parts))
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint agent skills and memory files for security & structure.")
    parser.add_argument("paths", nargs="*", help="Files or directories to scan (defaults to custom skills & memory)")
    parser.add_argument("--include-external", action="store_true", help="Include symlinked external submodule skills")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON")
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    args = parser.parse_args(argv)

    if args.test:
        from test_skill_lint import run_tests

        run_tests()
        return 0

    targets = expand_paths(args.paths) if args.paths else collect_default_targets(include_external=args.include_external)
    findings: list[Finding] = []
    for target in targets:
        try:
            findings.extend(lint_text(target, target.read_text(encoding="utf-8")))
        except OSError as exc:
            findings.append(Finding(str(target), 0, "io-error", str(exc)))

    if args.json:
        print(json.dumps({"scanned": len(targets), "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: [{f.rule}] {f.message}")
        print(f"skill_lint: scanned {len(targets)} file(s), {len(findings)} finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
