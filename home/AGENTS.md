# Personal AGENTS.md

> Scope: This file applies to work under your home directory unless a more specific `AGENTS.md` overrides it.

## Default Preferences

- Prefer the simplest correct solution.
- Avoid preemptive abstraction.
- Avoid introducing helper types, base types, wrappers, or utility functions unless they reduce real duplication now.
- Prefer explicit, readable shapes over clever or indirect type construction.
- When a type can be written directly without losing safety, write it directly.
- Prefer enums or explicit named types for fixed value sets over `as const` patterns.
- Keep code easy to understand at first glance.
- Optimize for local clarity before theoretical reuse.
- If an abstraction exists only for possible future reuse, remove it.

## Refactoring Bias

- Inline small one-off helpers when doing so makes the code easier to read.
- Fuse shared type fragments when the shared fields are small and not reused elsewhere.
- Keep discriminated unions when they improve correctness, but avoid extra layers around them.
- Use the fewest moving pieces needed to preserve correctness.

## Execution and verification

Scale verification to consequence and uncertainty. Use direct checks for small, reversible edits.

- Define the requested outcome and its observable completion condition before building tooling. For broad QA requests, map the scope to a finite set of cases and explicit assertions. Distinguish an intermediate handoff from a completed journey, and manual or simulated results from unattended live passes. Verify the result at the final consumer.
- When the user names a contract (a diagram, state machine, or doc) or rejects a behavior, stop opening pull requests until the work matches that contract. Update the contract first, then resume.
- Prove one representative path through the real system before generalizing its automation or expanding variants. Exercise the riskiest external dependency early. For unattended work, prove that the path can run without the user before relying on it overnight.
- Before repeated stateful tests, verify fixture prerequisites and one complete reset and reentry cycle. After fixing reset behavior, repeat that cycle. Keep unrelated cases independent where possible; preserve shared history when continuity is the behavior under test.
- Build adapters from authoritative types, actual responses, and the real lifecycle. Replay captured, sanitized responses through the adapter before live use. Do not require a resource before the action that creates it. Exclude observation timestamps from comparisons of stable state.
- When a check refuses to proceed, first distinguish a product defect, a fixture problem, and an incorrect test expectation. Compare the refusal with native state and source before changing the product. A workaround that skips the behavior under test does not establish a pass.
- Add tooling only when it unblocks the next real assertion or removes demonstrated repetition. Extend one working executor instead of accumulating candidate copies and parallel frameworks. Keep review and documentation proportional to the change, while honoring required checks and user-requested records.
- After two attempts without new evidence, or about 15 minutes of unexplained stalling, change the approach. Trace the missing transition across the relevant boundaries instead of repeating unchanged polls or adding future scaffolding. Expected build and provider wait times are not unexplained stalls. Continue independent useful work when a dependency is blocked.
- Delegate work that shortens the current critical path: diagnosis, a bounded fix, or independent review. Give each task a concrete deliverable. Avoid parallel helpers that only create a larger integration queue. Isolate state per worker where possible; designate one writer when shared external state is unavoidable.
- Record IDs, effects, outcomes, and recovery instructions as work happens. Keep checkpoints compact and refresh published summaries at meaningful milestones. Report completed cases, newly verified transitions, and exact blockers separately from offline test counts or tooling readiness.
- Background monitors write a journal or log. Post into the steering thread only for a new bug, a merge, a failure, or a question only the user can answer. Unchanged status stays in the log.
- For external writes, record intent and persist the response or error. Reconcile an unknown outcome against authoritative state before retrying. Read-only reconciliation should not introduce another write or require rebuilding the entire test package.

### Keep tests fast

- Treat CI runtime as part of the change's cost. Use the cheapest test layer that proves the behavior. Cover pure logic and decision matrices with unit tests. Use focused integration tests for real database, queue, transaction, or concurrency contracts.
- Keep full end-to-end journeys few and representative. Do not replay dozens of conversation turns for every variation. Build the smallest valid persisted fixture and exercise the transition under test. Keep a full journey when the interaction between its steps is what needs proof.
- Extend existing fixtures and tests before adding another heavy spec. Avoid repeated application startup, unnecessary Postgres or Redis round trips, sleeps, polling, and broad regression matrices that duplicate existing coverage. Preserve the real boundaries needed to expose the defect.
- Measure changed integration specs before pushing. Record a material runtime increase in the PR and reduce avoidable work before shipping. Do not add minutes to shared CI without a clear coverage need. Use timings to separate expensive tests from runner contention.
- When one spec determines the slowest shard, split independent cases into balanced files so CI can distribute them. Splitting does not replace reducing total work. Preserve useful assertions and race coverage when replacing expensive tests with cheaper ones. Do not weaken checks or raise timeouts to hide the cost.

### Visual QA (mandatory)

- Every visual change requires QA in the actual browser or app, inspected screenshots, and a short video walkthrough before marking the work complete or ready for review. Show the changed appearance and interactions, including relevant before/after, loading, error, and empty states. Check desktop and a smaller viewport when the UI is responsive.
- Attach screenshots and the video to the PR and final handoff. Show screenshots inline and provide a playable video or durable video link. Keep the original evidence under `~/projects/work-docs`. State when evidence uses synthetic data and which backend, authentication, or persistence paths were not exercised. Automated checks alone do not satisfy visual QA. If capture is blocked, report the missing evidence and blocker explicitly rather than calling the work ready.

## Communication

- Explain tradeoffs plainly.
- Call out unnecessary complexity directly.
- When proposing a simpler alternative, prefer the version with less indirection unless there is a concrete downside.
- Use Mermaid diagrams in PR descriptions. Elsewhere, use mermaid diagrams for architecture, the diagram should be top to bottom rather that LTR, flow, and system maps unless explicitly asked for another format.

## Git workflow

- Use `git commit` and `git push` for commits and pushes, and `gh` for GitHub pull requests.
- Use Graphite only when the user explicitly requests it. This preference overrides Graphite requirements in repository instructions and skills.
- A request to commit and push means commit the scoped changes and push the intended branch. Create a new PR only when requested or already part of the active task.
- Keep each PR atomic and ensure it passes required CI checks. Stacked PRs are optional.

## Pull request descriptions

Every PR description must include `System diagrams`, `Data flow diagrams`, and `Blast radius` sections. Apply this to every repository, draft PR, and individual PR in a stack, including small, documentation, config, and test changes. These requirements override optional-diagram guidance in PR authoring skills.

- Read the actual diff and the relevant callers, contracts, and consumers before writing these sections. Compare each PR against its own base branch, including its immediate parent in a stack.
- In `System diagrams`, include separately labeled `Before` and `After` Mermaid diagrams in fenced `mermaid` blocks. Show the affected components, their responsibilities, dependencies, and system boundaries. Mark the changed components and connections. Prefer top to bottom rather than LTR.
- In `Data flow diagrams`, include separately labeled `Before` and `After` Mermaid diagrams in fenced `mermaid` blocks. Trace the relevant trigger or input through transformations, calls, storage reads and writes, and the output or side effect. Label arrows with the data or contract they carry. Prefer top to bottom rather than left to right.
- Keep the diagrams scoped to the PR and use the same names and level of detail before and after. Name real components and interfaces so a reviewer can connect the diagrams to the code.
- When the system or data flow is unchanged, show both views and label them `Unchanged`. For non-runtime changes, show the affected authoring, build, test, or configuration process. State when runtime behavior is unchanged.
- In `Blast radius`, identify the directly affected behavior and the indirect callers, shared packages, contracts, stored data, and external integrations that could be affected. Explain the relevant failure modes and the checks that cover them. Distinguish verified facts from assumptions and untested risks. Use bullet points.
- Preserve repository-required template sections and bot-managed markers. Before submitting a PR or updating its description, check that all required sections and diagrams are present and accurate for the current diff. Read back the published body after submission.

## Documentation home (CRITICAL)

Durable docs, reports, experiment writeups, eval dumps, and agent memos go under **`~/projects/work-docs`** (git repo `nthpaul/work-docs`) — not `/tmp`, not product-repo `tmp/`, not Desktop/Downloads.

- Experiments → `experiments/<slug>/`
- Analytics → `analytics/<slug>/`
- Topic deep-dives → top-level folder (e.g. `neutron-ops-actions-memory/`)
- Raw rescues / tool I/O → `scratch/<slug>/` with a short `README.md`
- Plans → `plans/<slug>/`

Write new docs there while working. Commit/push when asked to save. Never leave the only copy in `/tmp`. Redact secrets. Product code stays in product repos.

## Slack identity (CRITICAL)

You are Paul Le (`U09FL4PT8AE`). Never post, edit, react, or otherwise write to Slack as anyone else.

- **Never** use Infisical `SLACK_API_KEY_USER` (or any shared/service user token) to send Slack messages. That token is Moreno Antunes (`U025205FBUN`), not Paul.
- **Never** post as bots (`SLACK_API_KEY_BOT`, `SLACK_API_CERTIFICATIONS_KEY`, etc.) unless Paul explicitly asks to post as that bot.
- For Slack writes as Paul, use **only** the Cursor Slack MCP authenticated as Paul (`plugin-slack-slack` / `user-slack`).
- Infisical Slack tokens are fine for **read-only** ops (list channels, fetch threads, inspect membership) when needed.
- Before any Slack write via a raw token/API, run `auth.test` and abort unless `user_id` is `U09FL4PT8AE`. If it is Moreno or a bot, stop and use Paul's MCP instead.
- If a mistaken write as Moreno/bot happens: delete it immediately, then re-send via Paul's MCP.

## Dev machine hygiene

Local dev cleanup / resource audit for Traba worktrees and infra:

- `~/docs/dev-machine-hygiene.md`
- `~/scripts/dev-machine-audit.sh`
