# Astra and Grok orchestration plan

Proposed architecture, 13 September 2026. This records the design; it does not install an orchestration runtime or change existing skills.

Read [the six-page PDF](astra-grok-plan.pdf) for five vector diagrams covering services, data structures, normal assignments, mediated broadcasts, and urgent replanning. The plan also defines delivery and recovery contracts, tmux ownership, implementation stages, and validation gates.

## Editable sources and rebuild

The portable LaTeX source and style are in [sources/](sources/). Install Tectonic and Poppler, then run from this directory:

```sh
python3 sources/build_pdf.py --source sources/brief.tex --output astra-grok-plan.pdf
```

The helper checks for overfull boxes and unresolved references, preserves compilation logs, and renders every page at 150 DPI. Inspect all newly rendered pages after changes; compilation alone is not visual validation.

## Evidence and validation

[evidence/](evidence/) preserves the local source snapshots, SHA-256 provenance manifest, and CLI help used in the plan. External references are linked in the PDF. These observations document advertised capabilities, not tested runtime behavior.

[verification.json](verification.json) records the delivered PDF hash, six-page count, metadata, four external citation destinations, text checks, and visual inspection of every final page. Build logs and renders remain with the original artifact outside the repository; new rebuilds generate them locally.
