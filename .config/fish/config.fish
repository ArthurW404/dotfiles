# ~/.config/fish/config.fish
# Cross-platform (Linux native apt/pacman/dnf & macOS Homebrew) PATH & environment configuration
# Top-level runs in both interactive and non-interactive shells

# macOS Homebrew (or optional Linuxbrew if installed)
if test -d /opt/homebrew
    set -gx HOMEBREW_PREFIX "/opt/homebrew"
    set -gx HOMEBREW_CELLAR "/opt/homebrew/Cellar"
    set -gx HOMEBREW_REPOSITORY "/opt/homebrew"
else if test -d /usr/local/Homebrew
    set -gx HOMEBREW_PREFIX "/usr/local"
    set -gx HOMEBREW_CELLAR "/usr/local/Cellar"
    set -gx HOMEBREW_REPOSITORY "/usr/local/Homebrew"
else if test -d /home/linuxbrew/.linuxbrew
    set -gx HOMEBREW_PREFIX "/home/linuxbrew/.linuxbrew"
    set -gx HOMEBREW_CELLAR "/home/linuxbrew/.linuxbrew/Cellar"
    set -gx HOMEBREW_REPOSITORY "/home/linuxbrew/.linuxbrew/Homebrew"
end

# OS-specific PNPM_HOME
switch (uname -s)
    case Darwin
        set -gx PNPM_HOME "$HOME/Library/pnpm"
    case '*'
        if set -q XDG_DATA_HOME
            set -gx PNPM_HOME "$XDG_DATA_HOME/pnpm"
        else
            set -gx PNPM_HOME "$HOME/.local/share/pnpm"
        end
end

# Core tool paths (fish_add_path automatically skips non-existent directories)
if set -q HOMEBREW_PREFIX
    fish_add_path -g "$HOMEBREW_PREFIX/bin" "$HOMEBREW_PREFIX/sbin"
end

fish_add_path -g \
    "$HOME/.local/bin" \
    "$HOME/.cargo/bin" \
    "$PNPM_HOME" \
    "$HOME/.gemini/antigravity/bin" \
    "$HOME/Library/Application Support/Antigravity/bin" \
    "$HOME/.config/Antigravity/bin" \
    /snap/bin

# Editor & CLI environment
if command -sq nvim
    set -gx EDITOR nvim
else
    set -gx EDITOR vim
end
set -gx VISUAL "$EDITOR"
if test -f "$HOME/.config/ripgrep/rc"
    set -gx RIPGREP_CONFIG_PATH "$HOME/.config/ripgrep/rc"
end

# Interactive shell configuration only
if status is-interactive
    # Suppress default welcome message
    set -g fish_greeting

    # Interactive Abbreviations (expand inline in history)
    # Git
    abbr -a g git
    abbr -a gst git status -sb
    abbr -a gd git diff
    abbr -a gds git diff --staged
    abbr -a gco git checkout
    abbr -a gcb git checkout -b
    abbr -a gl 'git log --oneline --graph --decorate -n 20'

    # Editor
    abbr -a v "$EDITOR"
    abbr -a vi "$EDITOR"

    # Python / uv
    abbr -a uvr uv run
    abbr -a uvp uv run pytest
    abbr -a ruffc uvx ruff check .
    abbr -a rufff uvx ruff format .

    # Directory listing (eza if installed, otherwise native ls)
    if command -sq eza
        alias ls='eza --group-directories-first'
        alias ll='eza -lah --git --group-directories-first'
        alias lt='eza --tree --level=2'
    else
        switch (uname -s)
            case Darwin
                set -gx CLICOLOR 1
                alias ls='ls -G'
                alias ll='ls -lahG'
                alias la='ls -AG'
                alias l='ls -CFG'
            case '*'
                alias ls='ls --color=auto'
                alias ll='ls -lah --color=auto'
                alias la='ls -A --color=auto'
                alias l='ls -CF --color=auto'
        end
    end

    # Debian/Ubuntu apt binary name compatibility (fdfind -> fd, batcat -> bat)
    if not command -sq fd; and command -sq fdfind
        alias fd='fdfind'
    end
    if not command -sq bat; and command -sq batcat
        alias bat='batcat'
    end

    # Colored grep
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'

    # fzf integration
    if command -sq fzf
        fzf --fish | source
        if command -sq fd
            set -gx FZF_DEFAULT_COMMAND 'fd --type f --strip-cwd-prefix --hidden --exclude .git'
            set -gx FZF_CTRL_T_COMMAND "$FZF_DEFAULT_COMMAND"
        else if command -sq fdfind
            set -gx FZF_DEFAULT_COMMAND 'fdfind --type f --strip-cwd-prefix --hidden --exclude .git'
            set -gx FZF_CTRL_T_COMMAND "$FZF_DEFAULT_COMMAND"
        end
    end

    # zoxide (smarter cd)
    if command -sq zoxide
        zoxide init fish | source
    end

    # direnv
    if command -sq direnv
        direnv hook fish | source
    end

    # Starship prompt or clean built-in prompt fallback
    if command -sq starship
        starship init fish | source
    else
        function fish_prompt
            set -l last_status $status
            set -l stat_color (set_color green)
            if test $last_status -ne 0
                set stat_color (set_color red)
            end

            set -l user_color (set_color cyan)
            set -l host_color (set_color magenta)
            set -l cwd_color (set_color blue --bold)
            set -l normal (set_color normal)

            echo -n -s $user_color $USER $normal "@" $host_color (prompt_hostname) " " $cwd_color (prompt_pwd) $normal
            if type -q fish_git_prompt
                echo -n -s (fish_git_prompt)
            end
            echo -n -s " " $stat_color "❯" $normal " "
        end
    end
end
