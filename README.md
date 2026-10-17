# dotfiles

Cross-platform (**Linux & macOS**) dotfiles (`fish` primary shell, `zsh`/`bash` agent-ready environments, `nvim`, `git`, `tmux`, `ripgrep`) and Universal Agent Hub for **Google Antigravity** and **Claude Code**.

Works natively on Linux (`apt` on Debian/Ubuntu, `pacman` on Arch, `dnf` on Fedora — no Homebrew/Linuxbrew required) and on macOS (Homebrew).

## Structure

- **Shells & Prompt**:
  - [`.config/fish/config.fish`](./.config/fish/config.fish) — Primary `fish` shell configuration (`PATH` exports, Catppuccin Mocha syntax theme, Git/editor/`uv` abbreviations, `fzf`/`zoxide`/`starship`/`direnv`/`eza` integrations, and Debian/Ubuntu `fdfind`/`batcat` support).
  - [`.config/starship.toml`](./.config/starship.toml) — Sleek, minimalist cross-shell prompt (uses universal Unicode symbols with no patched font required).
  - [`.zshenv`](./.zshenv), [`.zshrc`](./.zshrc), & [`.bashrc`](./.bashrc) — Cross-platform non-interactive `PATH` setup (so agent subshells always find `~/.local/bin`, `~/.cargo/bin`, `pnpm`, `/snap/bin`, or macOS Homebrew) and guarded interactive configs.
- **Editor & Developer CLI Tools**:
  - [`.config/nvim/init.lua`](./.config/nvim/init.lua) & [`.vimrc`](./.vimrc) — Modern Lua Neovim configuration (with `lazy.nvim`, Treesitter, Telescope, and LSP for `clangd`, `pyright`, `ruff`, `lua_ls`) plus classic Vim config.
  - [`.gitconfig`](./.gitconfig) & [`.config/git/ignore`](./.config/git/ignore) — Shared Git ergonomics (Delta syntax-highlighted pager with automatic `less` fallback, histogram diff, `zdiff3`, rebase-by-default, aliases, global ignore) with machine-local identity isolated in untracked `.gitconfig.local`.
  - [`.config/tmux/tmux.conf`](./.config/tmux/tmux.conf) — Ergonomic `tmux` setup (truecolor, Catppuccin Mocha status bar, mouse support, 1-indexed windows/panes, `vi` keys).
  - [`.config/ripgrep/rc`](./.config/ripgrep/rc) — Default `ripgrep` options (`--smart-case`, `--hidden`, `--glob=!.git/*`).
- **Universal Agent Hub ([`agents/`](./agents/))**:
  - [`agents/AGENTS.md`](./agents/AGENTS.md) — Shared baseline rules linked to `~/.gemini/GEMINI.md`, `~/.gemini/config/AGENTS.md`, and `~/.claude/CLAUDE.md`.
  - [`agents/skills/`](./agents/skills/) — Shared `SKILL.md` skills registered in `~/.gemini/config/skills.json` and symlinked to `~/.claude/skills`:
    - [`git-workflow`](./agents/skills/git-workflow/SKILL.md) — Branching, atomic commits, Chris Beams' 7 rules, rebase hygiene, and `git bisect`.
    - [`cpp-style`](./agents/skills/cpp-style/SKILL.md) — Google C++ Style Guide & C++ Core Guidelines (RAII, smart pointers, `string_view`/`span`, IWYU).
    - [`python-style`](./agents/skills/python-style/SKILL.md) — Google Python Style Guide & PEP 8 (strict 3.10+ typing, dataclasses, `pathlib`, docstrings, `ruff`/`pytest`).
    - [`python-uv`](./agents/skills/python-uv/SKILL.md) — `uv` project, dependency, and PEP 723 script workflows.
    - [`shell-style`](./agents/skills/shell-style/SKILL.md) — Google Shell Style Guide (`set -euo pipefail`, defensive quoting, when to switch to Python).
    - [`code-review`](./agents/skills/code-review/SKILL.md) — Pre-commit engineering & security review checklist.
    - [`dotfiles-sync`](./agents/skills/dotfiles-sync/SKILL.md) — Workflow for maintaining and syncing this repository.
    - **Anthropic Skills Catalog** ([`external/anthropics-skills`](https://github.com/anthropics/skills)) — Git submodule providing 19 official agent skills (including `skill-creator`, `mcp-builder`, `frontend-design`, `webapp-testing`, `pdf`, `docx`, `pptx`, `xlsx`), automatically linked into `agents/skills/`.
- **Linux X11 Desktop ([`linux/`](./linux/)) & Legacy ([`legacy/`](./legacy/))**:
  - `linux/` — Linux/X11 configurations (`.Xresources`, `.fehbg`, `i3`, `i3blocks`), automatically linked on Linux (or skipped via `--no-x11`).
  - `legacy/` — Archived configurations for Emacs (`legacy/emacs/init.el`) and Mutt (`legacy/mutt/muttrc`), ready to be restored whenever needed.

## Setup

Preview changes without modifying your home directory:

```sh
./setup.sh --dry-run
```

Apply symlinks idempotently (existing non-symlink files are automatically backed up with a `.bak.<timestamp>` suffix):

```sh
./setup.sh
```

Optionally bootstrap core CLI packages (`fish`, `neovim`, `tmux`, `ripgrep`, `fd` / `fd-find`, `jq`, `uv`, `fzf`, `zoxide`) using your native OS package manager (`apt-get`, `pacman`, `dnf` on Linux, or `brew` on macOS):

```sh
./setup.sh --packages
```
