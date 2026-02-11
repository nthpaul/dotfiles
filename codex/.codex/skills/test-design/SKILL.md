---
name: test-design
description: "Design test plans and test cases for new features or changes, covering boundaries, error cases, and levels (unit/integration/e2e). Use when asked to write tests or create a test plan in any repo."
---

# test-design

## Overview
Translate requirements into a compact test plan and concrete cases that minimize regression risk.

## Workflow

### 1) Clarify behavior
- Confirm acceptance criteria and non-goals.
- Identify inputs, outputs, and side effects.

### 2) Identify test levels
- Choose unit, integration, or e2e coverage based on risk and scope.
- Prefer the smallest effective level.

### 3) Enumerate cases
- Happy path
- Boundary conditions
- Invalid inputs and error handling
- State transitions and idempotency
- Performance or rate limits if relevant

### 4) Map to tests
- Group cases into test files/suites.
- Suggest fixtures and data builders.

## Output template (adapt as needed)
- Acceptance criteria recap
- Test plan (levels + rationale)
- Test cases list
- Fixtures/data needs
