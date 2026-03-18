---
name: clean-simple-code
description: "Run a focused cleanup pass that makes code clean and simple: remove unnecessary code, reduce possible states, tighten types, eliminate fake optionality, and keep only real extension points."
---

# clean-simple-code

## Overview
Treat cleanup as a dedicated pass whose goal is simpler code, not more features.

## Workflow

### 1) Remove what is not needed
- Delete dead code, unused branches, stale helpers, and redundant indirection.
- Remove code that exists only for hypothetical flexibility.
- Inline one-off abstractions that hide straightforward behavior.

### 2) Reduce possible states
- Prefer fewer states over more generic code.
- Use discriminated unions or narrower types when they make invalid states impossible.
- Collapse overlapping flags or parameters into one clear model.

### 3) Tighten APIs
- Remove optionality that is not truly optional.
- Do not pass override parameters unless there is a real, current need.
- Require inputs that are always required in practice.

### 4) Keep behavior obvious
- Prefer direct code paths over configurable plumbing.
- Eliminate special cases that can be modeled away.
- Avoid keeping parallel sources of truth when one derived value will do.

### 5) Verify the cleanup
- Confirm behavior is preserved.
- Update tests when the public surface or reachable branches change.
- Re-read for anything that still feels generic, defensive, or overbuilt.

## Heuristics
- Every parameter should earn its existence.
- Every branch should represent a real case.
- Every state should be reachable and meaningful.
- If flexibility is not being used, remove it.

## Output shape
- Smaller surface area.
- Fewer possible states.
- Fewer escape hatches and override knobs.
- Cleaner code with less to read and less to reason about.
