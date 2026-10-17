# Global Agent Rules & Guidelines

These baseline guidelines apply across all projects and workspaces for AI coding agents (Antigravity, Claude Code, etc.) on both Linux and macOS.

## 1. Environment, OS & Package Management
- **Supported Platforms**: Cross-platform Linux and macOS (`uname -s` / `$OSTYPE` aware).
- **System Package Managers**:
  - **Linux**: Use native system package managers (`apt` on Debian/Ubuntu, `pacman` on Arch, `dnf` on Fedora) — do not assume Homebrew/Linuxbrew is installed on Linux.
  - **macOS**: Use `brew` (Homebrew).
- **Interactive Shell**: `fish`, configured via `~/.config/fish/config.fish`.
- **Non-Interactive Agent Shells**: Agents frequently execute commands in `zsh`, `bash`, or `sh`. Common tool paths (`~/.local/bin`, `~/.cargo/bin`, `PNPM_HOME`, `/snap/bin`, and Homebrew on macOS) are exported in `~/.zshenv`, `~/.bashrc`, and `~/.config/fish/config.fish` so tools resolve reliably across platforms.

## 2. Tooling Preferences
- **Python**: Always prefer `uv` (`uv run`, `uv add`, `uv sync`, `uvx`) over raw `pip`, `venv`, `poetry`, or `conda` unless a project explicitly mandates otherwise.
- **Node.js / TypeScript**: Prefer `pnpm` over `npm` or `yarn` unless a lockfile (`package-lock.json` / `yarn.lock`) dictates otherwise.
- **Search & CLI**: Prefer modern fast CLI tools (`rg` for search, `fd` / `fdfind` for file finding, `jq` for JSON) when running terminal commands.

## 3. Git Conventions
- **Branching**: **Never push directly to `main` or `master`.** Always create a descriptive feature or fix branch (e.g., `feat/...`, `fix/...`, `chore/...`) for changes.
- **Commits**: Write clear, concise, imperative commit messages (following Conventional Commits where appropriate). Keep commits focused and atomic.
- **Safety**: Never commit secrets, credentials, `.env` files, or large binary artifacts. Avoid destructive git commands (`git reset --hard`, `git push --force`) without explicit user confirmation.

## 4. Coding Standards
- **Simplicity First**: Favor straightforward, readable, and maintainable code over premature abstraction.
- **Minimal Diffs**: Preserve existing code style, formatting, and unrelated comments when editing files.
- **Verification**: Always verify changes by running relevant tests, linters, typechecks, or dry-runs before considering a task complete.
