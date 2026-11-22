---
name: web-research
description: >-
  Search the web, fetch online documentation, verify API signatures, and look up technical
  references. Trigger whenever researching unfamiliar libraries, resolving cryptic error
  messages, verifying version-specific API syntax, checking upstream GitHub issues/PRs,
  or finding authoritative technical documentation online.
---

# Web Research & Online Documentation Lookup

## 1. Local-First Principle
Check local resources before hitting the network:
- **CLI & Man Pages**: `<command> --help`, `<command> -h`, `man <command>`
- **Language Docs & Installed Source**: `pydoc <module>`, `go doc <package>`, `rustup doc`, Neovim `:help <topic>`, virtualenv packages (`uv pip show -f <pkg>`), or `node_modules` type definitions (`.d.ts`).

## 2. Tool Selection
- **`search_web`**: Targeted queries, exact quoted error messages, `site:` filters, and explicit tool version numbers.
- **`invoke_subagent`**: Use `research` for broad exploratory surveys (isolates bulky readouts from the main context) or `browser` for interactive / JS-rendered pages.
- **Raw / Markdown Docs**: Prefer raw URLs (`raw.githubusercontent.com/...`) or `.md` doc mirrors over heavy HTML pages.

## 3. Authoritative Domains & Version Parity
- **Python**: `docs.python.org`, `peps.python.org`, `pypi.org`, `docs.astral.sh`
- **Rust / Go**: `doc.rust-lang.org`, `docs.rs`, `go.dev`, `pkg.go.dev`
- **Web / Node / Systems**: `developer.mozilla.org`, `typescriptlang.org`, `nodejs.org`, `cppreference.com`, `man7.org`, `wiki.archlinux.org`
- **Platforms & AI**: `github.com`, `docs.anthropic.com`, `cloud.google.com`, `ai.google.dev`

## 4. Verification & Synthesis
1. Confirm documentation matches the user's installed tool version (`python3 --version`, `fish --version`, `nvim --version`).
2. Link upstream documentation in final explanations using Markdown links.
3. Synthesize the minimal, surgical change required rather than copying boilerplate verbatim.
