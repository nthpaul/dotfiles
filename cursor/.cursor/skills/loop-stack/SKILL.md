---
name: loop-stack
description: >-
  Loop until every PR in a Graphite stack has zero unresolved review threads and
  all CI checks are green. Triage with bugbot-review and pr-unresolved-threads,
  fix issues, fix-ci, pr-stack-ship, then advance with gt up (gt bottom at top).
  Use with /loop or invoke as /loop-stack or loop-stack.
---

# Loop stack

Keep a **Graphite PR stack** merge-ready by cycling branches until **every PR** has **zero unresolved threads/comments** and **all CI checks are green**.

Pair with the **loop** skill: `/loop` with no interval (dynamic mode) and this skill's body as the tick prompt.

## Exit condition

Stop looping only when **each PR in the stack** satisfies both:

- Zero unresolved inline review threads and actionable comments
- All required CI checks green (`gh pr checks` — use check link as source of truth)

## Tick workflow

UNTIL each PR on the stack has zero unresolved threads/comments and CI checks are all green,

START_LOOP -> {

You can find unresolved threads and new issues by running `/bugbot-review` and `/pr-unresolved-threads` (first check that it's not yet been solved, and if it has then reply and resolve the thread).

If issues are found, fix them.

After that, `/fix-ci`, and make sure CI is all green, then restack and submit the stack (command: `/pr-stack-ship`) before moving to the next PR up the stack (command: `gt up`).

If you are at the top of the stack, then go back to the bottom of the stack (command: `gt bottom`) and repeat.

}

## Per-tick checklist

1. **Orient** — `gt log short`; note current branch and stack depth.
2. **Triage** — On the **current** branch's PR:
   - Read `pr-unresolved-threads` skill and list open threads.
   - Read `bugbot-review` skill; run review; dedupe against existing threads.
   - For each thread: if already fixed on branch, reply and resolve; else fix in code.
3. **CI** — Read `fix-ci` skill; drive `gh pr checks` to green for current PR.
4. **Ship** — Read `pr-stack-ship` skill; `gt restack` then `gt submit --stack` after local fixes/commits.
5. **Advance** — If current PR is clean: `gt up`. If at stack top: `gt bottom`.
6. **Gate** — If **any** stack PR still has unresolved threads or failing CI, continue loop (do not declare done).

## Loop integration (dynamic)

When invoked via `/loop` without a fixed interval:

1. Run the tick workflow **once immediately**.
2. If exit condition not met, arm a fallback heartbeat (see **loop** skill): lean long when waiting on CI (e.g. 5–10m); shorter when only local triage remains (e.g. 2–3m).
3. Optional: arm a CI watcher (`gh pr checks` poll) that emits wake when state changes from pending → complete.
4. On stop request: kill watcher/heartbeat; do not re-arm.

## Repo defaults

- **trabapro/traba** for `gh` / `pr-unresolved-threads` unless the active repo differs.
- Graphite: `gt restack`, `gt submit --stack`, `gt up`, `gt bottom`, `gt log short`.

## Output each tick

Brief status:

- Current branch / PR number
- Unresolved thread count (this PR + stack summary if useful)
- CI: failing / pending / green
- Actions taken this tick
- Next branch after `gt up` or `gt bottom`

When exit condition is met: say **stack is merge-ready** and list each PR with thread count 0 and CI green.
