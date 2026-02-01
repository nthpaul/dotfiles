---
name: debug-triage
description: "Debug and triage failing tests, regressions, flaky behavior, or production issues with a fast repro -> isolate -> minimal failing test -> fix -> verify workflow. Use when debugging, investigating CI failures, or minimizing regression risk in any repo."
---

# Debug Triage

## Overview
Apply a consistent, minimal-change debugging workflow that yields a reproducible failure, a focused fix, and verification tests.

## Workflow

### 1) Capture the symptom
- Record the error, stack trace, and environment details.
- Identify the first failing test or observable failure.

### 2) Reproduce locally
- Re-run the failing test or command.
- If flaky, run multiple times and note variability.
- If no repro, ask for logs, seeds, config, or CI artifacts.

### 3) Isolate the cause
- Reduce input and scope to the smallest failing case.
- Narrow the failure by bisecting or commenting out changes.
- Add temporary logs or assertions to confirm hypotheses.

### 4) Lock the bug with a test
- Write the smallest failing test that reproduces the bug.
- Ensure it fails before fixing (Red).

### 5) Fix minimally
- Make the smallest change to pass the test (Green).
- Refactor only after green tests.

### 6) Verify
- Run the minimal test set and any higher-level tests if risk is high.
- Remove temporary logs and confirm cleanup.

## Output template (adapt as needed)
- Root cause: <short explanation>
- Fix: <what changed>
- Tests run: <commands and results>
- Risks/notes: <follow-ups or gaps>
