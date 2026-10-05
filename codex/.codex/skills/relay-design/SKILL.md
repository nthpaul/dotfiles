---
name: relay-design
description: >
  Create, publish, and revise readable HTML documents in the Traba Relay library:
  plans, TRDs, proposals, analyses, explainers, and mockups. Use for relay-cli
  document authoring, Relay document design, or requested Relay review rounds.
  Lead with the decision, layer supporting detail, and verify factual claims.
metadata:
  short-description: Relay document design, publishing, and review
---

# Relay design

A Relay document must let someone decide or learn without the author's conversation
context. Put the current conclusion and next action in the main text. Keep definitions,
reasoning, alternatives, and supporting evidence reachable without interrupting it.

## Destination and publication

- Use the user's chosen path or the existing document's path. For new documents for
  Paul, default to `/paul/<project>/<document>.html`. Use another person's namespace
  only when the user requests it. Style guidance never determines document ownership.
- Publish requested documents with `relay library put <path> <local-file>`. Locate
  `relay` on PATH; this machine also has `~/.relay/bin/relay`. Inspect CLI help for
  commands or flags you have not verified.
- Use HTML for reader-facing Relay documents. Use Markdown for agent handoffs or
  when explicitly requested. Preserve the requested format during revisions.
- Return the full library URL, `https://relay.traba.work/library/<path>`, using the
  actual destination. Use an ephemeral share link only when requested.
- Before replacing an existing document, read it with `relay library get <path>` and
  retain its structure and content outside the requested change.
- After publishing, read the document back and verify its contents. Inspect the
  rendered page when a browser is available; distinguish content checks from visual
  checks if rendering cannot be inspected.

## Lead with the decision

- Open with what this is, the decision or finding, and the reader's next action.
  The summary contains conclusions that make sense without the body.
- State settled decisions directly. Keep proposed behavior visibly separate from
  existing behavior. Move unresolved work into a TODO section.
- Define unfamiliar terms on first use. Explain the problem before its mechanism.
  Scale technical detail to the audience and the requested document type.
- Put discarded alternatives, historical context and out-of-scope material in a
  collapsed section, a short supporting note or an appendix.
- Use descriptive names and headings. Link ticket/PR references and explain their
  purpose; a ticket number alone is not a useful title.
- Apply the available `unslop` skill for prose cleanup. Keep exact technical names,
  field names, material uncertainty and evidence intact.

## Layer detail and design

- Use tooltips for short definitions and supporting reasons. Read
  [references/tooltips.md](references/tooltips.md) when adding or revising them.
  Essential decisions and warnings must remain visible without hovering.
- Use collapsed `<details>/<summary>` for longer supporting detail. Use tabs when
  parallel proposals benefit from comparison, rather than forcing a tabbed layout.
- Add an anchored table of contents when the document has enough sections to need one.
- Prefer diagrams where they explain ownership, structure, flow or timing faster than
  prose. Use HTML/SVG by default; honor a requested format such as ASCII box diagrams.
  Use screenshots of real UI when documenting an existing user experience. Label a
  proposed mockup as proposed.
- Preserve source values, units and scales in charts. Label illustrative data as
  illustrative; do not present it as measured evidence.
- Theme with `:root` tokens. Support the system dark preference under
  `@media (prefers-color-scheme: dark)` with `:root:not([data-theme="light"])`, and
  repeat the dark tokens under `:root[data-theme="dark"]` for Relay's theme toggle.
- Check narrow layouts, diagram labels, table wrapping and tooltip clipping. Keep
  scrollable diagrams separate from tooltip containers.

## Shape by document type

- **Plan / design / TRD:** explain the end-to-end user experience first, then the data
  model, existing components to reuse, gaps, services, API contracts, sequencing,
  rollout and verification. Include relevant Linear project/ticket links when they
  exist. Label schema sketches as proposed; migration diffs must come from real files.
- **Stateful system:** map each backend state to what the user sees and can do.
  Include legal transitions, their triggers, ownership, failures and return paths.
  Keep every repeated state name and diagram consistent.
- **Proposal:** state what each item covers, the concrete request and unresolved
  decisions. Record sign-offs only when they actually exist.
- **Analysis:** define the incremental question, comparison, verified time window,
  sample size and result. Use a sample adequate for the claim and disclose its limits.
- **Explainer:** build from the reader's problem through the concepts to the runtime
  flow. Add diagrams or a step-through when they improve understanding.
- **Status / handoff:** state what changed, the current outcome and what remains.
  Put historical detail where the next reader can consult it only if needed.

## Evidence and verification

- Verify load-bearing claims against the available source: code, data, configuration
  or recorded discussion. Link the exact supporting artifact and identify its scope
  or revision when it affects the claim.
- Separate requirements, verified existing behavior and design judgment. Do not claim
  local source reflects a deployed production revision without checking it.
- Quote only what matters and is permitted to reproduce. Preserve exact wording when
  a prompt or configuration value is itself the subject of the decision.
- When a claim is challenged, recheck its source. Update every section, table and
  diagram that repeats the corrected claim, then reread the document as a whole.
- For substantial technical designs, use an independent critique when delegation is
  available and permitted. Use an available reviewer/model; a specific unavailable
  model must not block the document. Check its findings against the actual artifact.
  For small edits, focused direct verification is sufficient.

## Requested review rounds

- Use `relay review` when the user requests review work. Posting review replies or
  contacting reviewers stays within that authorization; publishing a document alone
  does not request an ongoing review session or messages to other people.
- Read the published document rather than relying on truncated anchor excerpts.
  Inspect every unresolved thread whose latest message is the reviewer's, including
  follow-ups on old threads.
- Answer the question and describe the specific change in each reply. If the user
  asks for a reply without an edit, keep the document unchanged.
- Treat one reported style pattern as a reason to check the whole document for that
  pattern. Keep all linked representations consistent after each revision.
- Do not intervene in conversations between other humans unless requested. Follow
  the requested number or scope of review rounds; do not start an indefinite wait.
