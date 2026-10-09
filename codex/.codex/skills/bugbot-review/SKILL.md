---
name: bugbot-review
description: Run Bugbot-guided PR or branch review using scoped BUGBOT.md checks and an independent whole-diff pass, then deduplicate actionable findings. Use for bugbot-review, review-bugbot, or a request for Bugbot-guided code review. Supports --comment to post findings on a PR.
---

# Bugbot review

Review for concrete correctness, reliability, and security problems. Combine the repository's Bugbot guidance with a whole-diff review. Use Codex review agents rather than Cursor's specialized `bugbot` subagent.

## Resolve the target

1. Read the repository's `AGENTS.md` and applicable nested instructions. Treat `CLAUDE.md` and Bugbot guidance as supplemental.
2. Honor an explicit PR, branch, base, or uncommitted-only scope. Otherwise check the current branch's PR association with `gh pr view`. Record the PR number, URL, title, base, and head. Distinguish no associated PR from a CLI authentication or network failure; report failures instead of silently substituting another target.
3. For a PR, read its description and diff with `gh pr view` and `gh pr diff`. Review the requested PR head, not whatever happens to be checked out. Read remote file contents or use an isolated checkout if the local checkout differs. Do not stash or overwrite local work to perform a review.
4. For a branch without a PR, resolve the repository's default base or the specified base. Use `git diff <base>...HEAD`. Respect a stacked branch's actual parent instead of treating downstack changes as part of this review.
5. For a local branch review, include staged, unstaged, and relevant untracked source changes unless the user requests committed changes only. For uncommitted-only scope, exclude branch commits. Keep local additions separate from a published PR diff so locations remain accurate.
6. Build the repo-relative changed-file list from this scope. If empty, report that there is no diff to review.

## Discover guidance

Find `BUGBOT.md` files with `rg --files --hidden`, excluding Git metadata and dependencies. Keep guidance when changed files fall under its directory subtree or its topic clearly applies to the diff. Keep matching ancestors, and include `.cursor/BUGBOT.md` when present. Load applicable `BUGBOT-NITS.md` guidance too, while keeping findings actionable.

## Review passes

Run one independent pass per relevant guidance file and one global whole-diff pass. When Codex collaboration tools are available, delegate these passes to review subagents, bounded by the available concurrency slots. Otherwise perform the passes separately yourself and disclose that they were not independent agents.

Give each reviewer:

- The absolute repository path, target head and base, and exact diff scope, including any local changes.
- The changed files and applicable repository instructions.
- Its guidance file, or the instruction to review the entire diff for regressions.
- A request for actionable findings only, with severity, path, line range, triggering conditions, impact, and supporting evidence.
- A read-only assignment. Reviewers must not edit code or post comments.

Inspect surrounding code, callers, contracts, and tests to verify each claim. A review comment or rule violation is an input to investigate, not proof of a bug. Keep concerns that cannot be substantiated out of the findings. Report an incomplete pass as a coverage limitation.

## Aggregate findings

Deduplicate by file, line range, and normalized title. Also merge differently worded findings with the same underlying cause. Retain all contributing source tags, such as `path/to/BUGBOT.md` and `global-diff`.

Order findings by severity:

- `critical`: likely outage, data loss, or security vulnerability.
- `high`: strong chance of broken behavior in an important flow.
- `medium`: meaningful correctness or reliability risk with limited impact.
- `low`: concrete edge-case risk with small impact.

Each finding needs a short title, why it is a problem, a precise file and line range, and source tags. Use clickable local file links or verified PR diff links when available. Do not fix findings unless the user requests fixes.

Always report PR association as `Associated PR: #<number> (<url>)` or `Associated PR: none (reviewed branch diff)`. If association could not be checked, say so.

If no issues remain after completed passes, say `No issues found after Bugbot + whole-diff review.` State material coverage gaps separately.

## PR comments

Return findings in chat by default. Post on GitHub only when the user asks to post the review or invokes `--comment`. Chat-only instructions take precedence. A branch-only review has nowhere to post.

Before posting, inspect existing open and resolved review threads and PR-level comments, including pagination. Avoid repeating the same underlying issue even when the wording differs. Verify that the PR head still matches the reviewed commit; if it changed, revalidate affected findings before posting.

- Post one inline comment per new finding anchored to the reviewed diff. Keep findings without a valid diff anchor in chat.
- For a completed review with no findings, post `lgtm - bugbot review` only if an equivalent review comment is not already present. Do not post this when passes were incomplete or all findings were merely duplicates.
- Append `left by $bugbot-review skill` to every posted comment.
- Pass comment bodies as structured data or through a body file, never as interpolated shell code.

Summarize what was posted, already covered, or retained in chat.
