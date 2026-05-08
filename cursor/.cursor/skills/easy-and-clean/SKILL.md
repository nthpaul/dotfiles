---
name: easy-and-clean
description: >-
  Shapes branch changes to be minimal, skimmable, and low-state TypeScript/React
  code: discriminated unions, asserts over defensive defaults, few parameters,
  early returns, no cleverness. Use when polishing a PR or when the user asks
  for easy-and-clean, skimmable, or minimal code on their branch.
---

# Easy and clean

When improving code on the user's branch, make the added code **beautiful** by following these rules **verbatim**:

- Write extremely simple code; it should be **skimmable** and you should still be able to understand it.
- **Minimize possible states** by reducing the number of arguments; remove or narrow any state.
- Use **discriminated unions** to reduce the number of states the code can be in.
- **Exhaustively handle** any objects with multiple different types; **fail on unknown type**.
- **Don't write defensive code**; assume the values are always what types tell you they are.
- Use **asserts** when loading data, and always be **highly opinionated** about the parameters you pass around. **Don't let things be optional** if not strictly required.
- **Remove any changes that are not strictly required.**
- **Bias for fewer lines of code.**
- **No complex or clever code.**
- **Don't break out into too many functions** — that's hard to read.
- **Early returns are great.**
- Use **asserts** instead of try/catches or default values when you **do** expect something to exist.
- **Never pass overrides** except strictly necessary; **keep argument count low**.
- **Don't make arguments optional** if they are actually required.

## Application

- Prefer `assert` / narrow checks at boundaries (e.g. after parse/load), then **straight-line** code that trusts types.
- For unions: `switch` on a discriminant with a final branch that `throw`s or `assertNever`s on unknown variants.
- After edits, **delete** optional props, wrappers, and drive-by refactors that the task did not need.
