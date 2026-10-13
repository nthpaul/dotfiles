# Optional structured builder

Use this builder for technical plans that benefit from shared model/flow inputs,
generated diagrams, exports or connected previews. For a tailored document, author
HTML directly as described in SKILL.md. This contract applies only to the builder.

```bash
python3 <skill-dir>/scripts/plan.py scaffold <project-dir> --structured
python3 <skill-dir>/scripts/plan.py build <project-dir> --out <output-dir>
python3 <skill-dir>/scripts/plan.py validate <output-dir>
```

`--example injury-rtw` scaffolds the comprehensive example instead. Inputs and generated
outputs must be separate. Edit inputs and rebuild, rather than patching generated files.
The builder protects source directories and produces deterministic preview bytes.

## Plan

`plan.json` is an object. Include only relevant keys; absent arrays behave as empty.
The neutral scaffold includes only document metadata and a summary. No schema, flow,
diagram or preview is implied by scaffolding.

| Field | Shape and purpose |
| --- | --- |
| `document` | Optional `title`, `pageTitle`, `subtitle`, `date`, `brand`, `eyebrow`, `sampleLabel`; `sourceUrl` and `revision` record inspected evidence |
| `summary` | Optional `decision`, `nextAction`, `evidence` strings; `reuse`, `netNew`, `buildSequence` string arrays |
| `tables` | Proposed physical tables or extensions, described below |
| `referenceTables` | Existing FK targets as `{name, fields:[{name,type}]}`. Declare inspected referenced columns, not invented full schemas |
| `existing` | `{name, change, why}` entries describing existing tables/services to reuse |
| `flows` | `{id, title, summary, columns, steps, owner}` entries, described below |
| `schemaDiagrams` | Explicit selection of generated diagram IDs, `"model"` and/or `"model-full"`. Omitted or `[]` generates none |
| `decisions` | Settled design choices as strings |
| `questions` | Unresolved decisions as strings |
| `sources` | `[label, pathOrUrl]` pairs. Prefer precise repository paths with recorded revisions or source document links |

The viewer omits empty technical tabs, cards, counts and optional columns. Existing
reuse entries without a model appear in the overview. Authored `document.modelIntro`
or `notStored` can justify a model section; `flowContract` or `flowNotes` can justify
a flow section without a step table. Use direct HTML when another structure is clearer.

## Physical tables

A table has `name` and a nonempty `fields` array. Optional `purpose`, `constraints`
string array and `relationships` text explain important rules. A field has `name` and
physical `type`, with optional `rule` text and `relation` as `table.column`. Type text
includes `PK`, `FK` and `nullable` when applicable. Match inspected ID types and time
conventions. Validate declared foreign keys against actual targets.

Choose detail from the task. A full-schema request needs all relevant fields; an
extension can show only proposed fields and existing columns needed to explain it.
Use prose or direct HTML for a conceptual model without physical field types.

Table `storage` is `"new"` by default; `"extension"` identifies changes to an existing
table. For a single-column unique FK, `unique:true` renders one child per parent.
Explain composite uniqueness and enforcement in constraints; the generator does not
infer it from prose. Table and column names use SQL identifier characters.

## Flows

Choose column labels that explain this flow. The first column names the step:

```json
{
  "id": "filter",
  "title": "Narrow the visible results",
  "columns": ["Step", "User action", "Visible result"],
  "steps": [["Filter", "Select a status", "Matching rows remain visible"]]
}
```

Each step has one string per label. Omitted `columns` uses the technical example's
five labels: Step, Input, Read / decide, Write, Output / next action. Entirely blank
columns are hidden. Optional `owner` states verified ownership when it matters;
no ownership is assumed. Flow IDs use letters, numbers, `_` and `-`, starting with
a letter. An associated diagram can use the same ID for inline display.

Optional document explanations are `modelIntro`, `modelConventionsTitle`, `notStored`,
`flowContract`, `diagramNote` and `flowNotes:[{title,text,tone}]`. Tones are `violet`,
`green`, `orange`, `blue` or blank. Keep claims specific to the authored feature.

## Diagrams

`diagrams.json` is optional. Missing or `[]` adds no supplementary diagrams.
`schemaDiagrams` selects generated schema views only when tables are present:
`model` shows relationships; `model-full` shows every authored field. Choose one,
both or neither according to the information needed. Their content derives from
`plan.json`. A selected ID cannot also be authored in `diagrams.json`.

Supplementary graphs use one node/edge representation for DOT, SVG and Mermaid:

```json
{
  "id": "review",
  "title": "Review a request",
  "description": "Permission precedes the write.",
  "direction": "LR",
  "nodes": [
    {"id": "input", "label": "Request + actor", "kind": "input"},
    {"id": "check", "label": "Authorized and pending?", "kind": "decision"},
    {"id": "write", "label": "Persist approval", "kind": "state"}
  ],
  "edges": [
    {"from": "input", "to": "check"},
    {"from": "check", "to": "write", "label": "Yes"}
  ]
}
```

Node kinds are `new`, `existing`, `decision`, `data` and `result`. `input` aliases
`result`; `state` aliases `data`. IDs are unique SQL-style identifiers; edge endpoints
must exist. Direction is `TB`, `BT`, `LR` or `RL`.

Legacy recreation graphs may supply authored `dot` and `mermaid` strings, including
schema views. Compare their nodes, branches and labels when revising them. The injury
fixture explicitly retains these graphs to reproduce its comprehensive artifact.

The build always keeps internal plan JSON and a Markdown plan. It exposes a model
JSON download only with tables, and creates diagram exports only with diagrams.
Diagramless plans without a custom prototype need no Node runtime. Builds with Node
check script syntax; `build-info.json` records whether that check ran. Browser rendering
and source truth require separate verification.

## Optional preview surfaces

The document works without `prototype.js`. It shows only authored document content,
with no preview tabs, preview metric or scenario controls. The starter omits this file.
Add it only for requested previews or affected UI. Declare exactly the chosen surfaces;
there are no default app names. A later request can change this list. Any app, page,
role or tool can be a surface, and a single surface needs no companion apps.

The optional file is trusted local JavaScript, wrapped in an IIFE to avoid sharing
globals with the viewer. A static, single-surface preview needs only:

```javascript
window.PROTOTYPE = {
  surfaces: [{id:'review-tool',label:'Review tool'}],
  render(id) { return '<section class="card"><h2>Review tool</h2><p>Illustrative preview.</p></section>'; }
};
```

For an interactive preview, add the methods and scenarios the feature needs:

```javascript
window.PROTOTYPE = {
  surfaces: [{id:'review-tool',label:'Review tool'}],
  scenarios: [{id:'pending',label:'Pending review'}],
  initialScenario: 'pending',
  init() { loadScenario('pending'); },
  selectScenario: loadScenario,
  reset() { loadScenario(currentScenario); },
  status() { return {label:'Awaiting review',tone:'orange'}; },
  render(id) { return reviewToolView(); }
};
```

Each surface has a unique ID and its own display label. Reserve `overview`, `model`,
`flow` and `diagrams` for the viewer. `render(id)` returns that surface's HTML. For
multiple surfaces, route by ID and share state only where their journey requires it.
The Injury/RTW example explicitly selects worker, Ops and business surfaces; do not copy
that selection into unrelated features. An empty `surfaces` array also omits previews.

`init()` runs after `window.PlanDocument` exists. Do not initialize at
script load time. After an action updates state, call `window.PlanDocument.render()`.
`window.PlanDocument.setView(id)` navigates between declared surface/document tabs.
`scenarios`, `initialScenario`, `init`, `selectScenario`, `reset` and `status` are
optional. Scenario controls appear only on a surface with declared scenarios. Supply
`selectScenario` when using the scenario selector, and `reset` when offering reset.

Own feature forms, actions, dialogs and state in this file. The viewer owns navigation
for included content, optional scenario selection/reset, themes, flow tabs and diagram zoom.
An optional `overview()` returns a custom overview, but it must derive repeated counts
and decisions from `PLAN`, not maintain a second schema or flow definition. Reuse the
packaged CSS classes for phone frames, desktop shells, tables, badges and controls.

Escape text inserted into HTML. Keep stable IDs and scenarios for verification. No
network requests or production mutations are needed. Explain simulated behavior and
any differences in what each actor can see. Test the feature's actual invariants;
cross-surface assertions apply only when multiple surfaces interact. Do not infer backend
correctness from this demo.
