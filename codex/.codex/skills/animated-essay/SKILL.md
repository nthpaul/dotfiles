---
name: animated-essay
description: Explain a system, pipeline, protocol or incident as a long-form HTML essay with auto-playing, interactive figures, in the style of Cursor's engineering blog ("Git at any scale"). One narrow reading column, wide figure breakouts, small animated scenes where labeled packets travel between components, a store panel fills with the rows each step writes, a phase strip with Back / Pause / Next, and failure toggles. Use when asked for this doc style, an animated or interactive explainer, an engineering essay, or "make it like the Cursor blog". Not for dashboards, slide decks, static PDF briefs (concise-research-pdf), or Relay documents (relay-design).
---

# Animated Essay

Write an essay a reader finishes understanding how the system *moves*: what talks to what, in what order, what each step writes, and where it breaks. Prose carries the argument; figures show one mechanism each, playing on their own. Reference style: <https://cursor.com/blog/git-at-any-scale> (record it, don't just screenshot it; stills hide the animation).

## Editorial rules

- Open with the concrete thing a reader sees (a text message, a push, a request), then name the systems behind it and what the piece will show. No hero banner, no summary tiles.
- One section per stage of the flow, in the order data moves. Each section: plain prose that explains the mechanism, then the figure, then what to notice in it (especially what a toggle revealed).
- Name real tables, columns, states, config keys and functions in `code`. Every claim is grounded in code or data; mark anything not observed as inferred.
- Separate intended behavior from what the code or data shows. When they differ, say both plainly.
- End with "Where it breaks" (ranked gaps, each with who it hurts and the evidence), then the decisions only the reader can make, then a Reference section (state machines drawn on open, full lists) and a sources line naming code revision, data source, capture time, and which figures use illustrative values.
- Voice: first person plural, plain words, short sentences, light wit at most. No mannered devices (dash asides, "not X but Y", colon reveals). Follow the user's voice rules when they exist.

## Visual system (fixed, in `assets/essay.html`)

- Warm off-white page (`#f7f7f4`), near-black ink (`#26251e`), one sans (Geist) and one mono (Geist Mono). 645px column, 16px body, 36px regular-weight title, 22px bold section heads. Breadcrumb in a quiet left gutter. Collapsible table of contents.
- Figures break out to 966px in a bordered `--fig` panel. Inside: mono uppercase micro-labels, white node boxes with a colored left edge, dashed links, pastel packets (green / peach / blue / pink / yellow, each with a matching stroke), status dots (orange running, green done, pink failed, yellow waiting), a store panel, the phase strip (active phase orange-tinted), centered Back / Pause / Next, and a gray caption band.
- Accent orange only for the active phase, the playhead and "just changed". Light and dark themes are both defined; keep every color a token.

## Figures

Pick the pattern from `references/figures.md`; the engine API is documented there.

- **Scene** (default): nodes + links + phases of steps (`p` packet, `n` node status, `r` row chip, `j` JSON line, `f` custom). Use a rows store for "what gets written", a JSON store when one document holds the state, and the `draw` hook for grids/matrices.
- **Slider timeline**: hours or days on x, lanes for lifetimes and scheduled events; a slider or segmented control moves the inputs and the caption states the consequence. Best for "this ends before that fires" bugs.
- **Swimlanes**: real timestamped events per subject, playhead reveal, click a dot to read it. Label it as real data.
- 3–8 phases per scene, each with a one-sentence caption that says what happened, not what to look at. Toggles are real failure modes you found (a build in flight, a dropped call, a config edit), never decorative.
- Figures autoplay when 45% visible, pause when they leave, stop autoplaying once the reader pauses or steps. At rest (thumbnail, reduced motion) a scene shows its final phase. Say which figures use illustrative values.

## Workflow

1. Research the system first (code, data, docs). Collect the facts each figure needs: components, ordered steps, rows written, states, failure modes with evidence.
2. Outline sections and write a figure plan: for each figure, its pattern, nodes, phases, store tables, and toggles. Cut any figure that does not show motion or a write.
3. Start from the starter: `python3 "$SKILL/scripts/new_essay.py" --init "$OUT"` (`$SKILL` is this skill's directory; `$OUT` a work directory outside product repos, e.g. `~/projects/work-docs/experiments/<slug>`). Replace every example paragraph, figure and data row.
4. Large real data (timelines, gap lists, state machines) goes in a JSON file, injected at build: `python3 "$SKILL/scripts/new_essay.py" --source essay.html --data data.json --output built.html`. Keep phone numbers, tokens and secrets out.
5. QA by recording, not by screenshot alone: `node "$SKILL/scripts/qa_record.cjs" built.html "$OUT/qa"`. It records a walkthrough video (each figure plays, its first toggle flips), writes per-figure PNGs, contact sheets, `phone.png`, `dark.png` and `report.json` (console errors, 400px overflow offenders). Read the contact sheets and fix what they show: clipped labels, colliding text, packets landing off-target, empty stores, overflow. Re-run once after fixes.
6. Deliver: publish as an Artifact (or hand over the file if asked), link related artifacts, and give the user the video path. Keep sources and QA output next to each other.

## Gotchas already hit

- SVG text does not wrap: size columns and labels for the narrowest cell, put extra detail on a second line, shorten gate/status labels. Check the rightmost column against the viewBox width.
- Long identifiers in prose overflow phones; paragraphs use `overflow-wrap:anywhere`, segmented controls wrap.
- `.view{display:block}`-style rules beat the `hidden` attribute; keep `[hidden]{display:none!important}`.
- Mermaid: one `classDef`/`class` per line (semicolon chaining fails to parse); draw state machines on `<details>` open, with a transition table fallback.
- Automated clicks on dense dots can hit a neighbor; dispatch the click event in QA scripts.
- Load fonts from Google Fonts only and libraries from an allowed CDN pinned to an exact version (mermaid `10.9.1` via jsDelivr works).

A full worked example (Traba recruiting pipeline, seven figures) may exist at `~/projects/work-docs/experiments/recruiting-vetting-onboarding-map-2026-10/article.template.html`; read it for richer patterns (matrix `draw` hook, three-toggle JSON scene, onboarding slider timeline) when present.
