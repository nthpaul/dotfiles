---
name: pr-stack-ship
description: >-
  After local commits on a Graphite stack: restack branches and push/update the
  whole stack with gt (not plain git push alone). Use when finishing work on
  stacked branches like pl/… → feat/…. Invoke as /pr-stack-ship or pr-stack-ship.
---

# PR stack ship (Graphite)

Use when **commits are done locally** and you need to **push the stack** so parent + child PRs stay aligned.

## Steps

1. **Confirm clean commits** — `git status`; commit anything that should ship (specific `git add`, not blind `-A` unless intentional).

2. **Restack** — rebases stacked children onto their parents:

```bash
gt restack
```

Fix conflicts if prompted, then `gt continue` (or follow Graphite's instructions).

3. **Submit the stack** — pushes all branches in the stack and updates PRs:

```bash
gt submit --stack
```

If Graphite reports **remote drift** / "updated outside of Graphite", sync or override:

```bash
gt sync
# or, when you intend to overwrite remote with your local stack:
gt submit --stack --force
```

4. **Sanity check** — Graphite prints PR links; optional: `git status -sb` shows branch tracking `origin/…`.

## Notes

- **Parent branch "No-op"** on submit means that branch had nothing new to push; **child** branches may still update.
- **oxfmt** may run on changed TS files during submit — fix format locally if it fails.

## Quality gates

Run targeted lint, typecheck, format checks, and tests **before** you commit when the change warrants it (follow repo scripts and team norms). This skill only covers **restack + stack submit**, not validation.
