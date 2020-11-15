# my zshrc config

export PATH="$PATH:/usr/share:/home/arthur/.local/bin"

# Lines configured by zsh-newuser-install
HISTFILE=~/.histfile
HISTSIZE=5000
SAVEHIST=5000

# End of lines configured by zsh-newuser-install
# The following lines were added by compinstall
zstyle :compinstall filename '/home/arthur/.zshrc'

autoload -Uz compinit
compinit
# End of lines added by compinstall

# Adding autocompletion with an arrow-key driven interface 
zstyle ':completion:*' menu select


# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac


# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias dir='dir --color=auto'
    alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

alias ll='ls -al'

# make additional lines in shell prompt look like this
PS2=" >>> "

PS1='%F{green}%n%f@%F{magenta}%m%f %F{blue}%B%~%b%f %# '


# Adding Fish-like syntax highlighting and autosuggestions
if cat /etc/*-release | grep -q "Arch Linux" 
then
    ## arch linux
    source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
    source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
else if  cat /etc/*-release | grep -q "Debian"
    ## debian
    source  "`whereis zsh-syntax-highlighting | cut -d' ' -f2`/zsh-syntax-highlighting.zsh"
    source  "`whereis zsh-autosuggestions | cut -d' ' -f2`/zsh-autosuggestions.zsh"
fi
