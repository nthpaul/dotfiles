. $HOME/.asdf/asdf.sh

alias vim='nvim'

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

export KERL_CONFIGURE_OPTIONS="--with-ssl=/opt/homebrew/opt/openssl@1.1 \
                               --with-wx-config=/opt/homebrew/opt/wxmac/bin/wx-config \
                               --without-javac"
export CPPFLAGS="-I/opt/homebrew/opt/openssl@1.1/include -I/opt/homebrew/opt/unixodbc/include"
export LDFLAGS="-L/opt/homebrew/opt/openssl@1.1/lib -L/opt/homebrew/opt/unixodbc/lib"

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

# RUBY
# By default, binaries installed by gem will be placed into:
export PATH="$HOME/.asdf/installs/ruby/3.3.0/bin:$PATH"

# PSQL
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/paul/google-cloud-sdk/path.zsh.inc' ]; then . '/Users/paul/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/Users/paul/google-cloud-sdk/completion.zsh.inc' ]; then . '/Users/paul/google-cloud-sdk/completion.zsh.inc'; fi
