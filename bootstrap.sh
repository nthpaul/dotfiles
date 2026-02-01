#!/usr/bin/env bash
set -euo pipefail

DOTFILES_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
OS=$(uname -s)
ARCH=$(uname -m)

log() {
  printf "[bootstrap] %s\n" "$1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1
}

ensure_brew_env() {
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

install_brew() {
  if require_cmd brew; then
    log "Homebrew already installed"
    return
  fi
  if [ "$OS" != "Darwin" ]; then
    log "Homebrew not installed and OS is not macOS. Install your package manager manually."
    return 1
  fi
  log "Installing Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ensure_brew_env
}

install_brew_bundle() {
  ensure_brew_env
  if ! require_cmd brew; then
    log "brew not available; skipping Brewfile"
    return
  fi
  log "Installing packages from Brewfile"
  brew bundle --file "$DOTFILES_DIR/Brewfile"
}

setup_asdf() {
  ensure_brew_env
  if ! require_cmd asdf; then
    log "asdf not found; skipping asdf install"
    return
  fi
  log "Installing asdf plugins"
  asdf plugin add elixir || true
  asdf plugin add erlang || true
  asdf plugin add nodejs || true
  if [ -f "$HOME/.asdf/plugins/nodejs/bin/import-release-team-keyring" ]; then
    log "Importing Node.js release team keyring"
    bash "$HOME/.asdf/plugins/nodejs/bin/import-release-team-keyring" || true
  fi
  log "Installing tool versions from .tool-versions"
  (cd "$DOTFILES_DIR/asdf" && asdf install)
}

install_nvim() {
  if [ "$OS" != "Darwin" ]; then
    log "Skipping Neovim manual install (non-macOS)"
    return
  fi
  if require_cmd nvim; then
    log "Neovim already installed"
    return
  fi
  if [ "$ARCH" = "arm64" ]; then
    NVIM_TAR="nvim-macos-arm64.tar.gz"
    NVIM_DIR="nvim-macos-arm64"
  else
    NVIM_TAR="nvim-macos-x86_64.tar.gz"
    NVIM_DIR="nvim-macos-x86_64"
  fi
  log "Installing Neovim 0.11.6 ($OS $ARCH)"
  mkdir -p "$HOME/symlinked-apps"
  tmp_dir=$(mktemp -d)
  curl -L -o "$tmp_dir/$NVIM_TAR" \
    "https://github.com/neovim/neovim/releases/download/v0.11.6/$NVIM_TAR"
  tar -xzf "$tmp_dir/$NVIM_TAR" -C "$tmp_dir"
  mv "$tmp_dir/$NVIM_DIR" "$HOME/symlinked-apps/nvim-0.11.6"
  mkdir -p "$HOME/.local/bin"
  ln -sf "$HOME/symlinked-apps/nvim-0.11.6/bin/nvim" "$HOME/.local/bin/nvim"
}

install_tpm() {
  local tpm_dir="$HOME/.config/tmux/plugins/tpm"
  if [ -d "$tpm_dir" ]; then
    log "TPM already installed"
    return
  fi
  log "Installing tmux plugin manager (TPM)"
  mkdir -p "$HOME/.config/tmux/plugins"
  git clone https://github.com/tmux-plugins/tpm "$tpm_dir"
}

stow_dotfiles() {
  if ! require_cmd stow; then
    log "stow not found; skipping stow step"
    return
  fi
  log "Stowing dotfiles"
  (cd "$DOTFILES_DIR" && stow -t ~ */)
}

log "Starting bootstrap in $DOTFILES_DIR"

install_brew
install_brew_bundle
setup_asdf
install_nvim
install_tpm
stow_dotfiles

log "Done. Open a new shell, run nvim once to install plugins, and install tmux plugins with prefix + I."
