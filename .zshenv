# ~/.zshenv
# Sourced on ALL zsh invocations across Linux (apt/pacman/dnf) and macOS.
# Keep this file fast and restricted to environment variables and PATH setup.

# Deduplicate PATH entries automatically
typeset -U path PATH

# macOS Homebrew (or optional Linuxbrew if present — set directly for fast, sandbox-safe startup)
if [[ -d /opt/homebrew ]]; then
    export HOMEBREW_PREFIX="/opt/homebrew"
    export HOMEBREW_CELLAR="/opt/homebrew/Cellar"
    export HOMEBREW_REPOSITORY="/opt/homebrew"
    fpath=("/opt/homebrew/share/zsh/site-functions" $fpath)
    export INFOPATH="/opt/homebrew/share/info:${INFOPATH:-}"
elif [[ -d /usr/local/Homebrew ]]; then
    export HOMEBREW_PREFIX="/usr/local"
    export HOMEBREW_CELLAR="/usr/local/Cellar"
    export HOMEBREW_REPOSITORY="/usr/local/Homebrew"
    fpath=("/usr/local/share/zsh/site-functions" $fpath)
    export INFOPATH="/usr/local/share/info:${INFOPATH:-}"
elif [[ -d /home/linuxbrew/.linuxbrew ]]; then
    export HOMEBREW_PREFIX="/home/linuxbrew/.linuxbrew"
    export HOMEBREW_CELLAR="/home/linuxbrew/.linuxbrew/Cellar"
    export HOMEBREW_REPOSITORY="/home/linuxbrew/.linuxbrew/Homebrew"
    fpath=("/home/linuxbrew/.linuxbrew/share/zsh/site-functions" $fpath)
    export INFOPATH="/home/linuxbrew/.linuxbrew/share/info:${INFOPATH:-}"
fi

# Rust / Cargo
if [[ -f "$HOME/.cargo/env" ]]; then
    . "$HOME/.cargo/env"
fi

# Cross-platform pnpm directory
if [[ "$OSTYPE" == darwin* ]]; then
    export PNPM_HOME="$HOME/Library/pnpm"
else
    export PNPM_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/pnpm"
fi

# NVM directory (actual interactive loading happens in .zshrc if needed,
# but add default node bin to PATH if present for non-interactive shells)
export NVM_DIR="$HOME/.nvm"
if [[ -d "$NVM_DIR/versions/node" ]]; then
    latest_node_bin="$(find "$NVM_DIR/versions/node" -maxdepth 2 -name bin -type d 2>/dev/null | sort -V | tail -n 1)"
    [[ -n "$latest_node_bin" ]] && path=("$latest_node_bin" $path)
    unset latest_node_bin
fi

# Prepend user and platform tool paths
path=(
    "$HOME/.local/bin"
    "$HOME/.cargo/bin"
    "$PNPM_HOME"
    "$HOME/.gemini/antigravity/bin"
    ${HOMEBREW_PREFIX:+"$HOMEBREW_PREFIX/bin"}
    ${HOMEBREW_PREFIX:+"$HOMEBREW_PREFIX/sbin"}
    $path
)

[[ -d /snap/bin ]] && path+=(/snap/bin)

if [[ -d "$HOME/Library/Application Support/Antigravity/bin" ]]; then
    path=("$HOME/Library/Application Support/Antigravity/bin" $path)
elif [[ -d "$HOME/.config/Antigravity/bin" ]]; then
    path=("$HOME/.config/Antigravity/bin" $path)
fi

if [[ -f "$HOME/.config/ripgrep/rc" ]]; then
    export RIPGREP_CONFIG_PATH="$HOME/.config/ripgrep/rc"
fi

export PATH
