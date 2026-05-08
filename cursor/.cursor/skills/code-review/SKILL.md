---
name: code-review
description: Perform regression-focused code reviews by identifying bugs, risks, missing tests, and edge cases. Supports optional `--pull` and `--pull-only` modes to start from unresolved PR comments, `--comment` mode to leave inline PR review comments for new findings while avoiding duplicates already flagged on the PR, and `--fix` mode to apply safe fixes, rerun repo-appropriate validation, and update the branch. Use when reviewing a PR, diff, or change set.
---

# Code Review

Review code changes with a bias toward correctness, regression risk, and test coverage.

## Modes

- Default: review the change set and report findings in the assistant response.
- `--pull`: if reviewing a GitHub PR, gather unresolved review comments and unresolved conversation threads first, then perform the normal review with those pulled issues as required context.
- `--pull-only`: if reviewing a GitHub PR, gather unresolved review comments and unresolved conversation threads first, and review only those pulled issues without expanding review scope to the rest of the diff.
- `--comment`: if reviewing a GitHub PR, also leave inline review comments for new findings on the PR itself.
- `--fix`: if reviewing a branch or PR, apply safe, scoped fixes for validated findings, rerun the repo-appropriate checks, and update the branch or PR.

`--pull-only` is narrower than `--pull`. If both are present, follow `--pull-only`.

## Pull rules

- Only use `--pull` or `--pull-only` when the review target is a GitHub PR.
- Start by gathering unresolved PR review comments and unresolved conversation threads.
- Treat the pulled comments as review inputs, not as automatically correct findings.
- Verify whether each pulled issue is still valid on the current PR head before surfacing it again.
- If a pulled issue is already resolved in code or is no longer applicable, say so explicitly instead of re-reporting it as an open finding.
- In `--pull-only` mode, do not expand review scope beyond the pulled unresolved comments.
- In `--pull` mode, after processing the pulled unresolved comments, continue with the normal review over the rest of the requested surface area.

## Commenting rules

- Only use `--comment` when the review target is a PR and inline comments can be anchored to specific files and lines.
- Before leaving any inline comment, inspect existing PR review comments and issue comments already present on the PR.
- Do not leave an inline comment for a finding that is already flagged on the PR.
- Treat a finding as already flagged when the existing comment points to the same file, line, or underlying issue, even if the wording differs.
- If a finding cannot be anchored cleanly to a line, keep it in the assistant response instead of forcing an inline comment.

## Fix rules

- Only use `--fix` for findings that are clear, local, and safe to correct without widening scope.
- Do not use `--fix` for speculative concerns, broad refactors, product decisions, or findings that need user confirmation.
- Before changing code, confirm the issue is not already fixed on the branch.
- After applying fixes, rerun the repo-appropriate validation commands and relevant targeted tests until they pass.
- When repository-specific instructions exist, follow them.
- In `/Users/ple/projects`, use the standard validation matrix:
  - `/Users/ple/projects/traba-server-node`: `yarn lint:fix --quiet && yarn typecheck && yarn format`
  - `/Users/ple/projects/traba`: `pnpm lint:fix --quiet && pnpm format`
  - `/Users/ple/projects/traba-app`: `yarn format`
  - `/Users/ple/projects/traba-server-firebase`: `yarn format`
- If `--fix` is used for a PR branch, update the branch and PR after checks pass.
- If `--fix` is used together with `--comment`, do not leave inline comments for issues that were fixed on the branch.

## Workflow

### 1. Understand intent and scope
- Read the request or PR description.
- Identify the user-visible behavior and risk areas.
- Load the repo root `AGENTS.md` first.
- Load the repo root `CLAUDE.md` if it exists.
- Load the closest relevant `.cursor/BUGBOT.md` or `.cursor/BUGBOT-NITS.md` files for the reviewed paths.
- If repo guidance conflicts, treat `AGENTS.md` as authoritative and use `CLAUDE.md` or BUGBOT guidance as supplemental.

### 2. Pull unresolved PR comments when requested
- If `--pull` or `--pull-only` is present, gather unresolved PR review comments and unresolved conversation threads first.
- Check whether each pulled issue is still open on the current head.
- Build the initial review set from the still-valid pulled issues.

### 3. Inspect changes for correctness
- If `--pull-only` is present, inspect only the pulled unresolved issues and stop there.
- Look for logic errors, unhandled cases, and unsafe assumptions.
- Flag performance or security issues when relevant.

### 4. Assess tests
- Confirm new behavior is covered by tests.
- Call out missing tests or weak assertions.

### 5. Handle inline comments when requested
- If `--comment` is present, gather existing PR comments first.
- Deduplicate against existing comments before writing anything new.
- Leave inline comments only for net-new findings that are specific, actionable, and line-anchored.

### 6. Apply fixes when requested
- If `--fix` is present, fix only the subset of findings that meets the fix rules.
- Keep the patch atomic and directly tied to the reviewed finding.
- Rerun repo checks and targeted tests after each fix set until they pass.
- Update the branch or PR with the fix commit(s).
- Summarize what was fixed, what remains, and any findings intentionally left unfixed.

### 7. Provide findings
- List findings ordered by severity.
- Include file or line references when available.
- If no findings, say so explicitly and note any testing gaps.
- If `--pull` or `--pull-only` was used, distinguish pulled unresolved findings from any newly discovered findings.
- If `--comment` was used, say which findings were commented inline and which were intentionally kept only in the summary.
- If `--fix` was used, distinguish between fixed findings and remaining findings.

## Output template

- Findings (ordered by severity)
- Fixed findings (when `--fix` is used)
- Questions or assumptions
- Change summary (brief)
- Testing notes or gaps
