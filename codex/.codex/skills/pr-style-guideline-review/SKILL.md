---
name: pr-style-guideline-review
description: "Review a PR for repository-specific coding and style guideline compliance before merge. Use when a user asks to sanity-check whether branch changes align with AGENTS.md rules, lint/type/style conventions, architecture boundaries, and existing code patterns."
---

# pr-style-guideline-review

## Overview
Use this skill to evaluate whether the current PR follows the repository's coding conventions and stylistic standards, then provide concrete, file-referenced findings and suggested fixes.

## Workflow

### 1) sync branch context
- run `gt sync` and `gt restack` first when working on a Graphite stack.
- identify the PR scope from the current branch unless the user provides a specific PR number.
- review changes against the branch below (`git diff <downstack-branch>...HEAD`) when available.

### 2) collect repository guidelines
- read `AGENTS.md` from repo root and any sub-repo `AGENTS.md` that applies.
- read repo-level quality config to infer stylistic rules:
  - `package.json` scripts
  - eslint/prettier configs
  - tsconfig(s)
  - CI checks (if needed)
- read only the touched modules needed to evaluate conventions and boundaries.

### 3) audit the PR diff for compliance
Focus on concrete violations, not preferences. Check:
- architecture boundaries (module ownership, repository/service placement)
- typing discipline (`any`, unsafe casts, optional vs required mismatches)
- naming/style consistency (existing patterns in surrounding code)
- dead code, redundant helpers, duplication, and accidental churn
- logging/error-handling consistency with local patterns
- test alignment with changed behavior

### 4) produce findings before code changes
Output findings first, ordered by severity, each with:
- severity: `high`, `medium`, `low`
- file reference: `path:line`
- violated guideline (quote or cite source file)
- why it matters (behavior/regression/maintainability)
- concrete code suggestion

If no findings, say so explicitly and mention residual risk/test gaps.

### 5) approval gate
- do not implement automatically unless the user asks.
- ask for numbered decisions per finding (e.g., `1 implement`, `2 ignore`, `3 defer`).
- implement only approved items.

## Output format
- `guideline sources`
- `findings`
- `recommended actions`
- `approval prompt`

## Guardrails
- do not invent repository standards; cite actual local sources.
- do not treat personal preference as a violation without a source.
- keep PRs atomic; avoid opportunistic refactors.
- preserve existing behavior unless a change is explicitly approved.
