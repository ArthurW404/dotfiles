---
name: dotfiles-sync
description: >-
  Workflow for adding or updating cross-platform (Linux & macOS) shell configurations,
  dotfiles, and shared AI agent rules/skills in ~/Projects/dotfiles. Activate this skill
  when modifying dotfiles, shell configs (fish/zsh/bash), or adding skills for Antigravity and Claude.
---

# Dotfiles & Agent Hub Sync Skill

## Repository Layout
- `agents/AGENTS.md`: Shared global instructions linked to Antigravity (`~/.gemini/GEMINI.md`, `~/.gemini/config/AGENTS.md`) and Claude (`~/.claude/CLAUDE.md`).
- `agents/skills/<skill-name>/SKILL.md`: Universal skills registered in Antigravity (`~/.gemini/config/skills.json`) and symlinked for Claude (`~/.claude/skills`):
  - `git-workflow`, `cpp-style`, `python-style`, `python-uv`, `shell-style`, `code-review`, `dotfiles-sync`.
- `.config/fish/config.fish`: Primary interactive and non-interactive `fish` shell configuration (Linux & macOS aware).
- `.zshenv`, `.zshrc`, & `.bashrc`: Cross-platform non-interactive `PATH` setup and interactive shell configs.
- `.gitconfig` & `.config/git/ignore`: Shared Git config (includes untracked `~/.gitconfig.local` for local identity) and global ignore file.
- `.config/nvim/init.lua` & `.vimrc`: Modern Lua Neovim configuration and classic Vim configuration.
- `.config/tmux/tmux.conf` & `.config/ripgrep/rc`: Ergonomic `tmux` and `ripgrep` configurations.
- `linux/`: Linux/X11 desktop configurations (`.Xresources`, `.fehbg`, `i3`, `i3blocks`), auto-linked when `setup.sh` runs on Linux.

## Adding or Updating Configurations
1. Make edits on a non-`master` branch inside `~/Projects/dotfiles`.
2. Run the idempotent installer in dry-run mode first to preview symlink actions:
   ```sh
   ./setup.sh --dry-run
   ```
3. Apply symlinks:
   ```sh
   ./setup.sh
   ```
