---
name: concise-research-pdf
description: Create concise arXiv/LaTeX-style research briefs, decision memos, and technical reports as PDFs, with restrained serif typography, clear tables, vector diagrams, and precise citations. Use for this article style; not for slides, branded brochures, or exact publisher submission formats.
---

# Concise Research PDF

Produce an article the reader can use immediately: conclusion first, evidence nearby, only the detail needed to understand or act. This captures Paul's preferred visual style, not any past report's subject matter or conclusions. It is a normal personal skill, not an artifact template or an arXiv submission class.

## Editorial and visual choices

- Use a single column, readable Latin Modern serif body (11pt default), compact bold headings, enough margin (0.85in default), black text, and restrained ink-blue links. Match the user's paper-size request; the starter uses US Letter.
- Lead with the answer or decision and its limits. A short brief may need no abstract, table of contents, numbered sections, or separate title page. Length follows the material; never pad to a page quota.
- Keep paragraphs short and high signal. Use tables for genuine comparisons, and vector diagrams when relationships, transitions, ownership, or timing are easier to see than read. Label arrows; distinguish uncertainty with words or line styles as well as color. Split dense diagrams before shrinking labels.
- Use thin horizontal table rules, wrapped text columns, consistent units, and few colors. Keep body text at 10-11pt and table/diagram labels around 9-10pt or larger; shorten or split content before shrinking it.
- Include concrete schemas, state definitions, invariants, and failure/retry contracts when they answer the actual question. Do not add architecture sections to nontechnical briefs. Move supporting detail into an optional appendix without hiding critical caveats there.
- Cite evidence adjacent to the claim with descriptive linked titles and precise page/section or pinned code locations. Separate verified facts, proposals, assumptions, and open decisions. Never fabricate citations or carry old findings forward. Avoid opaque tool citation tokens in the PDF.

## Author and build

Use the PDF skill's artifact-operation hook and runtime discovery if that skill is available; keep this workflow usable with ordinary Python, Tectonic, and Poppler too. Honor an explicitly requested authoring format. Direct LaTeX is the default for this style; Pandoc is optional for prose-heavy Markdown, using the same visual settings rather than depending on a particular Pandoc template version.

The self-contained starter includes a neutral worked example with a table, vector diagram, links, and an optional appendix. Read and adapt [assets/brief.tex](assets/brief.tex); the shared style is [assets/concise-research.sty](assets/concise-research.sty). Replace all illustrative content and metadata for real work. Both files travel with the source.

Resolve this skill's directory from its loaded path. In these commands, `SKILL` means that directory and `OUT` is a dedicated artifact directory outside source repositories (for example, a user-selected work-docs directory or `~/Documents/Codex/briefs/<topic>`):

```bash
python3 "$SKILL/scripts/build_pdf.py" --init "$OUT/sources"
# Edit the copied brief.tex and, if necessary, the copied style.
python3 "$SKILL/scripts/build_pdf.py" --source "$OUT/sources/brief.tex" --output "$OUT/brief.pdf"
```

The helper refuses to overwrite starter sources, compiles from the source directory so relative assets work, keeps logs in `<output-stem>-build`, and renders **every page** to a fresh `<output-stem>-qa-*` directory at 150 DPI. Tools resolve from `PATH`; `--tectonic` and `--pdftoppm` accept explicit executable paths returned by runtime discovery. Tectonic may download TeX packages on its first build. A missing dependency or failed build stops with an actionable error; do not substitute an unverified result.

## Verify and deliver

Inspect all final page PNGs at readable resolution after the last edit. Check title balance, paragraph and heading breaks, table wrapping, diagram labels/arrows, citations, page numbering, clipping, and excess empty pages. A successful compiler run is not visual QA. The helper rejects overfull boxes and unresolved LaTeX references/citations; underfull warnings still need a human/model layout check.

Also extract text and inspect PDF link annotations with an available PDF library to verify expected sections, accurate metadata, and intended destinations. Check factual claims and links against their actual evidence; syntax checks cannot establish source accuracy. If rendering or inspection is unavailable, report that limitation rather than claiming QA passed.

Deliver the PDF and a compact account of validation; include sources or a preview when useful or requested. Preserve editable sources, the build log, and final page renders beside the artifact. Follow the active PDF skill's output-citation convention when applicable. Do not publish or send externally unless the user requests it.
