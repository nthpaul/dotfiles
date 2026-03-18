---
name: easy-to-consume-code
description: "Write or refactor code so it is extremely easy to consume: optimize for readability, skimmability, explicit control flow, and low cleverness. Use when the user wants code that is easy to read fast."
---

# easy-to-consume-code

## Overview
Bias toward code that a new reader can understand in one pass.

## Workflow

### 1) Optimize for the reader
- Prefer the most obvious implementation that satisfies the requirement.
- Make control flow visible without mental backtracking.
- Choose names that explain intent without extra comments.

### 2) Keep code skimmable
- Prefer short functions with one clear job.
- Use early returns to avoid deep nesting.
- Group related logic together and keep call sites easy to scan.
- Keep branching shallow and conditionals direct.

### 3) Avoid cleverness
- Do not compress logic just to save lines.
- Avoid surprising abstractions, dense chaining, or indirect helper layers.
- Introduce helpers only when they remove repeated complexity for readers.

### 4) Make state easy to follow
- Prefer explicit data flow over mutable shared state.
- Pass the data a function actually needs.
- Keep parameters few and purposeful.

### 5) Validate readability
- Re-read the changed code top to bottom.
- Simplify names, branches, or helpers that slow down comprehension.
- Preserve behavior while improving how quickly the code can be understood.

## Heuristics
- A reader should be able to explain the happy path after one pass.
- Branches should read like plain decisions, not puzzles.
- If a helper makes the caller harder to follow, inline it.
- If a comment is doing too much work, improve the code shape first.

## Output shape
- Favor flat, explicit, readable code.
- Prefer clarity over terseness.
- Prefer maintainable repetition over premature abstraction when the tradeoff is close.
