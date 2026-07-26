---
name: correctness-then-erase
description: >-
  Prioritize correctness first, then erase and simplify so the result stays
  tractable for posterity. Prefer deleting wrappers, dual paths, and rename
  theater over adding structure; allow net LOC only when it closes fail-open
  or real product holes. Use when fixing review findings, hardening authz or
  boundaries, implementing cutovers, or when the user asks for correct-but-minimal,
  erase-first, or posterity-tractable code.
---

# Correctness, then erase

## Priority order (do not reverse)

1. **Correctness** — close fail-open holes, wrong-resource bugs, silent skips,
   cutover gaps, and misattributed deny/monitor signals. Do not ship a “simpler”
   version that still allows the bad path.
2. **Erasure** — delete wrappers, duplicate maps, dead flags, redundant checks,
   and unused branches once behavior is right.
3. **Tractability** — what remains should be obvious to a future reader: one
   structure per concern, few states, no clever indirection.

Net LOC growth is fine when it buys robustness. Growth for ceremony, rename
theater, or parallel books of truth is not.

## When fixing or adding

- Prefer a **one-line stamp / map / parse fix** over a new abstraction.
- Prefer **one shared structure** (options that carry their mutation, one typed
  map with `satisfies`) over index maps + comments or stringly switches.
- Prefer **compile-checked exhaustiveness** (`switch` / `satisfies`) over
  if-chains that fail open when a member is added.
- Prefer **logging unexpected failures** over empty `catch {}`; only soft-fail
  genuine not-found when intentional.
- Prefer **reusing an existing bridge** (flag, allowlist) for cutover holes over
  expanding privilege roles for everyone.
- Mark dual paths as **temporary** in a one-line comment when they must stay.

## Erase by default

Delete when safe:

- Pass-through methods that only call one util
- `'x' in obj` when `obj.x === undefined` already covers absence
- `?? ''` / `?.` where control flow already guarantees a value
- Parallel label/index maps that can collapse into the options themselves
- File renames / suffix churn that do not change the model
- Chatty comments that restate the map or the type

Do **not** erase: handler/guard parse parity, bounded fan-out on bulk authz,
decision context on deny logs, or stamps on stronger sibling mutations.

## Anti-patterns

- Simplifying by dropping a check (“we’ll catch it in the handler”)
- New helper classes / layers for a three-line fix
- Expanding roles globally to paper over three stranded allowlist users
- Keeping two sources of truth without naming one transitional
- Polishing nits while fail-open paths remain

## Relationship to other skills

- **easy-and-clean** — shape for skimmability after (or while) correctness holds
- **minimal-fix** — smallest change for a bug; this skill adds the
  correctness-then-erase ordering for broader hardening / review passes
- **enforcement-boundaries** — authz-specific severity triage; apply this skill
  to *how* those fixes are written
