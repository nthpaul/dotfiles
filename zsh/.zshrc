# ALIASES
alias vim='nvim'
alias lzg='lazygit'

alias ls='gls -lahps --author --group-directories-first --color=auto'
# export PATH="/Users/ple/.local/bin:$PATH"
export PATH="/Users/ple/.local/bin:$PATH"
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# export KERL_CONFIGURE_OPTIONS="--with-ssl=/opt/homebrew/opt/openssl@1.1 \
#                                --with-wx-config=/opt/homebrew/opt/wxmac@3.1/bin/wx-config \
#                                --without-javac"

# export KERL_CONFIGURE_OPTIONS="--with-ssl=$(brew --prefix openssl)"
# export CPPFLAGS="-I$(brew --prefix openssl)/include"
# export LDFLAGS="-L$(brew --prefix openssl)/lib"

export HISTSIZE=10000
export SAVEHIST=10000
export HISTFILE=~/.zhist
setopt INC_APPEND_HISTORY
setopt EXTENDED_HISTORY

if command -v brew >/dev/null 2>&1; then
  OPENSSL_PREFIX="$(brew --prefix openssl@3 2>/dev/null || brew --prefix openssl@1.1 2>/dev/null)"
  WX_PREFIX="$(brew --prefix wxwidgets 2>/dev/null || brew --prefix wxmac 2>/dev/null)"
  ODBC_PREFIX="$(brew --prefix unixodbc 2>/dev/null)"
  if [ -n "$OPENSSL_PREFIX" ]; then
    export CPPFLAGS="-I$OPENSSL_PREFIX/include"
    export LDFLAGS="-L$OPENSSL_PREFIX/lib"
  fi
  if [ -n "$ODBC_PREFIX" ]; then
    export CPPFLAGS="$CPPFLAGS -I$ODBC_PREFIX/include"
    export LDFLAGS="$LDFLAGS -L$ODBC_PREFIX/lib"
  fi
  if [ -n "$OPENSSL_PREFIX" ] && [ -n "$WX_PREFIX" ]; then
    export KERL_CONFIGURE_OPTIONS="--with-ssl=$OPENSSL_PREFIX --with-wx-config=$WX_PREFIX/bin/wx-config --without-javac"
  fi
fi

eval "$(direnv hook zsh)"

# ADD GIT BRANCH INFORMATION TO YOUR ZSH PROMPT
# Load version control information
autoload -Uz vcs_info
precmd() { vcs_info }

# # Set up the prompt (with git branch name)
setopt PROMPT_SUBST

# Regex to match git branch in prompt
zstyle ':vcs_info:git:*' formats '%b'

# Set the prompt
PROMPT='%{$fg_bold[green]%}%n@%{$reset_color%}%{$fg_bold[blue]%}%~%{$reset_color%}%{$reset_color%} $ '
RPROMPT=\$vcs_info_msg_0_

# ASDF
# . "$HOME/.asdf/asdf.sh"

# PSQL
if command -v brew >/dev/null 2>&1; then
  PG_PREFIX="$(brew --prefix postgresql@17 2>/dev/null)"
  if [ -n "$PG_PREFIX" ]; then
    export PATH="$PG_PREFIX/bin:$PATH"
    export LDFLAGS="$LDFLAGS -L$PG_PREFIX/lib"
    export CPPFLAGS="$CPPFLAGS -I$PG_PREFIX/include"
  fi
fi

# POSTGRES export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
# bun completions
[ -s "/Users/ple/.bun/_bun" ] && source "/Users/ple/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# CONDA
# export PATH="$HOME/anaconda3/bin:$PATH"  # commented out by conda initialize
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/opt/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/opt/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/opt/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

# Set up fzf bindings and fuzzy completion
source <(fzf --zsh)

# Load .env
if [ -f "$HOME/.env" ]; then
    # export $(cat "$HOME/.env" | xargs)
fi

# . $(brew --prefix asdf)/libexec/asdf.sh

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/ple/google-cloud-sdk/path.zsh.inc' ]; then . '/Users/ple/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/Users/ple/google-cloud-sdk/completion.zsh.inc' ]; then . '/Users/ple/google-cloud-sdk/completion.zsh.inc'; fi

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# JAVA
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"

# ANDROID SDK
export JAVA_HOME=/Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home

# # Added by Antigravity
# export PATH="/Users/ple/.antigravity/antigravity/bin:$PATH"

# # OpenClaw Completion
# source <(openclaw completion --shell zsh)
