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
- fzf
- ripgrep
- fd (optional but useful)
- lazygit
- direnv
- tmux
- zellij (optional)
- yazi (optional)
- bun (optional; zshrc sources it if present)
- nvm + node
- python
- openjdk (if you use Java/Android tooling)
- postgres (if you use the CLI tools in PATH)
- graphite CLI (`gt`) if you use Graphite

Apps (configs in this repo expect them):

- Neovim
- Ghostty
- Cursor
- VS Code
- Zed

After installing, re-run `stow -t ~ */` and open a new shell session.
