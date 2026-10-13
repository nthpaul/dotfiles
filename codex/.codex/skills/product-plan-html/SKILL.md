---
name: product-plan-html
description: Create source-grounded product plans as readable, portable HTML. Use for product proposals, implementation planning, PRD-to-build analysis, or recreating this document style. Adapt the content and layout to the task, with diagrams and previews when useful or requested. Automatically use installed pstack, traba-design and relay-design guidance, with bundled fallbacks.
metadata:
  version: "1.1.0"
---

# Product plan HTML

Create a document that helps its audience understand the proposal and make the next
needed decision. This is style guidance with borrowable templates, examples and tools.
Choose the content, level of detail and layout from the work being planned.

## Select scope and guidance

Resolve this directory from the loaded SKILL.md path and discover available guidance:

```bash
python3 <skill-dir>/scripts/plan.py detect
```

Pass callable browser tool names through repeated `--tools` arguments before `detect`.
Read the returned `read` paths for pstack architecture and verification, traba-design,
and relay-design. Discovery automatically selects bundled guidance for missing roles;
`--standalone detect` selects all fallbacks. Additional pstack principles remain in
`skills`: use model-the-domain for stateful work, idempotence for retries and external
effects, and build-the-lever for repeated transformations. Apply their guidance to the
actual scope. Installed guidance does not make its examples mandatory document sections.
Honor the user's instructions and local AGENTS.md. Apply available unslop guidance to prose.

Start from the audience, problem, requested deliverables and next decision. Include
technical detail when it changes understanding or makes a requested plan complete.
For a full data-model request, include every relevant table, field and relationship.
A UI change may need only a user journey or preview; a decision memo may need only
reasoning and evidence. Diagrams should explain a useful relationship, flow or timing,
or satisfy an explicit request. Choose preview surfaces from the request and affected
experience, with arbitrary apps, tools or roles. Omit content that has no purpose,
including empty sections, placeholder fields, zero-value metrics and repeated diagrams.

## Ground the proposal

Read supplied requirements through the user's requested browser or connected document
tools. Inspect relevant code with `rg`; record exact evidence and revisions before
asserting reuse or current behavior. Distinguish requirements, observed behavior,
proposed decisions and unresolved questions. Label unavailable source as proposed design
and sample data as fictional. A checkout alone does not establish a deployed revision.
Reuse established evidence for the same revision; refresh facts that may have changed.

## Author the HTML

Write tailored HTML directly. Optionally scaffold a small editable document:

```bash
python3 <skill-dir>/scripts/plan.py scaffold <project-dir>
```

This creates `preview.html` with embedded Poppins fonts, theme tokens, responsive styles
and a theme toggle. Edit that file as the source. Borrow or reshape its markup freely.
The broader [viewer styles](assets/viewer/styles.css) provide field tables, diagram
panels, app frames and controls when useful. The [injury example](assets/examples/injury-rtw)
is a comprehensive reference, not a required outline or default set of apps. Read its
[source context](references/provenance.md) when recreating that fixture.

Lead with the conclusion and next action. Use headings, anchored navigation, tabs or
collapsed detail according to the document's size and reading task. Apply Traba styling
to previews and Relay guidance to the surrounding document. Support readable light,
system dark and explicit dark themes, keyboard use and narrow layouts. Keep necessary
content visible without interactions. Preview behavior is illustrative; it does not
prove the backend works.

Use the optional structured builder when repeated schemas, flows, diagrams or connected
previews benefit from shared inputs and generated exports. Read
[the structured contract](references/plan-contract.md) only for that path. Its components
are optional, including schema diagrams. Select the representations needed by the task.
Edit its authored inputs and rebuild generated output. Tailored HTML requires no JSON
contract, fixed tabs, compulsory downloads, diagram renderer or script count.

## Verify and deliver

```bash
python3 <skill-dir>/scripts/plan.py validate <project-dir>/preview.html
python3 <skill-dir>/scripts/plan.py serve <project-dir> --port 8771
```

Validation checks portability for tailored HTML and consistency for components in a
structured build. Follow [verification](references/verification.md) for the selected
content. Inspect the actual document in the user's chosen browser; otherwise prefer
Codex's in-app browser when available, then the host's exposed browser tools. Check
reading order, themes, narrow layout and the controls or previews that exist. Verify
source-backed claims separately. Report browser or other checks that could not run.

Return the self-contained HTML with concise verification results. Keep authored inputs
and supporting evidence in the user's durable document workspace. Publish only when
requested, following [Relay publication](references/relay-publishing.md) and the user's
destination. Publication does not authorize contacting reviewers.

## Tools and portability

The package works in Codex, Cursor, Grok and Claude Code; [platforms](references/platforms.md)
explains discovery and browser differences. Python 3.10+ runs the CLI. Node 18+ is needed
only for Graphviz diagrams or structured custom-prototype syntax checks. Local fonts,
a pinned Viz renderer, bundling and fallback guidance are included. No dependency install
or external skill is required. Use the exposed desktop dependency-loader to locate a
runtime when needed. Relay CLI is optional and used only for requested publication.

To distribute the whole package:

```bash
python3 <skill-dir>/scripts/plan.py package <outside-skill-dir>/product-plan-html.zip
```

Extract `product-plan-html/` into the target host's user skills root. Its next discovery
run resolves that machine's installed guidance and tools.
