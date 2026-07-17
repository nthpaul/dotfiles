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
| Name **one coordinator** for multi-pane boards | Peer↔peer freeze/ack theater; quorum by default |

### Board setup (default: one coordinator)

```text
Human: "Faraday coordinates — Curie + Darwin on SPCX FMV"
Faraday → bounded ask each peer once
Peers  → one substance reply each
Faraday → FREEZE once → final report to human
Peers  → silence
```

Quorum voting is **not** the default (extra ceremony). Use only if the human asks; coordinator still tallies and alone reports. Full rules: SKILL.md → **Board protocol**.

### When telld helps vs hurts

- **Helps when one agent owns a slice** — clear owner, clear artifact; peers consult. Failure mode is two agents editing the *same file path*, not just the same idea.
- **Helps for narrow critique/handoff** — bounded `tell X --ask` (e.g. "5 bullets on Y"). Ready-gate is a feature for critique; it hurts when you need an urgent unblock and the critic pane is mid-tool-call.
- **Helps when peers are already live** — prefer tell over Task subagents for panes already on the board; human watching is optional (good for demos, not the rule).
- **Helps for boards with one coordinator** — that pane owns freeze + final report; peers dig once and shut up.
- **Hurts for vibe broadcasts** — hellos, "team complete," stamp-the-stamp, and especially `[status]` ack loops; ceremony crowds out work (see SKILL.md ask vs status).
- **Hurts when nobody owns the next artifact** — open-ended "figure it out together" with no named owner or typed deliverable (path, PR, or decision) turns the board into a chatroom.

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
