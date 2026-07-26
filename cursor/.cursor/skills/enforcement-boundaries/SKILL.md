---
name: enforcement-boundaries
description: >-
  Severity triage and patterns for authz/guards, policy engines, feature-flag
  cutovers, and scripts on the build/deploy path. Prefer fixing true fail-open
  and cutover holes; treat nits as optional unless asked. Use when writing or
  reviewing guards, policies, permission cutovers, bulk mutation authz, monitor
  vs enforce modes, or build-chained sync/check scripts.
---

# Enforcement boundaries

Classify work by severity. Fix true issues by default. Do not expand a PR for
nits unless asked.

## Severity classes

| Class | Fix by default? | Meaning |
|---|---|---|
| **Correctness / fail-open** | Yes | Wrong allow, wrong resource, silent skip of a check, or build/deploy break |
| **Observability for enforce** | Yes | Would-deny / deny logs that misattribute the resource — signal for flipping enforce |
| **Product / cutover completeness** | Yes, or call out | Stronger sibling left ungated; allowlist→role cutover strands users; taxonomy mismatches economic effect |
| **Consistency / maintainability** | Usually | Enum exhaustiveness, kind parity across entry points, naming/suffixes, dead flag surfaces |
| **Nit / style** | No (unless asked) | Redundant checks, pass-through wrappers, unneeded casts, duplicate defense-in-depth |

Litmus: can a bad input or a future enum/map member **silently skip** a lock or
check? Silent skip → correctness, not style.

## Must-fix (true issues)

### Guard / handler input parity
Pre-handler authz must parse and normalize IDs the same way the handler does
(quotes, whitespace, CSV shape). Mismatch → nonexistent resources → spurious
deny, or monitor logs for the wrong id while the handler mutates the real one.

### Fail-open on map / enum drift
Action→policy maps and kind taxonomies must be compile-checked (`satisfies`,
exhaustive `switch` without `default`). Unmapped strings falling through to
"no check" silently disable enforcement. Prefer enums / typed maps over raw
string literals when the value gates a check.

### Batch deny / monitor must name the offender
Do not collapse a batch deny to `ids[0]`. Log (and throw context for) the
resource that actually failed, including decision context used for the enforce
flip.

### Bound fan-out at the authz boundary
Per-id heavy queries on bulk routes need concurrency limits (e.g. `pLimit`) or
batch APIs. Independent loads in a single-id path should `Promise.all`. Authz
often runs on every stamped request, including monitor mode.

### Never swallow unexpected lookup failures
Empty `catch {}` on throw-on-missing lookups turns transient errors into
role-less / capability-less stubs and unexplained denials. Log unexpected
failures with ids; only treat genuine not-found as soft degradation when that
is intentional.

### Scripts on the build path must tolerate deploy context
If a check/sync is chained from `build` / codegen, it must no-op or skip when
sources outside the Docker/build context are absent (committed generated output
is enough there). PR CI often cannot catch merge-time image builds.

### Cutover completeness
- Gating a weaker mutation while leaving a stronger sibling on the same auth
  surface ungated is a product hole — stamp it or justify the gap in the PR.
- Replacing an email/user allowlist with roles: verify active allowlisted users
  are covered before FE cutover; call out stranded users.
- Taxonomy must match economic effect (e.g. pay-reversing status changes are
  not "roster only" if they reverse pay).

## Consistency (fix when cheap)

- Same operation via multiple entry points (HTTP, job runner, agent executor)
  should stamp the same mutation kind / policy.
- Exhaustive enum branching for resource-source / kind resolution.
- Do not add client flag-enum members the client never reads; retire orphaned
  flags when the last consumer leaves.
- Layer/file suffixes that match role (`*.types.ts`, `*.service.ts`, etc.).
- Explicit return types on new functions.
- UI maps keyed by list **index** silently mis-map on reorder — key by stable
  identity or one shared options+mutation structure.
- Visible UI changes need PR evidence (touched surfaces + screenshots), not "N/A".

## Nits (skip unless asked or already touching the lines)

- Redundant `'x' in obj` when `obj.x === undefined` covers absence
- `?? ''` / `?.` where control flow already guarantees a value
- Widening casts the types do not need
- One-line pass-through wrappers
- Extracting a helper for a 3× duplicated expression
- Extra "defense in depth" copies of a guard the caller already applies
