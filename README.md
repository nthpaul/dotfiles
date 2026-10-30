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
- Editors: `nvim/`, `zed/`, `cursor/` (includes [agent-tell](cursor/.cursor/skills/agent-tell/) lab for tmux Cursor agents), `vscode/`
- Terminal/tools: `tmux/`, `ghostty/`, `direnv/`, `yazi/`, `zellij/`
- macOS: `hammerspoon/`
- Dev tools: `asdf/`, `graphite/`, `opencode/`, `github-copilot/`
- Git/GitHub: `git/` (.gitconfig, global gitignore), `gh/` (CLI config; `hosts.yml` stays local)
- Shared agent instructions: `home/AGENTS.md` is linked to `~/AGENTS.md`. Claude's `CLAUDE.md` imports it. The Codex entry file and the always-applied Cursor rule `shared-instructions.mdc` instruct agents to read it at task startup, with a fallback to the dotfiles source if the home link is missing. It also holds the voice and documentation rules that used to be separate Cursor rules. Grok loads `~/.grok/AGENTS.md` as its global rules, so `grok/.grok/AGENTS.md` is a symlink to the shared file.
- Codex: `codex/` (`config.toml`, `AGENTS.md`, `rules/`, `skills/`, `plans/`, a Pele browser preview hook, and the [local orchestrator](codex/.codex/orchestrator/README.md) exposed as `codex-orch`; auth, sessions, sqlite, and caches stay local)
- Claude Code: `claude/` (`CLAUDE.md`, `settings.json`, and the `hooks/mermaid-preview` Stop hook, which renders the Mermaid diagrams in each reply to a background browser tab; `skills/` symlinked to `codex/.codex/skills`)
- Grok: `grok/` (`config.toml`, `skills/`; auth, sessions, MCP credentials, and caches stay local)

Codex's `Stop` hook calls `codex-pele`, which reuses Claude's existing Pele renderer
and opens diagrams in a background browser tab. Codex previews live in
`~/.codex/mermaid-preview/` (or `$CODEX_HOME/mermaid-preview/`). Its native terminal
Mermaid renderer is disabled; other text formatting remains enabled. Review and
trust the hook through Codex's `/hooks` menu after stowing `codex`. Set
`MERMAID_PREVIEW=0` when starting Codex to disable browser previews.

The [product-plan-html skill](codex/.codex/skills/product-plan-html/SKILL.md) is shared
by Codex, Claude Code, Cursor and Grok. Claude uses the shared skills directory;
Cursor and Grok link this skill to the canonical Codex folder. Its discovery command
selects available pstack, Traba and Relay guidance, with bundled fallbacks.

The [Anatomy skill](codex/.codex/skills/anatomy/SKILL.md) uses the same shared
layout for Codex, Claude Code, Cursor and Grok. It includes the drawing kit,
verification scripts and eight complete examples from
[wheresryan22/anatomy](https://github.com/wheresryan22/anatomy/tree/454a0ef801b6d9b905f08309d094491c7085b3dd),
vendored at commit `454a0ef801b6d9b905f08309d094491c7085b3dd` under the MIT license.
Invoke it as `$anatomy` in Codex or `/anatomy` in Claude Code, Cursor and Grok.

The [pstack bundle](codex/.local/share/cursor-pstack/README.md) is vendored at
commit `4dd1d05818d19792e7cd6e818f1667f95f7e1dbe` under the MIT license.
Stowing `codex` installs its 58 skills through relative links, including
`$pstack:poteto-mode`. The [Codex adapter](codex/.local/share/cursor-pstack/docs/harness/codex.md)
maps Cursor tool names to Codex and defaults helpers to the parent model.

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
| Vertical thirds | `Ctrl+Alt` + `D` `F` `G` |
| Horizontal thirds | `Ctrl+Alt` + `M` (top) `N` (bottom) |
| Two-thirds | `Ctrl+Alt` + `T` (left) `Y` (right) `L` (bottom) |
| Vertical fourths | `Ctrl+Alt` + `Z` `X` `C` `V` |
| Right three-fourths | `Ctrl+Alt` + `B` |
| 2×3 middle / bottom | `Ctrl+Alt` + `Q` `W` (middle) `E` `R` (bottom) |
| Center (keep size) | `Ctrl+Alt` + `Space` |
| Save layout | `Ctrl+Alt` + `S` |
| Restore layout | `Ctrl+Alt` + `Backspace` |

Saved profiles live in `~/.hammerspoon/window-layouts/` (gitignored). Snapped windows use an **8px** gap from screen edges and between tiles.
