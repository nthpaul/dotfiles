---
name: orch-tell
description: >-
  Enter orchestrator mode with a live/tell default. Use when the user says
  orch-tell, tell orch, live orch, watch the workers, or orchestrate with
  panes. Read the orch skill next. Do not implement — spawn grok or cursor
  with --mode tell and steer with orch tell.
---

# orch-tell — you just entered

This pane is the orch. Default mode for this session is **tell** (live panes).

```
orch  team=<slug>  default-mode=tell
```

1. Read `~/.cursor/skills/orch/SKILL.md` now and follow it.
2. Stamp the line above once (fill in the team).
3. Every spawn is `--mode tell` unless they ask for a headless job.
4. Grok or Cursor as the orch skill routes. Steer with `orch tell --team T ID --ask "..."`.
5. Kill when the job is done — that unclaims the scientist and drops the window.

Do not implement. The human watches the `orch` tmux session. You only spawn, tell, and kill.
