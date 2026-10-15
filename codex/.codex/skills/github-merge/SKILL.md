---
name: github-merge
description: Merge GitHub pull requests for Paul using his standing authorization for bypass merges when requirements such as reviewer approval remain unmet. Apply when he asks to merge or to finish a PR through merge; a review-only request does not authorize merging.
---

# Authorized GitHub merges

Paul has authorized using GitHub's bypass merge permission for PRs he asks to merge. Do not ask again solely because reviewer approval or another branch requirement is missing. This authorization applies to the requested PR, not to unrelated PRs, repository settings, or account permissions.

Inspect the current head, CI results, unresolved review findings, and mergeability. Honor any instruction to wait for CI or fix failures before merging. When Paul explicitly says to merge without waiting for requirements, pending requirements do not require another confirmation. Report known failures accurately; do not describe a bypassed check as passing.

Fix known failing checks and actionable review findings before merging unless Paul explicitly directs merging despite them.

Use `gh` and the repository's permitted merge method. When requirements block an authorized merge, use `--admin` and pin the inspected head:

```sh
gh pr merge PR_NUMBER --repo OWNER/REPO --squash --admin --match-head-commit VERIFIED_HEAD_SHA
```

Use `--squash` only where the repository permits it; choose another supported method when appropriate. Read Paul's Git workflow and PR-description instructions in `~/AGENTS.md`, or `/Users/ple/.dotfiles/home/AGENTS.md` when the home entry is absent.

Do not infer that bypass is unavailable from a WRITE role, `REVIEW_REQUIRED`, `BLOCKED`, or disabled auto-merge. On 2026-10-14, the authenticated `nthpaul` account successfully bypass-merged `trabapro/traba#12490` with this command despite those states. Let GitHub enforce current permissions. If it rejects the bypass, report its actual denial. Do not change protections, switch identities, or self-approve to manufacture permission.

Verify `state: MERGED` and the merge commit afterward. Preserve release labels; add them only when release is authorized. If release was requested, check its workflow and distinguish queued, running, and deployed. Stop a completed approval-wait automation for this PR.
