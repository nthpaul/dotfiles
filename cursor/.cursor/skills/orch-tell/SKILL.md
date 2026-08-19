---
name: orch-tell
description: >-
  Enter orchestrator mode with a live/tell default. Use when the user says
  orch-tell, tell orch, live orch, watch the workers, or orchestrate with
  panes. Read the orch skill next. Do not implement — spawn cursor --mode tell
  and steer with orch tell. Grok stays headless (Grok tell is not v1).
---

# orch-tell — you just entered

This pane is the orch. Default mode for this session is **tell** (live panes).

```
orch  team=<slug>  default-mode=tell
```

1. Read `~/.cursor/skills/orch/SKILL.md` now and follow it.
2. Stamp the line above once (fill in the team).
3. Cursor workers: `orch spawn --team T --mode tell cursor JOB`. Steer with `orch tell --team T ID --ask "..."`.
4. Grok workers stay `--mode headless`. Do not spawn `tell grok`.
5. Kill when the job is done — that unclaims the scientist and drops the window.

Do not implement. The human watches the `orch` tmux session. You only spawn, tell, and kill.
