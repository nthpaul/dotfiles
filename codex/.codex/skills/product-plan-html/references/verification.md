# Verification

The build checks field/FK targets, graph structure and SVGs, embedded assets/downloads,
and bundle syntax. JavaScript syntax is checked during the build; `validate` checks
artifact structure and portability without requiring Node. These checks do not establish that a proposal matches production.
Check source-backed claims separately.

## Generated artifact

Run `plan.py validate <output-dir>`. Build the same project into a second empty output
directory and compare `preview.html` hashes. Generated content must be deterministic;
the separate capabilities report may differ across machines. Validate the copied
standalone HTML too. No local script, CSS, font, image or supporting download should
be required for the bundle to work.

For package changes, use:

```bash
python3 -m unittest discover -s <skill-dir>/tests -v
python3 <skill-dir>/scripts/plan.py --standalone detect
```

The bundled fixture tests compare the original plan's seven tables, 124 fields,
28 foreign keys, four flows and eight diagrams. They check the connected recovery
actions and the Markdown additions that formerly required manual edits. A new feature
needs its own realistic scenario assertions rather than the injury-specific tests.

## Browser

Serve the generated output on `127.0.0.1` with `plan.py serve`. Use the session's
available browser tools or an existing permitted harness, following their actual
documentation. With CUA, select/create an `iab` tab when Codex's browser is requested.
See [platforms](platforms.md) for host differences. Inspect the actual bundle, then:

1. Read overview, every table, each flow and diagram. Check labels, cardinality, table
   wrapping, graph zoom/scroll and downloaded sources.
   Include realistic long table names when checking summaries and SVG labels. Verify
   the Markdown export preserves the decision, evidence and optional explanatory prose.
2. Check that preview tabs match the selected surfaces exactly, including arbitrary
   IDs and labels. With no previews, confirm there is no preview metric, separator or
   scenario toolbar, and that the document sections still work.
3. When previews exist, run the main journey on those surfaces. If multiple surfaces
   interact, verify an input changes the next surface's projection. Exercise applicable
   rejected/failed paths and permission restrictions, and confirm a visible return path.
   Test reset when supplied. Static previews need no scenario controls or reset.
4. Check light, explicit dark and system theme behavior. Inspect a narrow window with
   diagrams and any selected previews or dialogs. Save relevant screenshots and assertions.

Use UI actions for actual QA. An isolated prototype state test complements the browser;
it does not replace rendered interaction checks. If the browser is unavailable, deliver
the built artifact and state exactly which rendering checks remain unverified.

## Injury/RTW recreation assertions

- Worker sample full note reaches the Ops queue as pending review.
- Approval releases the medical hold when no other open injury exists.
- Approval alone creates no sent business notice. Preview then explicit send creates it.
- A second injury or ordinary account restriction still prevents booking/clearance notice.
- Restricted notes stay blocked; expected return dates do not automatically clear injury.
- Illness cancellation permits booking. Sharing is limited to the consented document
  and named business; revoke or conversion removes access.
- Reset restores the selected scenario without leaking prior notices or consent.

Record observed results, artifact hashes, runtime versions and limitations in a short
verification report beside the recreated project. Keep the original document intact.
