# Personal AGENTS.md

> Scope: This file applies to work under `/Users/ple` unless a more specific `AGENTS.md` overrides it.

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

## Communication

- Explain tradeoffs plainly.
- Call out unnecessary complexity directly.
- When proposing a simpler alternative, prefer the version with less indirection unless there is a concrete downside.
- Always use ASCII box diagrams for architecture, flow, and system maps. Do not use mermaid (or other diagram DSLs) unless explicitly asked.

## Git workflow

- Use `git commit` and `git push` for commits and pushes, and `gh` for GitHub pull requests.
- Use Graphite only when the user explicitly requests it. This preference overrides Graphite requirements in repository instructions and skills.
- A request to commit and push means commit the scoped changes and push the intended branch. Create a new PR only when requested or already part of the active task.
- Keep each PR atomic and ensure it passes required CI checks. Stacked PRs are optional.

## Pull request descriptions

Every PR description must include `System diagrams`, `Data flow diagrams`, and `Blast radius` sections. Apply this to every repository, draft PR, and individual PR in a stack, including small, documentation, config, and test changes. These requirements override optional-diagram guidance in PR authoring skills.

- Read the actual diff and the relevant callers, contracts, and consumers before writing these sections. Compare each PR against its own base branch, including its immediate parent in a stack.
- In `System diagrams`, include separately labeled `Before` and `After` ASCII box diagrams in fenced `text` blocks. Show the affected components, their responsibilities, dependencies, and system boundaries. Mark the changed components and connections.
- In `Data flow diagrams`, include separately labeled `Before` and `After` ASCII box diagrams in fenced `text` blocks. Trace the relevant trigger or input through transformations, calls, storage reads and writes, and the output or side effect. Label arrows with the data or contract they carry.
- Keep the diagrams scoped to the PR and use the same names and level of detail before and after. Name real components and interfaces so a reviewer can connect the diagrams to the code.
- When the system or data flow is unchanged, show both views and label them `Unchanged`. For non-runtime changes, show the affected authoring, build, test, or configuration process. State when runtime behavior is unchanged.
- In `Blast radius`, identify the directly affected behavior and the indirect callers, shared packages, contracts, stored data, and external integrations that could be affected. Explain the relevant failure modes and the checks that cover them. Distinguish verified facts from assumptions and untested risks.
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
