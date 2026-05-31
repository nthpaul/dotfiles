# Council — example outputs

Reference shapes for synthesis. Verdicts are illustrative, not prescriptive.

---

## Example 1 — Pure reasoning (`/council Should we add a fourth caching layer in front of Postgres?`)

### Question

Should we add a dedicated application cache tier (Redis) in front of Postgres for read-heavy dashboards?

### Context

none — pure reasoning

### Council (abbreviated)

**Occam — Kill**  
For: faster reads if hit rate is high. Against: new failure mode, invalidation complexity, ops burden. Flip: proven p99 pain on DB with query shapes we cannot index.  
One line: Fix the query before you fix the network hop.

**Popper — Experiment**  
For: cache might cut load measurably. Against: no stated falsifier yet. Flip: baseline metrics + 1-week shadow cache with kill if hit rate < X.  
One line: Measure miss rate before you name it architecture.

*(…remaining minds…)*

### Agreement

- Postgres and query shape should be examined first
- Any cache needs explicit invalidation story and metrics

### Unresolved tensions

- **Carmack ↔ Occam:** Carmack may accept cache if DB is proven bottleneck; Occam wants index/query fix first
- **Leonardo ↔ Occam:** Leonardo wants a spike with real traffic; Occam wants zero new tier until spike on existing stack

### Verdict

**Recommendation:** Experiment  
**Confidence:** medium  
**Scope note:** If experiment runs, one service, one read path, 2-week timebox  
**Kill criteria:** Hit rate below 60% or p99 unchanged at equal error budget  
**Next experiment:** Record dashboard query p95/p99 + EXPLAIN on top 5; optional read-through prototype behind flag

### Minority report

Leonardo dissenting toward **Build** (bounded prototype): observation beats debate; run the spike even if Occam prefers zero new nouns.

---

## Example 2 — Grounded (`/council --context Should this PR add a RepositoryModule wrapper for a single table?`)

### Question

Should PR #4821 introduce `WidgetRepository` + global `RepositoryModule` registration for a one-table CRUD used in one service?

### Context

PR adds 4 files, 180 lines; no second consumer; team convention requires global repository module per Nest guidelines.

### Verdict (sketch)

**Recommendation:** Build (scoped)  
**Confidence:** high  
**Scope note:** Build the repository (team rule) but reject extra interfaces/abstractions until second caller exists  
**Kill criteria:** Second feature needs different persistence shape — merge repos then, not preemptively  
**Next experiment:** n/a — convention compliance with Occam-shaped minimal diff

### Minority report

Occam **Defer**: wait for second caller before new module surface — overruled by explicit team invariant (document as tension, not hidden).

---

## Example 3 — Quick mode (`/council --quick Should we rewrite the agent in Rust?`)

### Question

Should we rewrite the Neutron agent from TypeScript to Rust for performance?

### Council

Only Occam, Popper, Linus respond (full schema).

### Verdict

**Recommendation:** Kill  
**Confidence:** high  
**Kill criteria:** n/a — decision is negative unless profiling shows TS as proven bottleneck on critical path  
**Next experiment:** Profile one production run; Carmack-style metric before any rewrite discourse

### Minority report

None in quick mode if unanimous Kill — state "quick council unanimous" explicitly.
