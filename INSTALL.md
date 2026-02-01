# Install Notes

This repo is managed with GNU Stow. Each top-level folder is a package that mirrors the target path under $HOME.

## Quick setup

```
cd ~/.dotfiles
stow -t ~ */
```

## Neovim (0.11.6 stable)

This setup expects a manual install into `~/symlinked-apps` plus a user-level symlink in `~/.local/bin`.

```
mkdir -p ~/symlinked-apps
curl -L -o /tmp/nvim-macos-arm64.tar.gz \
  https://github.com/neovim/neovim/releases/download/v0.11.6/nvim-macos-arm64.tar.gz
tar -xzf /tmp/nvim-macos-arm64.tar.gz -C /tmp
mv /tmp/nvim-macos-arm64 ~/symlinked-apps/nvim-0.11.6
ln -sf ~/symlinked-apps/nvim-0.11.6/bin/nvim ~/.local/bin/nvim
```

Optional system-level symlink:

```
sudo ln -sf ~/symlinked-apps/nvim-0.11.6/bin/nvim /usr/local/bin/nvim
```

Verify:

```
nvim --version
```

## Tools and apps to install

Install these with your preferred installer (brew/asdf/mise/manual). They’re referenced by shell config or Neovim plugins.

CLI tools:

- stow
- git
- curl, tar, unzip
- coreutils (provides `gls` used by alias)
- fzf
- ripgrep
- fd (optional but useful)
- lazygit
- direnv
- tmux
- tmux plugin manager (TPM): `git clone https://github.com/tmux-plugins/tpm ~/.config/tmux/plugins/tpm`
- zellij (optional)
- yazi (optional)
- bun (optional; zshrc sources it if present)
- asdf (recommended; see .tool-versions)
- nvm + node (optional; if you skip asdf)
- python
- openjdk (if you use Java/Android tooling)
- zulu-17 (JAVA_HOME in .zshrc points to Zulu 17)
- postgres (zshrc uses postgresql@17 path)
- openssl@1.1, wxmac, unixodbc (needed for Erlang builds / kerl)
- google-cloud-sdk (zshrc loads gcloud paths if present)
- conda (optional; zshrc initializes if present)
- xclip (Linux only; used by tmux copy mode) or adjust to pbcopy on macOS
- graphite CLI (`gt`) if you use Graphite

Apps (configs in this repo expect them):

- Neovim
- Ghostty
- Cursor
- VS Code
- Zed

Fonts:

- Hack Nerd Font Mono (Ghostty config uses it)

After installing, re-run `stow -t ~ */` and open a new shell session.

## Asdf setup (recommended)

This repo includes `.tool-versions` under `asdf/`. Install asdf, then:

```
asdf plugin add elixir
asdf plugin add erlang
asdf plugin add nodejs
asdf install
```

If you prefer nvm, skip asdf and install Node manually, but note the pinned version in `.tool-versions`.

## Automation sketch (high level)

Goal: make a fresh laptop setup repeatable with one command.

1) Bootstrap script (e.g. `bootstrap.sh`) that:
- Installs Homebrew (macOS) or your package manager (Linux).
- Installs core CLI tools, fonts, and apps (via brew bundle, apt, or pacman).
- Installs asdf + plugins, runs `asdf install`.
- Installs Neovim and sets the symlink in `~/.local/bin`.
- Clones TPM for tmux.
- Stows dotfiles.

2) Package list:
- A Brewfile (macOS) or apt/pacman list (Linux) for all tools above.
- Optional: a fonts installer step for Nerd Font.

3) Finalizer:
- Open a new shell, run `nvim` once to install plugins.
- Run tmux and install plugins via TPM (prefix + I).

Sketch of a bootstrap script:

```
#!/usr/bin/env bash
set -euo pipefail

# 1) Install package manager + tools
# 2) Install fonts
# 3) Install asdf + plugins + versions
# 4) Install Neovim and symlink
# 5) Clone TPM
# 6) Stow dotfiles
```
