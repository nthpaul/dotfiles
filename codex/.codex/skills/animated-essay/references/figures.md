# Figure patterns and engine API

All code lives inline in `assets/essay.html`. Each figure mounts into an empty `<div id="...">` placed in the column; the figure widens itself to 966px.

## Scene

```js
Scene({
  id: 'fig-send', w: 940, h: 360, label: 'aria label',
  nodes: { sender: {x, y, w, h, title, sub, tone, dot} },   // tone: g o b p y (left edge + packet color); dot: idle run ok bad wait
  links: [['sender','ep'], ['sender','store']],                // 'store' is a valid endpoint
  labels: [[x, y, 'MICRO LABEL', 'middle']],                   // optional static labels
  store: { x, y, w, h, title, counter: true,                   // rows store: one line per table, chips append
           tables: ['deliveries', 'delivery_attempts'] },
  // or: store: { ..., kind: 'json', json: { status: '"NEW"', attempts: '0' } }   // JSON document; changed line highlights
  draw: (state, g, opt) => { /* custom SVG for grids; read flags you set with f-steps in state.x */ },
  controls: [ {type:'chk', key:'timeout', label:'Endpoint times out'},
              {type:'seg', key:'reply', label:'Worker says', options:[['a','A'],['b','B']]} ],
  init: { timeout: false, reply: 'a' },
  caption: 'Optional text appended to every phase caption.',
  phases: opt => [ { name: 'Post', cap: 'One sentence: what happened.', steps: [...] } ]   // rebuilt when a control changes
});
```

Steps run in order inside a phase:

| Step | Effect |
| --- | --- |
| `{p:[from, to, 'LABEL', tone]}` | A packet travels the link (eased, 450–900 ms). |
| `{n:[node, 'sub text', dot]}` | Set a node's subtitle (`\n` for a second line) and dot. `bad` also turns the box pink and dashed. |
| `{r:[table, 'text', op]}` | Append a chip to a store table. op INSERT green, UPDATE blue, UPSERT yellow, DELETE pink; the newest chip gets an accent outline. |
| `{j:[key, 'value']}` | Set a JSON store line and highlight it. |
| `{f:(state, opt) => {}}` | Mutate `state.x` for `draw`. |
| `{w: ms}` | Pause. |

Behavior: autoplay at 45% visibility, loops (1.3 s between phases, 1.5 s before restarting), pauses off-screen, never resumes after the reader pauses, clicks a phase or steps. Phase buttons jump to the end state of that phase. Reduced motion: no tweens, no autoplay.

Layout tips: viewBox 940 wide; nodes about 150–180 × 46–56; keep nodes left, store right (x ≈ 420–450). Keep links few; every link a packet uses must exist or the packet still flies but looks unanchored. Chip text ~5.1 px per character at 8 px mono.

## Slider timeline (bespoke, ~60 lines)

Use when the bug is timing: something ends before something else fires.

- x axis in hours (or days) since a reference event; gridlines every 12 units; micro-label "HOURS SINCE HANDOFF →".
- One lane per lifetime or schedule: a lifetime is a tinted bar ending in a tick and an "ENDED · reason" label; scheduled events are small boxes, green when they fire, pink dashed with ✕ when they fall after the lifetime ended.
- Controls on top: a segmented outcome selector, a range slider for the moving input, a checkbox for an operator action. Redraw on input; animate only a looping playhead.
- The caption computes the consequence ("1 of 2 reminders never send") from the same model the drawing uses.

## Swimlanes

```js
Swimlanes({ id, t0, t1, lanes: [{ name, sub, events: [{ at, kind, actor, text }] }], caption });
```

Kinds map to colors (message blue, error pink, vetting/call orange, onboarding/offer green, tool yellow, other muted); actor `worker` draws hollow. Events before `t0` sit at the left edge. Detail band shows the clicked event. Playhead reveals dots once when scrolled into view.

## State machines in the Reference section

Render each machine in a `<details>`; draw its Mermaid `stateDiagram-v2` only on first open, with a transition table underneath as the fallback. Sanitize labels (strip `" ; : # { } < > [ ] |`), one statement per line.
