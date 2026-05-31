---
name: council
description: >-
  Convenes a council of seven thinkers (Aristotle, Leonardo, Linus, Carmack,
  Popper, Occam, Feynman) to debate whether something should exist. Use when
  the user invokes /council, asks for a deliberative pre-mortem, multi-perspective
  go/no-go, or "should we actually build this" before committing.
disable-model-invocation: true
---

# Council

Deliberative pre-mortem: seven fixed lenses debate whether something **should be** — not how to implement it.

## When to use

- Greenfield features, new abstractions, irreversible architecture
- Kill/keep decisions on existing systems
- Scope checks before large PRs or new agent skills/workflows
- Hypothesis validation before betting eng time

## When not to use

- Obvious bug fixes, typos, ticketed one-liners
- Anything with a clear checklist and no real tradeoff

## Invocation

```
/council <ask>
/council --quick <ask>       # Occam, Popper, Linus only
/council --context <ask>     # gather repo/PR context first, then full council
/council --debate <ask>      # two-round rebuttal (expensive; big bets only)
```

Parse flags in any order. Default roster: all seven minds.

## Step 0 — Classify the ask

Restate the question in one precise sentence. Classify:

| Type | Examples |
|------|----------|
| **Build** | New feature, service, layer, dependency |
| **Keep** | Retain code, pattern, process |
| **Merge** | Ship this PR / design direction |
| **Believe** | Metric, hypothesis, organizational claim |

Verdict vocabulary (each mind uses exactly one):

- **Build** — proceed as stated (maybe scoped)
- **Defer** — not now; name the blocker
- **Kill** — should not exist; name what replaces it
- **Experiment** — too uncertain to build; run cheapest falsifying test first

## Step 1 — Context (optional)

**Pure** (default): no codebase reads unless the ask embeds facts.

**`--context`**: before spawning minds, gather only what changes the debate:

- Associated PR (`gh pr view`, diff) if branch has one
- Files/paths the user named or that obviously own the ask
- Relevant config, schema, or prior art in-repo

Pass a **Context brief** (≤40 lines) to every subagent. Do not dump whole files.

## Step 2 — Spawn council members

Launch **one readonly subagent per active mind** in parallel (`Task` tool, `readonly: true`).

| Flag | Active minds |
|------|----------------|
| (default) | Aristotle, Leonardo, Linus, Carmack, Popper, Occam, Feynman |
| `--quick` | Occam, Popper, Linus |

**Model parity:** omit explicit model override so subagents inherit the parent model.

Each subagent prompt must include:

1. The classified ask (type + restated question)
2. Context brief (or "none — pure reasoning")
3. Instructions to read **only** its mind file (path below)
4. The **Member output schema** (below)
5. Explicit ban: no implementation, no code edits, no "how to build" beyond experiment sketch

Mind files (read before spawning that member):

- [minds/aristotle.md](minds/aristotle.md)
- [minds/leonardo.md](minds/leonardo.md)
- [minds/linus.md](minds/linus.md)
- [minds/carmack.md](minds/carmack.md)
- [minds/popper.md](minds/popper.md)
- [minds/occam.md](minds/occam.md)
- [minds/feynman.md](minds/feynman.md)

### Member output schema

Each mind returns markdown with these headings exactly:

```markdown
### <Name> — <Build|Defer|Kill|Experiment>

**For:** (strongest argument in favor)
**Against:** (strongest argument against — required even if verdict is Build)
**Flip condition:** (one concrete thing that would change this verdict)
**One line:** (≤20 words, quotable)
```

No biography. No implementation plan. Stay in character via **lens**, not cosplay.

## Step 3 — Debate round (`--debate` only)

After Round 1 completes:

1. Identify the **two most common verdicts** and the **strongest single objection** across all minds.
2. Re-spawn **all active minds** (same roster as Step 2) with:
   - Round 1 summaries (verdict + one line only per mind)
   - The strongest objection
   - Instruction: rebut or concede in ≤150 words; verdict may change
3. Use the same Member output schema for Round 2.

If platform limits block full parallel re-spawn, batch in groups of 3–4.

## Step 4 — Synthesize (parent agent only)

Do not spawn a "chair" subagent. Parent synthesizes using [examples.md](examples.md) as format reference.

Produce:

```markdown
## Question
<restated>

## Context
<brief or "none — pure reasoning">

## Council
<paste each mind's Round 1 block; if --debate, add ### Rebuttal subsection>

## Agreement
- bullets

## Unresolved tensions
- Name pairs (e.g. Leonardo ↔ Occam) and the tradeoff — do not fake consensus

## Verdict
**Recommendation:** Build | Defer | Kill | Experiment
**Confidence:** low | medium | high
**Scope note:** (smaller/shaped version if Build)
**Kill criteria:** (Popper-led — what observation means we were wrong)
**Next experiment:** (cheapest test, owner, timebox)

## Minority report
<Verdict + names of dissenters + why their concern shouldn't be ignored>
```

### Synthesis rules

- **Recommendation** follows weighted verdicts, not unanimity. One strong Kill from Popper + Occam outweighs three Build from enthusiasm.
- **Experiment** beats **Defer** when Popper or Feynman supplies a cheap falsifier.
- **Leonardo ↔ Occam** tension is expected: prototype vs. cut — surface it in Unresolved tensions.
- **Carmack ↔ Aristotle** tension: leverage vs. telos — surface it when both speak.
- Never hide dissent in Minority report.
- Do not implement, file tickets, or open PRs unless the user asks after the council finishes.

## Quality bar

- Every mind must fill **Against** even when voting Build.
- Popper's flip condition should be observational, not political.
- Occam must name what to delete or merge, not vague "simplify."
- Linus must say what you'd refuse to merge.
- Feynman must be understandable to a smart newcomer.

## Additional resources

- Mind lenses: [minds/](minds/)
- Sample outputs: [examples.md](examples.md)
