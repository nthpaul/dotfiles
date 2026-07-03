---
name: graph-stack-merge-order
description: >-
  Determine merge order for multi-repo or dependent Graphite stacks (e.g. traba
  execution before the-matrix propose). Use before graph-stack-merge-safe when
  stacks span trabapro/traba and trabapro/the-matrix or have cross-PR contracts.
---

# Graphite stack merge order

Pick merge sequence **before** calling `graph-stack-merge-safe`.

## Default rules

### Within one repo

Merge Graphite stack **bottom → top** (parent PR before child).

```text
main ← stack1 ← stack2 ← stack3   →   merge #stack1, then #stack2, then #stack3
```

### Across repos

Merge **execution / backend first**, **agent / propose surface second** when a parameter or behavior flows:

```text
traba executor accepts param  →  the-matrix propose schema passes param
traba bugfix unblocks action  →  the-matrix uses that action reliably
```

**Wrong order:** matrix propose ships a new field before traba honors it → approvals fail at execution.

## Decision checklist

Answer before merging:

| Question | If yes → merge first |
|----------|----------------------|
| Does traba execute an ops action the matrix proposes? | **traba** stack |
| Does matrix only add prompts/evals with no traba change? | **the-matrix** only |
| Does matrix add a propose param traba must read at execute? | **traba** executor PR, then **matrix** propose PR |
| Are stacks fully independent? | Either order OK; prefer smaller/riskier repo first or traba if both touch ops execution |

## Typical Neutron ops approval pattern

From investigation → fix stacks:

1. **traba** — publish retry, executor param handling, execution guards
2. **the-matrix** — server-side propose preflight, eval/guidelines, propose schema

Document cross-repo deps in the matrix PR **Release Dependencies** checklist.

## Output format

Before merging, print an ordered list:

```markdown
## Merge order
1. trabapro/traba #7512 — <title>
2. trabapro/traba #7513 — <title>
3. trabapro/the-matrix #1801 — <title>
4. trabapro/the-matrix #1804 — <title>  (recovered PR if applicable)
5. trabapro/the-matrix #1805 — <title>
```

Then invoke **`graph-stack-merge-safe`** for each repo's sub-stack in that order.

## Pair with

- `graph-stack-merge-safe` — actual merge commands
- `graph-stack-merge-recover` — if order was wrong or branch deleted mid-merge
