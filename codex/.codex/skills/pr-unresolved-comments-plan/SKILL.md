---
name: pr-unresolved-comments-plan
description: "Pull unresolved PR review comments, including full verbatim comment text and code-location context, propose response suggestions in both business-logic and code terms, and pause for explicit user approval before implementation. Use when the user asks to review unresolved comments and decide what to implement first."
---

# pr-unresolved-comments-plan

## Workflow

### 1) identify PR context
- run `gt sync` and `gt restack` first to ensure comments/stack state are current.
- use current branch PR by default.
- if PR is ambiguous, use the PR number provided by the user.

### 2) pull unresolved review threads
- run `scripts/fetch_unresolved_review_threads.sh` from this skill.
- parse each unresolved thread into:
  - thread id
  - latest comment url
  - reviewer
  - full comment text verbatim
  - code location for the comment (path + line/side fields when available)
  - concise issue summary

### 3) produce suggestions before coding
- for each unresolved thread, provide two suggestion layers:
  - business logic: product/behavior impact, user impact, and whether the suggestion improves signal integrity or safety.
  - code: concrete implementation direction, affected files/modules, and test impact.
- classify each thread with a recommendation: `implement now`, `defer`, or `ignore`.
- include risk if ignored and likely scope level (`small`, `medium`, `large`).

### 4) stop and request approval
- do not edit code and do not run formatting/lint/typecheck for implementation until the user approves.
- ask for explicit approval in numbered form, for example:
  - `1. implement`
  - `2. ignore`
  - `3. defer`
- only proceed to implementation after explicit confirmation.

### 5) after approval (when requested)
- implement only approved suggestions.
- leave ignored/deferred points untouched.
- run repo checks requested by the user.
- update the existing PR (not a new PR) when requested.

## Output format (planning phase)
- unresolved threads (with full verbatim comment text and code location)
- suggested handling (business logic + code)
- approval prompt (numbered decisions)

## Guardrails
- never jump straight into implementation from unresolved comments.
- keep suggestions concrete; avoid generic "could improve" feedback.
- prioritize correctness, regression risk, and atomic PR boundaries.
