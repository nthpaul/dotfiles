---
name: agent-tell
description: >-
  Collaborate with other visible Cursor agent panes via scientist names using
  the `tell` CLI. Use when peer agents are running in tmux panes, when the user
  wants agents to message each other instead of Task subagents, or when
  claiming/listing scientist identities for panes. Includes anti-loop protocol
  (ask vs status, hush, no idle-ack ping-pong).
---

# Agent Tell

Visible Cursor `agent` panes on one tmux screen, each with a scientist name.
Peers message each other through a **queued inbox**; **telld** auto-injects
each message as a real user turn when the target pane is Ready.

Prefer this over Task subagents when peers are already live and the human
wants to watch the team.

**Docs:** architecture and usage guide — [README.md](README.md).

**Motto:** *sic itur ad astra* — ship the work; do not orbit in ceremony.

## Mental model

```
tell curie "[ask] find X"  →  inbox file  →  telld waits for Curie Ready
                           →  injects as user message:
                                 [from newton]
                                 [ask] find X
                           →  Curie does the work / replies with substance
```

You do **not** run `tell inbox` in the happy path. If you see `[from <name>]`
in a user message, that *is* the peer message — answer it **only if it asks**.

## Setup (once per pane)

```bash
tell claim              # next free scientist (starts telld)
tell claim newton       # specific name
tell list               # roster + telld + hush + pending
tell daemon status
```

Borders show `@scientist` names (see tmux.conf).

## Send

```bash
tell curie "[ask] critique this method section in 5 bullets"
tell curie --ask "critique this method section in 5 bullets"
tell curie --status "idle"          # FYI only — peers must NOT reply
tell curie -                        # multiline from stdin
tell hush                           # hush all (status drops; work still delivers)
tell hush clear                     # lift hush
```

Returns immediately after queueing. telld delivers.

## Ask vs status (mandatory)

| Kind | How to send | Peer reply? |
|------|-------------|-------------|
| **Work / ask** | `[ask] …` or `tell name --ask "…"` or a clear task/question | Yes — do the work |
| **Status** | `[status] …` or `tell name --status "…"` | **Never** |

**Status** includes: idle, standing by/down, stamped, frozen, “no contact”,
“ack …” with no new ask, board-complete restatements, thank-you with no ask.

**If the message has no ask → do not `tell` back.** Work in your pane or stay quiet.

### Freeze / stamp ceremony

1. One coordinator (or the human) may declare freeze **once**.
2. Peers may send **one** final evidence payload (ROOT CAUSE, REPRO table, FIX).
3. After freeze is acknowledged by the coordinator/human: **silence**.
4. Do **not** stamp the stamp. Do **not** ack idle. Do **not** restate the writeup.

### Hush

When you see a HARD STOP / hush order, or `tell list` shows hush:

- Stop all status tells immediately.
- Do not ack the hush message.
- Resume status only after `tell hush clear` or the human asks.

telld **drops status-like mail** while hush is on (archives without injecting).
Work/ask still delivers. Repeated status from the same sender is **coalesced**
(dropped) even without hush.

## When you receive `[from <name>] …`

1. Classify: ask/work vs status (see above).
2. **Status → no `tell` reply.** Optionally note locally; do not ping.
3. **Ask →** do the work; reply with substance (`--ask` or `[ask]`).
4. Do **not** re-broadcast hellos or “team complete” loops.

## Manual / debug

```bash
tell inbox              # drain files to stdout (skips telld delivery)
tell hush | tell hush clear | tell hush newton
tell daemon start|stop|restart|status
tail -f ~/.cursor/scientists/telld.log
```

## Rules

1. `tell list` before addressing peers.
2. Use `tell <name>` for live panes — not Task subagents.
3. Keep messages short and actionable. Prefer `--ask` / `--status`.
4. `tell claim` at session start if unset.
5. **No ping-pong.** No idle-ack orbits. *Sic itur ad astra.*

## Paths

- Names: [names.txt](names.txt)
- Roster: `~/.cursor/scientists/roster.json`
- Hush: `~/.cursor/scientists/hush.json`
- Inbox: `~/.cursor/scientists/inbox/<name>/`
- Daemon log: `~/.cursor/scientists/telld.log`
- Script: [scripts/tell](scripts/tell) (also `telld`)
