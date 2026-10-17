---
name: web-research
description: >-
  Search the web, fetch online documentation, verify API signatures, and look up technical
  references. Trigger whenever researching unfamiliar libraries, resolving cryptic error
  messages, verifying version-specific API syntax, checking upstream GitHub issues/PRs,
  or finding authoritative technical documentation online.
---

# Web Research & Online Documentation Lookup

A systematic guide for searching, verifying, and extracting authoritative technical information from the web.

---

## 1. Local-First Principle

Before hitting the network, check if the answer is already on the local machine:
- **CLI Flags & Help**: `<command> --help`, `<command> -h`, `man <command>`
- **Language Docs**: `pydoc <module>`, `go doc <package>`, `rustup doc`, Neovim `:help <topic>`
- **Local Installed Source**: Inspect virtualenv packages (`uv pip show -f <pkg>`) or node_modules type definitions (`.d.ts`).

If local resources are insufficient, outdated, or the issue is an unknown bug/error, proceed to online research.

---

## 2. Source Authority Hierarchy

Always prioritize primary and authoritative sources over secondary summaries:

### Tier 1: Primary & Authoritative (Always Prefer)
- **Official Documentation**: Upstream project documentation (e.g., `docs.python.org`, `developer.mozilla.org`, `docs.rs`, `go.dev`).
- **Source Repositories**: Upstream GitHub/GitLab repositories for source code, changelogs, release notes, migration guides, and commit history.
- **Upstream Issue Trackers**: GitHub Issues/Discussions and PR threads for recent bug reports, workarounds, regressions, and API changes.
- **Package Registries**: PyPI, crates.io, pkg.go.dev, npmjs.com for package versions, dependency trees, and published READMEs.
- **Specifications & RFCs**: IETF RFCs, W3C/WHATWG specs, Python PEPs, TC39 proposals.

### Tier 2: High-Quality Community References
- **Authoritative Wikis**: ArchWiki (`wiki.archlinux.org`), Debian Wiki, Linux man-pages (`man7.org`).
- **Curated Q&A**: Stack Overflow / Stack Exchange (prioritize accepted, recently verified answers matching current tool versions).
- **Engineering Blogs**: Official engineering blogs from core teams (Google Open Source, Anthropic, Cloudflare, AWS, etc.).

### Tier 3: Low Quality (Avoid / Discard)
- **Content Farms & Aggregators**: GeeksforGeeks, W3Schools, TutorialsPoint, JavaTpoint.
- **AI-Generated SEO Spam**: Auto-generated scrape sites, duplicate mirrors of GitHub issues.
- **Outdated Blog Posts**: Tutorials older than 2–3 years referencing deprecated APIs without version caveats.

---

## 3. Tool Selection & Workflow

Choose the most efficient tool for the lookup:

| Task | Primary Tool | Best Practice |
| :--- | :--- | :--- |
| **Discovering pages / errors** | `search_web` | Use exact quotes for compiler errors, flags, and `site:` filters. |
| **Reading documentation / articles** | `read_url_content` | Fast HTTP conversion to markdown without browser overhead. |
| **Reading GitHub files / READMEs** | `read_url_content` | Prefer raw content URL (`raw.githubusercontent.com/...`) for clean markdown. |
| **Complex exploratory surveys** | `invoke_subagent` (research) | Delegate broad research to avoid polluting the main context window. |

---

## 4. Query Formulation Strategies

Make queries precise to filter out SEO junk:

1. **Exact Error Strings**:
   Wrap unique tokens or error codes in quotes:
   ```text
   "cannot lock ref" "git checkout"
   "E0382: use of moved value" rust
   "Operation not permitted" macos sandbox
   ```

2. **Domain-Targeted Search**:
   Restrict queries directly to official domains:
   ```text
   site:developer.mozilla.org View Transitions API
   site:github.com/neovim/neovim/issues "vim.diagnostic.jump"
   site:docs.rs reqwest "0.12" retry
   site:peps.python.org "PEP 723"
   ```

3. **Version-Scoped Search**:
   Always specify version numbers for fast-moving tools:
   ```text
   "neovim 0.11" lspconfig deprecated
   "python 3.12" asyncio run
   "starship" prompt exit code format
   ```

4. **Excluding SEO Noise**:
   Use negative keywords if needed:
   ```text
   "zsh completion" custom script -geeksforgeeks -tutorialspoint
   ```

---

## 5. Preferred & Whitelisted Domains

When prioritizing search results or selecting documentation URLs, favor these verified developer portals:

### Languages & Runtimes
- **Python**: `docs.python.org`, `peps.python.org`, `pypi.org`, `docs.astral.sh` (uv/ruff)
- **Rust**: `doc.rust-lang.org`, `docs.rs`, `crates.io`
- **Go**: `go.dev`, `pkg.go.dev`
- **Web / Frontend**: `developer.mozilla.org` (MDN), `typescriptlang.org`, `nodejs.org`
- **C / C++ / POSIX**: `cppreference.com`, `man7.org`, `en.cppreference.com`
- **Shell / Linux**: `wiki.archlinux.org`, `kernel.org`, `gnu.org/software`

### Repositories & Bug Trackers
- **GitHub**: `github.com`, `raw.githubusercontent.com`, `api.github.com`
- **GitLab**: `gitlab.com`

### Agent & AI Frameworks
- **Anthropic**: `docs.anthropic.com`, `github.com/anthropics`
- **Google Cloud & Gemini**: `cloud.google.com`, `ai.google.dev`, `github.com/google`

### User Whitelisted Domains
Add any custom, internal, or company-specific documentation portals below:
- *(Add your custom domains here, e.g. `docs.company.internal`, `gitlab.company.com`)*

---

## 6. Synthesis & Verification Rules

1. **Verify Version Parity**: Confirm the documentation matches the user's installed version (`fish --version`, `nvim --version`, `python3 --version`).
2. **Link Sources**: In your final explanation, link directly to the relevant upstream documentation using standard Markdown: `[Documentation Title](https://...)`.
3. **No Blind Copying**: Synthesize the core pattern into the minimal, surgical diff required for the project. Never blindly copy boilerplate.
