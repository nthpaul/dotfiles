---
name: plan-work-verify-merge
description: >-
  Plans, implements, reviews, and optionally merges one change in an isolated
  git worktree. Use when an agent should carry one change from a plan through
  a ready pull request, CI, Bugbot triage, a fresh review, and QA, then merge
  only when auto_merge is true. Read auto_merge, implementer_model, and
  reviewer_model, in that order, before starting.
---

# Plan, work, verify, merge

Carry one change from a plan to a reviewed pull request. Merge only when `auto_merge` is true.

## Read the three flags

Read these flags in this order before you start.

1. `auto_merge`. Boolean. When true, merge the pull request after the procedure below. When false, stop at an open, ready pull request and do not merge.
2. `implementer_model`. The model slug for the agent that plans and implements.
3. `reviewer_model`. The model slug for a fresh review agent.

## Run the procedure

Work in this order. Finish a step before you start the next.

1. Use an isolated git worktree. Do not share a checkout with another agent.
2. Plan from the named data shape, then implement. Run that plan and that implementation on `implementer_model`.
3. Open the pull request ready for review. Do not open it as a draft.
4. Babysit CI with `gh pr checks <n> --watch`. Never pass `--fail-fast`. Replace `<n>` with the pull request number. Green means every check is `pass` or `skipping`.
5. Triage Bugbot comments. Fix a real defect. Dismiss a nit with a concrete reason.
6. Spawn one fresh agent on `reviewer_model` to review the diff. Do not resume the implementer. The reviewer does not edit. If the reviewer reports a blocking defect, fix it on `implementer_model` and review again with another fresh agent.
7. Test and QA the behavior. Confirm the change works and existing behavior still works.
8. If `auto_merge` is false, stop. Leave the pull request open and ready. If `auto_merge` is true, merge with `gh pr merge <number> --squash --admin` so an approver is not required. Merge only after every CI check is `pass` or `skipping`, the fresh reviewer reported no blocking defect, and step 7 passed. If admin is denied, stop and report. Do not merge a red pull request. Do not force-push.
