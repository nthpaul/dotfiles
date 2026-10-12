---
name: product-plan-html
description: Build a source-grounded product implementation plan as a portable interactive HTML document, with the full data model, logic and data flows, diagrams, reuse versus net-new analysis, and connected previews across worker, operations and business apps. Use for PRD-to-build plans or recreating this document format. Automatically use installed pstack, traba-design and relay-design guidance, with bundled fallbacks when unavailable.
version: 1.0.0
---

# Product plan HTML

Produce a reviewable implementation plan and working illustrative previews. Start from
the supplied requirements and inspected source. The finished document must explain
what can be reused, what needs to be built, and how one input reaches every relevant app.

## Discover guidance and tools

Resolve this skill directory from the loaded SKILL.md location. Run commands with that
directory's `scripts/plan.py`; do not depend on the current working directory.

```bash
python3 <skill-dir>/scripts/plan.py detect
```

Pass the session's available browser tool names through repeated `--tools` arguments
before `detect`. The returned `read` list is mandatory reading before authoring. It selects
pstack architect, build-the-lever, model-the-domain, idempotence and prove-it-works;
traba-design; and relay-design. Follow installed guidance. If any is missing, read the
selected bundled reference for that role. Do not install plugins or stop to ask about
missing optional skills. `--standalone detect` exercises fallback selection explicitly.
Follow any applicable skill references these documents require. Honor user instructions
and local AGENTS.md above defaults. Apply available unslop guidance to the final prose.

The same package works in Codex, Cursor, Grok and Claude Code. Discovery searches their
project/user skill roots and installed plugin layouts, preferring the invocation host.
For platform installation or tool differences, read [platforms](references/platforms.md).

The package includes the viewer, local Poppins fonts, a pinned Viz/Graphviz renderer,
schema/diagram generators, bundling, validation, preview serving and Relay publication.
Python 3.10+ and Node 18+ are required. Discovery locates PATH and Codex runtimes. If
needed, use the desktop `load_workspace_dependencies` tool for runtime paths. No npm
install, system Graphviz, network connection or external skill is needed to build.
Relay CLI and a browser are optional capabilities. Use only callable tools exposed by
the current session. Report checks that could not run.

## Gather evidence once

Read the PRD through the user's requested browser or connected document tools. Prefer
Codex's in-app browser when requested. Inspect the relevant repositories with `rg`,
record revisions, and save source/input evidence with the project. Verify authoritative
schema, service ownership, eligibility, cancellation, scheduling, notification and app
patterns before asserting reuse. Label unavailable app source as proposed design.

Reuse verified evidence from an earlier run when the user asks for reconstruction.
Do not repeat research already established for the same source revision. Refresh facts
that may have changed for a new implementation plan. Separate requirements, observed
behavior, proposed decisions and open policy questions. Keep private medical or user
data out of fixtures. Use clearly labeled fictional examples.

## Author the contract

Read [the input and prototype contract](references/plan-contract.md). Scaffold a project:

```bash
python3 <skill-dir>/scripts/plan.py scaffold <project-dir>
```

For a recreation test, add `--example injury-rtw`. The example is an input fixture,
not a prebuilt HTML snapshot. For a new feature, replace the starter contents.

Use three authored inputs:

1. `plan.json` owns document metadata, every table/field, references, reuse changes,
   decisions, questions, evidence and flows with inputs, reads, writes and outputs.
2. `diagrams.json` owns supplementary flow graphs. Structured nodes/edges generate
   both DOT/SVG and Mermaid. Table diagrams always derive from `plan.json`. Preserve
   legacy DOT/Mermaid only for faithful recreations; check their agreement explicitly.
3. Optional `prototype.js` owns feature-specific state and actions. It exposes the
   small viewer API and uses one shared state across relevant app previews. Start from
   user actions and legal transitions. Include failure, rejection, retry and return
   paths required by the feature. Browser actions are a simulation, not backend proof.

Keep the packaged viewer generic. Do not rebuild tabs, field tables, flow cards, zoom,
downloads, themes, fonts or bundling for each feature. Apply Traba visual guidance to
app previews and Relay guidance to the surrounding document. Lead with the decision
and next action. Keep evidence and unsettled policy visible. Use both light and dark
themes and layouts that remain usable at narrow widths.

## Build and verify

```bash
python3 <skill-dir>/scripts/plan.py build <project-dir> --out <output-dir>
python3 <skill-dir>/scripts/plan.py validate <output-dir>
python3 <skill-dir>/scripts/plan.py serve <output-dir> --port 8771
```

The single build generates model JSON, Markdown, schema diagrams, authored flow SVGs,
viewer assets and `preview.html` with embedded fonts, scripts and downloads. Edit inputs
and rebuild. Never patch generated HTML, diagrams or Markdown by hand. Use a separate
output directory; repeated builds must yield the same preview bytes for the same input.

Follow [verification](references/verification.md). Open the actual `preview.html` using
the user's chosen browser, otherwise prefer Codex's in-app browser when available or
the host's browser tools. If the session has no browser tool, reuse a permitted existing
local browser harness. Exercise a complete cross-app path, failure and
eligibility cases, reset, diagrams/zoom, themes and narrow layout. Verify the downloaded
plan/model reflect the same input. Fix root causes in authored inputs or package tools.
For substantial designs, ask an independent reviewer to inspect the artifacts and
check load-bearing claims. Preserve their findings and verification evidence alongside
the project. Do not call a successful build visual or end-to-end QA.

## Deliver or publish

Return a link to the self-contained HTML and concise validation results. Keep authored
inputs and generated supporting files in the user's durable document workspace.
Publish only when requested, using the user's destination and
[Relay publication guidance](references/relay-publishing.md). Resolve a missing destination
from the authenticated user's library namespace. Read an existing destination before
replacing it. Publication does not authorize messaging reviewers or ongoing reviews.

To distribute this skill with its tools, run:

```bash
python3 <skill-dir>/scripts/plan.py package <outside-skill-dir>/product-plan-html.zip
```

Extract the resulting `product-plan-html/` directory into the target's user skills root.
Capability discovery resolves that machine's guidance and runtimes on its next run.
