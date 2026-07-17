# Agent Tell

A tiny lab for **Cursor `agent` panes in tmux**: each pane claims a scientist name, and `tell` queues messages that **telld** injects as real user turns. You watch the team on one screen instead of burying peers in Task subagents.

Needs: macOS/Linux, `tmux`, Python 3, [Cursor CLI](https://cursor.com) (`agent` / `cursor-agent`).

## Install (this repo)

From a machine with these dotfiles:

```bash
cd ~/.dotfiles
git pull
stow -t ~ cursor tmux zsh
tmux source-file ~/.config/tmux/tmux.conf   # or open a new tmux session
exec zsh -l                                 # pick up PATH
which tell                                  # -> …/skills/agent-tell/scripts/tell
```

Runtime state (roster, inboxes, daemon log) lives under `~/.cursor/scientists/` and is **not** in git. It appears on first `tell claim`.

## Up and running

```bash
# One tmux window, a few panes
tmux split-window -h && tmux split-window -v

# In each pane
agent
tell claim              # next free name; starts telld
# or: tell claim newton

tell list               # who’s who
tell curie --ask "critique this method in 5 bullets"
```

The other pane gets a normal user message:

```text
[from newton]
[ask] critique this method in 5 bullets
```

That’s it. No manual inbox ritual.

## Habits that keep the lab sane

| Do | Don’t |
|----|--------|
| `tell name --ask "…"` for real work | Reply to idle / “standing by” / stamp spam |
| `tell name --status "…"` for FYI (peers should ignore) | Ack loops after a freeze |
| `tell hush` when ceremony starts looping | Smash keys into a Busy pane (telld waits for Ready) |

Agents should load [SKILL.md](SKILL.md) (Cursor skill: `agent-tell`).

## Commands (cheat sheet)

```text
tell claim [name]     tell unclaim [name]     tell list
tell <name> --ask "…" tell <name> --status "…"
tell hush | tell hush clear | tell hush status
tell daemon status|start|stop|restart
```

## Layout

```text
dotfiles  cursor/.cursor/skills/agent-tell/   # this package (stowed → ~/.cursor/skills/…)
runtime   ~/.cursor/scientists/               # roster, hush, inbox/, telld.pid
tmux      pane option @scientist on the border
```

---

*Sic itur ad astra.* Ship the work; don’t orbit in ceremony.
