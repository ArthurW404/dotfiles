# ~/.zshrc
# Sourced only for interactive zsh shells. Environment/PATH exports live in ~/.zshenv.

[[ -o interactive ]] || return

# History configuration
HISTFILE="$HOME/.histfile"
HISTSIZE=10000
SAVEHIST=10000
setopt HIST_IGNORE_DUPS
setopt SHARE_HISTORY

# Completion system
zstyle :compinstall filename "$HOME/.zshrc"
autoload -Uz compinit
compinit -C
zstyle ':completion:*' menu select

# Color support across macOS (BSD ls) and Linux (GNU coreutils)
if [[ "$OSTYPE" == darwin* ]]; then
    export CLICOLOR=1
    alias ls='ls -G'
elif [[ -x /usr/bin/dircolors ]]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias dir='dir --color=auto'
    alias vdir='vdir --color=auto'
fi

# Debian/Ubuntu apt binary name compatibility (fdfind -> fd, batcat -> bat)
if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
    alias fd='fdfind'
fi
if ! command -v bat >/dev/null 2>&1 && command -v batcat >/dev/null 2>&1; then
    alias bat='batcat'
fi

if command -v nvim >/dev/null 2>&1; then
    alias vim='nvim'
    alias vi='nvim'
    alias v='nvim'
else
    alias v='vim'
fi

alias ll='ls -lah'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

# Prompt configuration
PS2=" >>> "
PS1='%F{green}%n%f@%F{magenta}%m%f %F{blue}%B%~%b%f %# '

# Keybindings (Control+Left / Control+Right for word navigation)
bindkey "^[[1;5D" backward-word
bindkey "^[[1;5C" forward-word

# Optional zsh plugins across Debian/Ubuntu apt (/usr/share), Arch (/usr/share/zsh/plugins), and macOS Homebrew (/opt/homebrew/share)
for plugin_dir in /opt/homebrew/share /usr/local/share /usr/share/zsh/plugins /usr/share; do
    if [[ -f "$plugin_dir/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]]; then
        source "$plugin_dir/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
        break
    fi
done

for plugin_dir in /opt/homebrew/share /usr/local/share /usr/share/zsh/plugins /usr/share; do
    if [[ -f "$plugin_dir/zsh-autosuggestions/zsh-autosuggestions.zsh" ]]; then
        source "$plugin_dir/zsh-autosuggestions/zsh-autosuggestions.zsh"
        break
    fi
done
unset plugin_dir

# Load Starship prompt if installed
if command -v starship >/dev/null 2>&1; then
    eval "$(starship init zsh)"
fi

# Load NVM in interactive sessions if installed
export NVM_DIR="$HOME/.nvm"
[[ -s "$NVM_DIR/nvm.sh" ]] && \. "$NVM_DIR/nvm.sh"
[[ -s "$NVM_DIR/bash_completion" ]] && \. "$NVM_DIR/bash_completion"
