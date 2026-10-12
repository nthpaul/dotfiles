# Authored inputs

Keep project inputs separate from generated outputs. All paths below are relative to
the project. The build reads `plan.json`, optional `diagrams.json` and optional
`prototype.js`. Save requirements and source notes alongside them for the next author.

## Plan

`plan.json` is an object with these fields. Run `scaffold` for a complete small example.

| Field | Shape and purpose |
| --- | --- |
| `document` | `title`, `pageTitle`, `subtitle`, `date`, `brand`, `eyebrow`, `sampleLabel`; `sourceUrl` and `revision` record the input and inspected checkout |
| `summary` | `decision`, `nextAction` and `evidence` are strings; `reuse`, `netNew` and `buildSequence` are arrays of strings |
| `tables` | Array of proposed table definitions shown below |
| `referenceTables` | Existing FK targets, each `{name, fields:[{name,type}]}`. Include the actual referenced columns; these are declarations of inspected targets, not proposed full schemas |
| `existing` | Array of `{name, change, why}` describing existing tables/services to reuse or extend |
| `flows` | Array of `{id, title, summary, steps}` with the five-column step format below |
| `decisions` | Settled design choices as strings |
| `questions` | Unresolved policy or design decisions as strings |
| `sources` | Array of `[label, pathOrUrl]`. Prefer repository-relative paths plus recorded revisions; preserve citations to precise files or source documents |

Every table has `{name, purpose, fields, constraints, relationships}`. Every field has
`{name, type, rule, relation}`. `type` is the physical storage type, with `PK`, `FK` or
`nullable` explicitly stated when applicable. `rule` explains its purpose, values,
ownership or invariants. `relation` is `table.column`, or `""` for no FK. Give nullable
and composite foreign keys their enforcement rules in constraints. `constraints` is
an array of strings; `relationships` describes cardinality and cross-table behavior.
Use existing ID types rather than assuming UUID.

Each flow step is exactly five strings:

```json
["Step name", "Input + actor", "Reads and decisions", "Transaction writes", "Output / next action"]
```

Flow IDs and diagram IDs use letters, numbers, `_` and `-`, starting with a letter.
The corresponding flow diagram should use the same ID. Table and column names use SQL
identifier characters, starting with a letter or `_`.
For a single-column unique FK, add `unique:true` to that field to render one child per
parent. Composite uniqueness belongs in constraints and needs explicit explanation;
the generator does not infer a unique FK from constraint prose.

Optional document fields add feature-specific explanations without changing the viewer:
`modelIntro`, `modelConventionsTitle`, `notStored`, `flowContract`, `diagramNote`, and
`flowNotes:[{title,text,tone}]`. Tones are `violet`, `green`, `orange`, `blue` or blank.
The bundled recreation also includes metadata recording the original artifact.

## Diagrams

`diagrams.json` is an array. New graphs use a shared node/edge representation:

```json
{
  "id": "review",
  "title": "Review a request",
  "description": "Permission and state precede the write.",
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

The builder generates schema overview `model` and every-field diagram `model-full`
from the plan. Do not manually author their contents for new plans. The recreation
fixture retains canonical originals of these graphs for comparison with that artifact.
Legacy graphs may instead supply `dot` and `mermaid` strings. They are separate authored
representations; compare their nodes, branches and labels before changing them.
Supported node kinds are `new`, `existing`, `decision`, `data` and `result`.
`input` aliases `result`; `state` aliases `data`. Use `result` for outputs and failure
results. Node IDs must be unique SQL-style identifiers, and every edge endpoint must
name a declared node. Direction is `TB`, `BT`, `LR` or `RL`.

## Optional preview surfaces

The document works without `prototype.js`: it shows overview, model, flow and diagrams,
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

Own the feature forms, actions, dialogs and state in this file. The viewer owns document
navigation, optional scenario selection/reset, theme selection, flow tabs and diagram zoom.
An optional `overview()` returns a custom overview, but it must derive repeated counts
and decisions from `PLAN`, not maintain a second schema or flow definition. Reuse the
packaged CSS classes for phone frames, desktop shells, tables, badges and controls.

Escape text inserted into HTML. Keep stable IDs and scenarios for verification. No
network requests or production mutations are needed. Explain simulated behavior and
any differences in what each actor can see. Test the feature's actual invariants;
cross-surface assertions apply only when multiple surfaces interact. Do not infer backend
correctness from this demo.
