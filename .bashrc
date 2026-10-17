# ~/.bashrc
# Cross-platform (Linux native apt/pacman/dnf & macOS) bash configuration

# 1. Universal PATH & Environment (runs in both interactive and non-interactive shells)
if [ -d /opt/homebrew ]; then
    export HOMEBREW_PREFIX="/opt/homebrew"
    export HOMEBREW_CELLAR="/opt/homebrew/Cellar"
    export HOMEBREW_REPOSITORY="/opt/homebrew"
elif [ -d /usr/local/Homebrew ]; then
    export HOMEBREW_PREFIX="/usr/local"
    export HOMEBREW_CELLAR="/usr/local/Cellar"
    export HOMEBREW_REPOSITORY="/usr/local/Homebrew"
elif [ -d /home/linuxbrew/.linuxbrew ]; then
    export HOMEBREW_PREFIX="/home/linuxbrew/.linuxbrew"
    export HOMEBREW_CELLAR="/home/linuxbrew/.linuxbrew/Cellar"
    export HOMEBREW_REPOSITORY="/home/linuxbrew/.linuxbrew/Homebrew"
fi

case "$(uname -s)" in
    Darwin*)
        export PNPM_HOME="$HOME/Library/pnpm"
        ;;
    *)
        export PNPM_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/pnpm"
        ;;
esac

for dir in \
    /snap/bin \
    ${HOMEBREW_PREFIX:+"$HOMEBREW_PREFIX/bin"} \
    ${HOMEBREW_PREFIX:+"$HOMEBREW_PREFIX/sbin"} \
    "$HOME/.gemini/antigravity/bin" \
    "$HOME/Library/Application Support/Antigravity/bin" \
    "$HOME/.config/Antigravity/bin" \
    "$PNPM_HOME" \
    "$HOME/.cargo/bin" \
    "$HOME/.local/bin"; do
    if [ -n "$dir" ] && [ -d "$dir" ]; then
        case ":$PATH:" in
            *":$dir:"*) ;;
            *) PATH="$dir:$PATH" ;;
        esac
    fi
done
export PATH

# 2. If not running interactively, don't do anything further
[[ $- != *i* ]] && return

# History configuration
HISTCONTROL=ignoreboth
HISTSIZE=5000
HISTFILESIZE=10000

# Make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# Set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# Prompt configuration
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}$?\[\033[01;32m\][\u@\h]\[\033[00m\]\[\033[01;34m\]\W\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}$?[\u@\h]\W\$ '
fi
unset color_prompt

case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\$?[\u@\h]\W\a\]$PS1"
    ;;
esac

PS2=" >>> "

# Color support across macOS (BSD ls) and Linux (GNU dircolors)
if [[ "$(uname -s)" == "Darwin" ]]; then
    export CLICOLOR=1
    alias ls='ls -G'
elif [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
fi

# Debian/Ubuntu apt binary name compatibility (fdfind -> fd, batcat -> bat)
if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
    alias fd='fdfind'
fi
if ! command -v bat >/dev/null 2>&1 && command -v batcat >/dev/null 2>&1; then
    alias bat='batcat'
fi

alias ll='ls -lah'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'
