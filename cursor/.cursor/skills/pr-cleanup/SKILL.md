---
name: pr-cleanup
description: >-
  Run before requesting review on multi-step React flows and Nest handlers (forms,
  wizards, uploads, feature-flagged UI). Generic checklist distilled from prior
  PR feedback to shorten review iteration. Invoke as /pr-cleanup or pr-cleanup.
---

# PR cleanup

Use **after** implementation, **before** push or re-request review. Scan changed files against the rules below; fix or note intentional deferrals in the PR.

## How to run this checklist (thorough pass)

Do **not** spot-check only the “interesting” hunks. For every PR:

1. **Build the file list** — diff against merge base (e.g. `git diff --name-only "$(git merge-base HEAD origin/main)"..HEAD`) and filter to code you own (`*.tsx`, `*.ts`, server `*.ts`).
2. **Walk section-by-section** — every heading below applies to the diff unless you document an explicit deferral with rationale in the PR.
3. **Ops-console theme pass is mandatory** — see **Ops-console UI / theme** and run the greps there on **changed** `.tsx` files. Missing `useTrabaTheme()` on colored/surfaced inline styles is a common review loop (dark mode, BUGBOT half-migration).
4. **Automated gates** — after edits: targeted `nx run <project>:lint`, `tsc --noEmit -p <app>/tsconfig.json`, `oxfmt` / `format:check`, and tests for touched packages.

## Multi-step create / update flows (API + UI)

- **No silent work after idempotent “already exists”**: If the server returns duplicate/skipped/no-op, **do not** run follow-up mutations that would overwrite existing persisted state.
- **Prefer server-aligned orchestration**: When the API supports doing related work in **one** coherent call (e.g. create parent with pre-collected child IDs), prefer that over ad hoc sequences (create empty → side effects → second call to attach) unless product requires the split.
- **Explicit handler outcomes**: Helpers that orchestrate steps should make success vs no-op vs failure obvious to callers (e.g. return whether downstream steps should run).
- **Confirm / review UI**: Close confirmation surfaces **only** after the intended mutation path succeeds; keep open or reset on failure.

## File uploads and linkage to domain entities

- **Partial failure mid-pipeline**: If early uploads succeed and a later step throws, avoid orphan persisted blobs/records with no recovery story—persist accumulated foreign keys before surfacing the error, or design idempotent retry so operators do not blindly duplicate uploads.
- **Empty collection semantics**: If “replace attachments” exists, define behavior for **`ids: []`** (clear all vs no-op). Prefer explicit clear or an explicit flag—avoid silent retention that contradicts the UI.
- **Errors match the failing phase**: Toast/dialog **titles** (and primary copy) must reflect what actually failed (e.g. “attach files” vs “create record”) when the parent entity may already exist.

## Backend services (Nest / similar)

- **Atomic related writes**: Updates that must succeed or fail together (e.g. main row + join-table replaces) belong in **one transaction**, or the weaker path must be explicitly best-effort with a consistent HTTP/success contract. Avoid partial persist + error that encourages duplicate retries.
- **Optional PATCH fields**: Do not map omitted optional DTO fields into ORM payloads such that **`undefined` clears** columns the client never intended to touch—patch only defined fields.
- **Validate near write**: Validation outside a transaction and persistence inside another invites TOCTOU; colocate checks with writes or enforce via DB constraints—or document intentional reuse of an established pattern.

## TypeScript client hooks and API params

- Do **not** widen finite enums/unions to **`string[]`** for convenience when a **named union** preserves compile-time safety (e.g. `(LegacyReason | NewReason)[]`).

## Single source of truth (labels, maps, constants)

- **No divergent copies**: Category order, labels, emoji, and taxonomy maps should live in **one canonical module** (e.g. shared types/utils)—screens that “create” vs “edit” must not fork divergent constants.
- **No duplicated formatters**: Identical display helpers across screens belong in **shared utils** with one implementation.
- **Cross-tier alignment**: Avoid defining the same enum/map separately in frontend and backend—export or generate from one source consumers share.

## TypeScript enums and switches

- Switches on TypeScript enums must be **exhaustive**—**no `default`** that hides missing cases when new enum members are added (matches common repo / Bugbot rules).

## Feature flags, modals, and multi-step UI

- **Flag resolution timing**: Effects keyed on live flag reads can reset wizard or modal state when the flag resolves late—snapshot at open, wait for provider readiness, or avoid wiping user input without notice.
- **Re-init when dependencies flip**: If form UI branches on a flag **and** loaded entity data, ensure state **re-initializes** when the flag becomes true after first paint (avoid empty required selections on entities that already have stored values).
- **Wizard navigation**: Review/final steps should allow **Back** to earlier steps without forcing full dismiss and data loss.
- **Ambiguous persisted strings**: Lookup tables that classify stored strings into “new taxonomy” vs “legacy” must handle **key collisions** between old and new vocabularies—misclassification breaks edit flows.

## Forms and validation

- **Tighter rules on edit**: When raising minimum lengths or new required fields, **grandfather** existing short values when the user is not rewriting that field—or add inline copy explaining why expansion is required.

## Ops-console UI / theme

- **One theme pattern per file**: Do **not** mix `import { theme } from '@traba/theme'` with `useTrabaTheme()` in the **same** `.tsx` file for rendered UI. Pick **one**: typically **`useTrabaTheme()`** for any component that reads **`theme.colors.*`**, **`theme.surface.*`**, or other tokens that must track ops-console dark mode. Reserve static `import { theme } from '@traba/theme'` for **module-level** helpers that only need mode-invariant values (`theme.space.*`, `theme.media.*`) **without** coloring surfaces — and avoid importing static `theme` into files that already call `useTrabaTheme()` for colors.
- **Mandatory grep on changed ops-console `.tsx` files** (fix violations before re-requesting review):

```bash
# Static theme import in files you changed (review each hit — prefer useTrabaTheme for JSX styling)
git diff --name-only "$(git merge-base HEAD origin/main)"..HEAD -- '*.tsx' | tr '\n' '\0' | xargs -0 rg 'from '\''@traba/theme'\''' || true

# Mixed pattern in one file (both static theme import and hook — should be empty after cleanup)
git diff --name-only "$(git merge-base HEAD origin/main)"..HEAD -- '*.tsx' | tr '\n' '\0' | xargs -0 rg -l 'from '\''@traba/theme'\''' | xargs rg -l 'useTrabaTheme' || true
```

If a file legitimately needs both, leave a **one-line PR note** explaining why (rare).

- **Reuse primitives**: Prefer shared components (`Text`, existing upload widgets). If UX diverges materially, **document why** in the PR (reuse audit).
- **Design tokens**: Typography and spacing use **theme** (or component props), not ad hoc px—unless matching an audited exception.
- **Non-obvious patterns**: Brief comment for choices like **WeakMap**-backed stable ids so GC and intent are clear.

## Lists and React keys

- Identity from **`name + size + lastModified`** (alone) is fragile for keys and dedupe. Prefer a **stable per-session id** (WeakMap, counter, UUID).

## Mutations and feedback

- Avoid unexplained “skip success toast” branches unless product explicitly wants silence.

## Upload metadata

- Avoid stamping every file with a generic type/description when downstream filters audit by category; use accurate taxonomy or document limitation + ticket.

## Comments and TODOs

- Remove **redundant** commentary (restates code or duplicates constants elsewhere).
- Deferred work: **`TODO(ENG-xxxxx):`** plus issue URL—prefer a ticket over project-only links.

## Optional repo-wide greps

Adjust paths to match your change set:

```bash
# Suspicious widening to plain strings for enumerated domains
rg ": string\[\]" apps/ops-console/src/hooks -n

# Enum switches worth spot-checking for default fallthrough
rg "default:\s*$" apps/ops-console/src -g '*.tsx' -n
```

---

When adding rules, append a **one-line provenance** (PR or ticket) so the list stays traceable without tying the skill to one feature.
