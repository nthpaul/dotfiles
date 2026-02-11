---
name: tdd-orchestrator
description: "Orchestrate a full TDD workflow for coding tasks: plan -> spec -> tasks -> implement -> test -> review -> debug -> summarize. Use when a user wants strict TDD, regression minimization, or end-to-end delivery across code changes in any repo."
---

# tdd-orchestrator

## Overview
Drive a full TDD lifecycle with Red -> Green -> Refactor gates and clear status updates. Enforce tests-first and finish with a concise, risk-aware summary.

## Workflow

### 1) Clarify scope and success
- Ask for missing requirements, constraints, and acceptance criteria.
- Confirm target area, boundaries, and non-goals.
- If ambiguous, stop and ask before coding.

### 2) Plan (when non-trivial)
- Use the planning tool for multi-step or risky work.
- Keep steps atomic and CI-safe.

### 3) Spec and tasks
- Convert requirements into acceptance criteria.
- Define a test plan (unit/integration/e2e) tied to the criteria.
- Break work into tasks that each map to a test.

### 4) TDD loop (Red -> Green -> Refactor)
- Red: write a failing test that captures the next smallest behavior.
- Green: implement the minimal change to pass.
- Refactor: clean up with tests still green.
- Repeat until acceptance criteria are met.
- Do not implement before a failing test unless the user approves an exception.

### 5) Test and verify
- Run the smallest set of tests that cover the change.
- Expand to broader suites when risk is higher or changes are cross-cutting.
- If test commands are unknown, invoke `repo-command-discovery` and run its wrapper:
  - `sh .codex/skills/repo-command-discovery/scripts/run.sh [path]`
  - Or use the full skill path if not symlinked into the repo.

### 6) Review and debug
- Review for regressions, missing tests, edge cases, and risky changes.
- If tests fail, isolate, reduce to a minimal repro, fix, and re-run.

### 7) Summarize
- Provide: change summary, tests run (with results), risks, and next steps.

## Output template (adapt as needed)
- Change summary: <1-3 bullets>
- Tests run: <commands and results>
- Risks/notes: <anything that needs attention>
- Next steps: <optional>
