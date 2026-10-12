# Platforms and tools

Install this directory as `product-plan-html` in the host's user skills root. Keep
`scripts`, `assets`, `references` and `tests` together. All hosts use the same build
commands and input contract.

| Host | User skills root | Project skills root | Installed plugins searched |
| --- | --- | --- | --- |
| Codex | `$CODEX_HOME/skills`, normally `~/.codex/skills` | `.codex/skills` | `$CODEX_HOME/plugins/cache` |
| Cursor | `~/.cursor/skills` and `~/.cursor/skills-cursor` | `.cursor/skills` | `~/.cursor/plugins/cache`, `~/.cursor/plugins/local` |
| Grok | `~/.grok/skills` | `.grok/skills` | `~/.grok/installed-plugins` |
| Claude Code | `~/.claude/skills` | `.claude/skills` | `~/.claude/plugins/cache` |

Discovery prefers an explicit `--skills-root`, then the nearest project roots, then
user roots, then installed plugins. Within each group it prefers the host identified
by the invocation path. Shared directory symlinks are supported. A pstack skill needs
pstack namespace or path provenance; an unrelated skill named `architect` does not qualify.
Cached marketplace source that has not been installed is not a guidance root.

Run `plan.py` through the path shown by the host's loaded skill. The script preserves
that invocation path for host selection, even when the skill directory is a symlink.
The build resolves assets from the package's actual location. `--standalone` ignores
external guidance, but still discovers runtimes and accepts the session tool catalog.

## Browser verification

Pass callable browser tools from the session, rather than inferring access from files
or an installed browser. For example, when those tools are actually exposed:

```bash
python3 <skill-dir>/scripts/plan.py --tools mcp__cua_repl__js detect
python3 <skill-dir>/scripts/plan.py --tools mcp__playwright__browser_navigate detect
```

CUA is optional. Use the user-requested browser first. Otherwise prefer Codex's in-app
browser when available, then the host's browser tools. Read the actual tool's instructions
before using it. For hosts without a browser tool, inspect the project for an existing
permitted Playwright/CDP harness. Grok's installed `control-ui` skill is one such workflow
when present; it is not an invented tool API or a package requirement. If no browser
path is available, deliver the built document and state that visual QA has not run.

## Runtime and publication

Use the host's shell/file tools to run bundled Python and Node helpers. Discovery checks
PATH and locally installed Codex runtimes; it does not install dependencies. The Codex
desktop dependency-loader is an optional way to locate a runtime when exposed. Other
hosts can pass an existing Node executable with `build --node <path>`.

Relay publication uses the `relay` executable discovered on PATH or `~/.relay/bin/relay`.
It needs an authenticated Relay installation and an explicit publication request.
Local generation and verification work without Relay.
