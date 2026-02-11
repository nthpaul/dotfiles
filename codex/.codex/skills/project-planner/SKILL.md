---
name: project-planner
description: "Discuss, scope, and design a project before implementation. Use to gather requirements, write a concise spec, identify risks, and decompose work into atomic tasks that are CI-safe and suitable for stacked PRs."
---

# project-planner

## Overview
Turn ambiguous ideas into a concrete spec, milestones, and atomic tasks with clear acceptance criteria.

## Workflow

### 1) Discovery
- Ask for goals, constraints, and success criteria.
- Identify stakeholders, timelines, and dependencies.

### 2) Scope and non-goals
- Define what is in vs out of scope.
- Note explicit exclusions to avoid scope creep.

### 3) Requirements and acceptance criteria
- Translate goals into testable criteria.
- Call out edge cases and failure modes.

### 4) Design sketch (lightweight)
- Outline high-level architecture and data flow.
- Identify impacted modules, APIs, and storage.
- Note migration or rollout needs.

### 5) Risks and mitigation
- List technical and product risks.
- Propose mitigations and validation steps.

### 6) Task decomposition
- Break into atomic, CI-safe tasks.
- Each task should be independently testable.
- Prefer tasks that map cleanly to a single PR.

## Output template (adapt as needed)
- Project brief
- Scope / non-goals
- Requirements + acceptance criteria
- Design sketch
- Risks + mitigations
- Task list (atomic)
