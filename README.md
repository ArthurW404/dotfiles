# dotfiles

Cross-platform (**Linux & macOS**) dotfiles (`fish` primary shell, `zsh`/`bash` agent-ready environments) and Universal Agent Hub for **Google Antigravity** and **Claude Code**.

Works natively on Linux (`apt` on Debian/Ubuntu, `pacman` on Arch, `dnf` on Fedora — no Homebrew/Linuxbrew required) and on macOS (Homebrew).

## Structure

- [`.config/fish/config.fish`](./.config/fish/config.fish) — Primary `fish` shell configuration (cross-platform `PATH` exports + OS-aware interactive aliases, including Debian/Ubuntu `fdfind`/`batcat` support).
- [`.zshenv`](./.zshenv), [`.zshrc`](./.zshrc), & [`.bashrc`](./.bashrc) — Cross-platform non-interactive `PATH` setup (so agent subshells always find `~/.local/bin`, `~/.cargo/bin`, `pnpm`, `/snap/bin`, or macOS Homebrew) and guarded interactive configs.
- [`agents/`](./agents/) — Universal Agent Hub:
  - [`agents/AGENTS.md`](./agents/AGENTS.md) — Shared baseline rules linked to `~/.gemini/GEMINI.md`, `~/.gemini/config/AGENTS.md`, and `~/.claude/CLAUDE.md`.
  - [`agents/skills/`](./agents/skills/) — Shared `SKILL.md` skills registered in `~/.gemini/config/skills.json` and symlinked to `~/.claude/skills`.
- [`linux/`](./linux/) — Linux/X11 desktop configurations (`.Xresources`, `.fehbg`, `i3`, `i3blocks`), automatically linked on Linux (or skipped via `--no-x11`).

## Setup

Preview changes without modifying your home directory:

```sh
./setup.sh --dry-run
```

Apply symlinks idempotently (existing non-symlink files are automatically backed up with a `.bak.<timestamp>` suffix):

```sh
./setup.sh
```

Optionally bootstrap core CLI packages (`fish`, `ripgrep`, `fd` / `fd-find`, `jq`, `uv`) using your native OS package manager (`apt-get`, `pacman`, `dnf` on Linux, or `brew` on macOS):

```sh
./setup.sh --packages
```
