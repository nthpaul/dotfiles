---
name: pr-link-review
description: "Review a pull request from a direct URL, including GitHub and Graphite PR links, by fetching metadata and diff, summarizing changes, listing major updates, and flagging correctness risks, flawed logic, and business-logic concerns. Use when a user shares a PR link and asks for review feedback, risk analysis, or a change summary."
---

# pr-link-review

## Overview
Review a PR from a link without requiring manual URL translation. Normalize the link, fetch the PR diff and metadata, then produce a risk-focused review.

## Workflow

### 1) Normalize the PR link
- Run:
  - `python3 scripts/parse_pr_link.py "<pr-link>"`
- Read JSON output:
  - `owner`
  - `repo`
  - `number`
  - `github_pr_url`
- Accept these inputs:
  - GitHub PR URL: `https://github.com/<owner>/<repo>/pull/<number>`
  - Graphite PR URL: `https://app.graphite.com/github/pr/<owner>/<repo>/<number>/<slug>`
  - Shortcut: `<owner>/<repo>#<number>`

### 2) Fetch PR context
- Use GitHub CLI for metadata:
  - `gh pr view <number> --repo <owner>/<repo> --json title,body,author,baseRefName,headRefName,changedFiles,additions,deletions,labels,url`
- Fetch changed files (with patches):
  - `gh api --paginate repos/<owner>/<repo>/pulls/<number>/files`
- Fetch full diff:
  - `gh pr diff <number> --repo <owner>/<repo>`
- If `gh` fails, report the blocker clearly and include the exact failing command.

### 3) Analyze the change
- Summarize:
  - the intent of the PR
  - what behavior changed
  - the highest-risk modules/files
- Inspect for:
  - correctness and edge-case handling
  - missing validation/error handling
  - transaction/order-of-operations risks
  - missing tests or weak assertions
  - business-rule mismatches (requirements vs implementation)
- Prioritize issues that can cause production regressions.

### 4) Produce structured review output
Use this exact section order:
- `summary`
- `major changes`
- `needs attention`
- `flawed logic`
- `business logic concerns`
- `testing gaps`
- `open questions`

For each finding:
- include severity (`high`, `medium`, `low`)
- include a file reference (path and line when available)
- explain why it matters
- propose a concrete fix

If no issues are found:
- state that explicitly
- still include residual risk and test coverage gaps

## Guardrails
- Focus on regression risk and logic correctness, not style nits.
- Separate confirmed defects from hypotheses.
- Treat Graphite links as PR pointers; review the underlying GitHub PR diff.
- Keep feedback actionable and tied to changed code.
- Do not implement fixes unless the user asks.

## Resources
- `scripts/parse_pr_link.py`: Parse GitHub/Graphite PR links into normalized GitHub PR coordinates.
