---
name: code-simplify
description: Simplify code by removing unnecessary abstraction, indirection, and preemptive structure while preserving correctness and repo conventions. Use when the user wants code flattened, fused, inlined, or made easier to understand at first glance.
---

# Code Simplify

Simplify existing code without weakening behavior, typing, or repo standards.

## Workflow

### 1. Load local guidance
1. Open the nearest applicable `AGENTS.md`.
2. Open the repo root `CLAUDE.md` if present.
3. Open the closest relevant `.cursor/BUGBOT.md` or `.cursor/BUGBOT-NITS.md`.
4. Treat `AGENTS.md` as highest priority.

### 2. Identify simplification targets

Look for:

- base types used once
- helper functions used once
- wrappers that only rename or forward data
- abstracted constants or helpers that do not reduce current duplication
- type constructions that are harder to read than the explicit result
- branching that can be made more direct

### 3. Keep the right complexity

Do not simplify away:

- correctness guarantees
- discriminated unions that enforce valid combinations
- explicit domain names that improve readability
- repo-required patterns
- abstractions that already serve multiple real call sites

## Preferred moves

- Inline one-off shared type fragments when the resulting type stays readable.
- Fuse small base types into their only consumer.
- Prefer explicit unions, enums, and named fields over indirection.
- Remove helpers that exist only for hypothetical reuse.
- Prefer direct control flow over layered helpers when behavior is local.

## Decision rule

Choose the simpler version when it:

- preserves type safety
- preserves behavior
- reduces indirection
- is easier to understand on first read

Keep the existing abstraction when removing it would:

- duplicate substantial logic
- hide an important domain concept
- weaken safety
- conflict with repo rules

## Output expectations

- Say what was simplified.
- Say what was intentionally kept and why.
- Keep the patch narrow.
- Rerun the repo-appropriate checks before finishing.
