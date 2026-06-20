# Dotfiles

Personal dotfiles managed with GNU Stow. Each top-level folder is a Stow package that mirrors the target path under $HOME.

## Quick setup

From a fresh laptop:

```
cd ~/.dotfiles
stow -t ~ */
```

That single command links every package into your home directory.

## How it works

Each package mirrors the desired path under $HOME. Example:

- Source: `~/.dotfiles/nvim/.config/nvim/init.lua`
- Link created by stow: `~/.config/nvim/init.lua -> ~/.dotfiles/nvim/.config/nvim/init.lua`

Stow creates relative symlinks so the repo stays portable across machines.

## Packages (high level)

- Shell: `zsh/` (.zshrc, .zprofile, .zshenv)
- Editors: `nvim/`, `zed/`, `cursor/`, `vscode/`
- Terminal/tools: `tmux/`, `ghostty/`, `direnv/`, `yazi/`, `zellij/`
- macOS: `hammerspoon/`
- Dev tools: `asdf/`, `graphite/`, `opencode/`, `github-copilot/`, `codex/`
- Git/GitHub: `git/` (.gitconfig, global gitignore), `gh/` (CLI config; `hosts.yml` stays local)
- Claude Code: `claude/` (`settings.json`; `skills/` symlinked to `codex/.codex/skills`)

## Adding new configs

1. Create a new package folder at repo root.
2. Mirror the target path under $HOME inside that package.
3. Move the config files into the package.
4. Run `stow -t ~ <package>`.

## Troubleshooting

- If stow reports a conflict, remove or move the existing target file, then re-run stow.
- Use `stow -n -t ~ */` for a dry run.
- Use `stow -D -t ~ <package>` to remove a package's links.

## Hammerspoon (window snapping + layouts)

Managed via `hammerspoon/` with [AutoArrange.spoon](https://github.com/jamesagarside/hammerspoon-auto-arrange).

1. Install: `brew install --cask hammerspoon`
2. Grant **Accessibility** in System Settings → Privacy & Security → Accessibility.
3. Reload: Hammerspoon menubar → Reload Config (or restart the app).

Default snap modifier: **Ctrl + Alt** (change via menubar **WL** → Configuration).

| Action | Keys |
|--------|------|
| Left / right half | `Ctrl+Alt` + `←` / `→` |
| Top / bottom half | `Ctrl+Alt` + `↑` / `↓` |
| Corners | `Ctrl+Alt` + `U` `I` `J` `K` |
| Thirds | `Ctrl+Alt` + `D` `F` `G` |
| Center | `Ctrl+Alt` + `C` |
| Save layout | `Ctrl+Alt` + `S` |
| Restore layout | `Ctrl+Alt` + `R` or `Backspace` |

Saved profiles live in `~/.hammerspoon/window-layouts/` (gitignored). Snapped windows use an **8px** gap from screen edges and between tiles.
