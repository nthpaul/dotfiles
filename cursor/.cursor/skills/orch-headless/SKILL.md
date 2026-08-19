---
name: orch-headless
description: >-
  Enter orchestrator mode with a headless default. Use when the user says
  orch-headless, headless orch, fire-and-forget workers, or orchestrate without
  panes. Read the orch skill next. Also apply /poteto-mode. Do not implement —
  spawn grok/cursor with --mode headless and wait on result.json.
---

# orch-headless — you just entered

This pane is the orch. Default mode for this session is **headless**.

```
orch  team=<slug>  default-mode=headless
```

1. Apply /poteto-mode. Read that skill now.
2. Read `~/.cursor/skills/orch/SKILL.md` now and follow it.
3. Stamp the line above once (fill in the team).
4. Every spawn is `--mode headless` unless they ask for a live pane on that one job.
5. Grok or Cursor as the orch skill routes. No tmux. No `orch tell`. Wait on `orch result` / `orch logs`, then `orch kill`.

Do not implement. Do not open panes “so you can watch” unless they switch you to tell.
