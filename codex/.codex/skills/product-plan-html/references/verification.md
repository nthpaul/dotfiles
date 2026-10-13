# Verification

Verify the content and controls actually included. The validator checks portability
for authored HTML; structured builds also check selected schema/FK references, graphs,
SVGs and agreement between inputs, exports and embedded downloads. It does not prove
source truth, visual quality or backend behavior.

## Artifact checks

Run `plan.py validate <html-file>` for a tailored document, or `validate <output-dir>`
for a structured build. Copy the standalone HTML away from its supporting files and
validate it too. Actual runtime assets and downloadable files must be embedded; ordinary
source links can remain links. When using the structured builder, compare two builds'
`preview.html` hashes for determinism and inspect `build-info.json` for syntax-check status.
For tailored interactive HTML, syntax-check its authored scripts with an available Node
runtime when useful; no fixed script count is required.

Check that each included section serves the request. Absent schema, flows, diagrams or
previews should leave no empty navigation destinations, placeholder rows or unrelated
ownership claims. If full physical schema was requested, check completeness against
the requirements and authoritative schema. Otherwise check only the represented fields
and relationships. A diagram should add understanding or satisfy the requested format.

For package changes, run:

```bash
python3 -m unittest discover -s <skill-dir>/tests -v
python3 <skill-dir>/scripts/plan.py --standalone detect
```

Use realistic cases with different scopes: a short decision memo, a client-side journey,
a schema change with selected diagrams, and the comprehensive recreation fixture. Tests
must verify meaningful content and omission, not impose the example's layout everywhere.

## Browser checks

Serve the document on `127.0.0.1` with `plan.py serve`. Use the user's chosen browser or
the session's exposed browser tools, following their actual documentation. With CUA,
select/create an `iab` tab when Codex's browser is requested. See [platforms](platforms.md).

Read the actual document and follow its reading order. Check light, explicit dark and
system themes, narrow layout, wrapping, contrast and keyboard navigation. Exercise the
controls present, such as navigation, collapsed detail, diagram zoom and downloads.
Confirm downloaded content agrees with the document. Save relevant screenshots/results.

If previews exist, run their main journey and applicable failures, permissions and return
paths. Check reset only when supplied, and shared state only when multiple surfaces
interact. Static previews need no scenarios or reset. A runtime state test complements
rendered UI checks. If browser access is unavailable, state which rendering checks remain
unverified rather than calling a build visual or end-to-end QA.

For substantial designs, use an independent reviewer for load-bearing claims and document
fit. Keep evidence, artifact hashes, runtime versions and limitations beside the project.

## Injury/RTW recreation

The explicitly comprehensive fixture preserves seven tables, 124 fields, 28 foreign
keys, four flows, eight diagrams and its worker/Ops/business previews. Its scenario checks
cover medical holds, approval, explicit business notices, multiple injuries, account
restrictions, illness booking, document consent, revocation, conversion and reset.
Use [the fixture manifest](../assets/examples/injury-rtw/fixture-manifest.json) for exact
assertions. These feature-specific checks do not define requirements for other plans.
