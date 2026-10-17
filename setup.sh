#!/usr/bin/env bash
# Cross-platform (Linux native apt/pacman/dnf & macOS Homebrew) idempotent installer
# Links dotfiles, sets up the Universal Agent Hub, and optionally installs core CLI tools.

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_NAME="$(uname -s)"
DRY_RUN=false
INSTALL_PACKAGES=false

# Auto-enable Linux desktop/X11 configs on Linux unless --no-x11 is passed; can also force with --x11
if [[ "$OS_NAME" == "Linux" ]]; then
    INSTALL_X11=true
else
    INSTALL_X11=false
fi

for arg in "$@"; do
    case "$arg" in
        -n|--dry-run)
            DRY_RUN=true
            ;;
        -p|--packages)
            INSTALL_PACKAGES=true
            ;;
        --linux|--x11)
            INSTALL_X11=true
            ;;
        --no-linux|--no-x11)
            INSTALL_X11=false
            ;;
        -h|--help)
            echo "Usage: $(basename "$0") [--dry-run|-n] [--packages|-p] [--x11|--no-x11]"
            echo "  --dry-run, -n       Preview operations without modifying files"
            echo "  --packages, -p      Install core packages (apt/pacman/dnf on Linux, brew on macOS)"
            echo "  --x11, --linux      Link Linux/X11 desktop configs (auto-enabled on Linux)"
            echo "  --no-x11, --no-linux Skip Linux/X11 desktop configs"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

install_system_packages() {
    echo "=== Installing Core CLI Packages ($OS_NAME) ==="
    if [[ "$OS_NAME" == "Darwin" ]]; then
        if command -v brew >/dev/null 2>&1; then
            local cmd="brew install fish neovim tmux ripgrep fd jq uv fzf zoxide git-delta starship eza"
            if [[ "$DRY_RUN" == true ]]; then
                echo "[dry-run] Would run: $cmd"
            else
                $cmd
            fi
        else
            echo "[skip] Homebrew not found on macOS"
        fi
    elif [[ "$OS_NAME" == "Linux" ]]; then
        if command -v apt-get >/dev/null 2>&1; then
            local cmd="sudo apt-get update && sudo apt-get install -y fish zsh vim neovim tmux git git-delta curl ripgrep fd-find jq fzf zoxide eza zsh-autosuggestions zsh-syntax-highlighting"
            if [[ "$DRY_RUN" == true ]]; then
                echo "[dry-run] Would run (Debian/Ubuntu apt): $cmd"
            else
                sudo apt-get update
                sudo apt-get install -y fish zsh vim neovim tmux git git-delta curl ripgrep fd-find jq fzf zoxide eza zsh-autosuggestions zsh-syntax-highlighting
            fi
        elif command -v pacman >/dev/null 2>&1; then
            local cmd="sudo pacman -S --needed --noconfirm fish zsh vim neovim tmux git git-delta curl ripgrep fd jq uv fzf zoxide eza starship zsh-autosuggestions zsh-syntax-highlighting"
            if [[ "$DRY_RUN" == true ]]; then
                echo "[dry-run] Would run (Arch pacman): $cmd"
            else
                $cmd
            fi
        elif command -v dnf >/dev/null 2>&1; then
            local cmd="sudo dnf install -y fish zsh vim neovim tmux git git-delta curl ripgrep fd-find jq fzf zoxide eza starship zsh-autosuggestions zsh-syntax-highlighting"
            if [[ "$DRY_RUN" == true ]]; then
                echo "[dry-run] Would run (Fedora dnf): $cmd"
            else
                $cmd
            fi
        else
            echo "[skip] No supported Linux package manager (apt-get, pacman, dnf) detected"
        fi

        # Install uv on Linux via standalone installer if not already present
        if ! command -v uv >/dev/null 2>&1; then
            if [[ "$DRY_RUN" == true ]]; then
                echo "[dry-run] Would install uv to ~/.local/bin via https://astral.sh/uv/install.sh"
            else
                curl -LsSf https://astral.sh/uv/install.sh | sh
            fi
        fi

        # Install starship on Linux via standalone installer if not already present
        if ! command -v starship >/dev/null 2>&1; then
            if [[ "$DRY_RUN" == true ]]; then
                echo "[dry-run] Would install starship to ~/.local/bin via https://starship.rs/install.sh"
            else
                mkdir -p "$HOME/.local/bin"
                curl -sS https://starship.rs/install.sh | sh -s -- -y -b "$HOME/.local/bin"
            fi
        fi
    fi
    echo ""
}

link_item() {
    local src="$1"
    local dst="$2"
    local parent_dir
    parent_dir="$(dirname "$dst")"

    if [[ ! -e "$src" ]]; then
        echo "[skip] Source does not exist: $src"
        return 0
    fi

    # Already linked to the exact target
    if [[ -L "$dst" ]] && [[ "$(readlink "$dst")" == "$src" ]]; then
        echo "[ok]   $dst -> $src"
        return 0
    fi

    if [[ "$DRY_RUN" == true ]]; then
        if [[ -e "$dst" && ! -L "$dst" ]]; then
            echo "[dry-run] Would back up existing $dst to ${dst}.bak"
        fi
        echo "[dry-run] Would link $dst -> $src"
        return 0
    fi

    mkdir -p "$parent_dir"

    # Back up existing regular file or directory before replacing with symlink
    if [[ -e "$dst" && ! -L "$dst" ]]; then
        local backup="${dst}.bak.$(date +%Y%m%d%H%M%S)"
        mv "$dst" "$backup"
        echo "[bak]  Backed up existing $dst -> $backup"
    fi

    ln -sfn "$src" "$dst"
    echo "[link] $dst -> $src"
}

echo "=== Detected OS: $OS_NAME ==="

if [[ "$INSTALL_PACKAGES" == true ]]; then
    install_system_packages
fi

echo "=== Linking Shell & Editor Configurations ==="
link_item "$DOTFILES_DIR/.config/fish/config.fish" "$HOME/.config/fish/config.fish"
link_item "$DOTFILES_DIR/.zshenv"                  "$HOME/.zshenv"
link_item "$DOTFILES_DIR/.zshrc"                   "$HOME/.zshrc"
link_item "$DOTFILES_DIR/.bashrc"                  "$HOME/.bashrc"
link_item "$DOTFILES_DIR/.vimrc"                   "$HOME/.vimrc"
link_item "$DOTFILES_DIR/.config/nvim"             "$HOME/.config/nvim"
link_item "$DOTFILES_DIR/.config/tmux/tmux.conf"   "$HOME/.config/tmux/tmux.conf"
link_item "$DOTFILES_DIR/.config/ripgrep/rc"       "$HOME/.config/ripgrep/rc"
link_item "$DOTFILES_DIR/.config/starship.toml"    "$HOME/.config/starship.toml"

# Preserve local git identity in untracked $DOTFILES_DIR/.gitconfig.local if an unlinked ~/.gitconfig exists
if [[ -f "$HOME/.gitconfig" && ! -L "$HOME/.gitconfig" && ! -f "$DOTFILES_DIR/.gitconfig.local" ]]; then
    if [[ "$DRY_RUN" == true ]]; then
        echo "[dry-run] Would copy existing ~/.gitconfig to $DOTFILES_DIR/.gitconfig.local"
    else
        cp "$HOME/.gitconfig" "$DOTFILES_DIR/.gitconfig.local"
        echo "[init] Copied existing ~/.gitconfig -> $DOTFILES_DIR/.gitconfig.local"
    fi
fi

link_item "$DOTFILES_DIR/.gitconfig"               "$HOME/.gitconfig"
link_item "$DOTFILES_DIR/.config/git/ignore"       "$HOME/.config/git/ignore"

# On Debian/Ubuntu, apt installs `fd-find` as `fdfind` and `bat` as `batcat`.
# Link them into ~/.local/bin so non-interactive agent subshells can invoke `fd` and `bat` directly.
if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
    link_item "$(command -v fdfind)" "$HOME/.local/bin/fd"
fi
if ! command -v bat >/dev/null 2>&1 && command -v batcat >/dev/null 2>&1; then
    link_item "$(command -v batcat)" "$HOME/.local/bin/bat"
fi

echo ""
echo "=== Linking Universal Agent Hub (Antigravity & Claude) ==="
# Antigravity global rules & skills manifest
link_item "$DOTFILES_DIR/agents/AGENTS.md"         "$HOME/.gemini/GEMINI.md"
link_item "$DOTFILES_DIR/agents/AGENTS.md"         "$HOME/.gemini/config/AGENTS.md"
link_item "$DOTFILES_DIR/agents/skills.json"       "$HOME/.gemini/config/skills.json"

# Claude Code global instructions & skills directory
link_item "$DOTFILES_DIR/agents/AGENTS.md"         "$HOME/.claude/CLAUDE.md"
link_item "$DOTFILES_DIR/agents/skills"            "$HOME/.claude/skills"

if [[ "$INSTALL_X11" == true ]]; then
    echo ""
    echo "=== Linking Linux / X11 Configurations ==="
    link_item "$DOTFILES_DIR/linux/.Xresources"        "$HOME/.Xresources"
    link_item "$DOTFILES_DIR/linux/.fehbg"             "$HOME/.fehbg"
    link_item "$DOTFILES_DIR/linux/.config/i3"         "$HOME/.config/i3"
    link_item "$DOTFILES_DIR/linux/.config/i3blocks"   "$HOME/.config/i3blocks"
fi

echo ""
echo "Done!"
