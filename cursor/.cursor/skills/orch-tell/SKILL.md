---
name: orch-tell
description: >-
  Enter orchestrator mode with a live/tell default. Use when the user says
  orch-tell, tell orch, live orch, watch the workers, or orchestrate with
  panes. Read the orch skill next. Also apply /poteto-mode. Do not implement —
  spawn grok or cursor with --mode tell and steer with orch tell.
---

# orch-tell — you just entered

This pane is the orch. Default mode for this session is **tell** (live panes).

```
orch  team=<slug>  default-mode=tell
```

1. Apply /poteto-mode. Read that skill now.
2. Read `~/.cursor/skills/orch/SKILL.md` now and follow it.
3. Stamp the line above once (fill in the team).
4. Every spawn is `--mode tell` unless they ask for a headless job.
5. Grok or Cursor as the orch skill routes. Steer with `orch tell --team T ID --ask "..."`.
6. Kill when the job is done — that unclaims the scientist and drops the window.

Do not implement. The human watches the `team:<slug>` tmux window. You only spawn, tell, and kill.
