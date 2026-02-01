---
name: code-review
description: "Perform regression-focused code reviews: identify bugs, risks, missing tests, and edge cases. Use when asked to review a PR, diff, or change set in any repo."
---

# Code Review

## Overview
Review code changes with a bias toward correctness, regression risk, and test coverage.

## Workflow

### 1) Understand intent and scope
- Read the request or PR description.
- Identify the user-visible behavior and risk areas.

### 2) Inspect changes for correctness
- Look for logic errors, unhandled cases, and unsafe assumptions.
- Flag performance or security issues when relevant.

### 3) Assess tests
- Confirm new behavior is covered by tests.
- Call out missing tests or weak assertions.

### 4) Provide findings
- List findings ordered by severity.
- Include file/line references when available.
- If no findings, say so explicitly and note any testing gaps.

## Output template (adapt as needed)
- Findings (ordered by severity)
- Questions or assumptions
- Change summary (brief)
- Testing notes or gaps
