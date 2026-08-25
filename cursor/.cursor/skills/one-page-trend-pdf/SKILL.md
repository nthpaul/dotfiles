---
name: one-page-trend-pdf
description: >
  Builds a landscape letter PDF in the one-page trend poster style: claim
  headline, four KPI tiles, SVG grouped bars, week table, method footnote.
  Use when the user wants a week-on-week or period-on-period chart PDF, a
  trend poster, or a report that looks like the Neutron timeout 6-week
  landscape PDF. Do not use for long RCA writeups or portrait memos.
argument-hint: "[metric] [window, e.g. last 6 weeks]"
metadata:
  short-description: Landscape trend PDF, claim plus bars
---

# One-page trend PDF

Print a landscape letter poster. The picture carries the argument. The table is the skim layer.

Copy [template.html](template.html). Do not invent a new layout. Fill it. Print with [print.sh](print.sh). Open the PDF.

## Prose

Read these before you write a sentence:

- [technical-writing](/Users/ple/.cursor/plugins/cache/cursor-public/pstack/46125561306434d8a1d7745d540d8932ab0cd2a2/skills/technical-writing/SKILL.md)
- [pleasant-voice](/Users/ple/.cursor/skills/pleasant-voice/SKILL.md)
- [unslop](/Users/ple/.cursor/plugins/cache/cursor-public/pstack/46125561306434d8a1d7745d540d8932ab0cd2a2/skills/unslop/SKILL.md)

`technical-writing` owns the sentences. One thought each. Real symbols. "You" and the present tense. No em dashes. No slashes. No "this" pointing at a whole clause.

`pleasant-voice` owns the wrapping. The headline should sound like speech, not a briefing title. Contractions are fine. Do not slap. Do not restate the ask.

`unslop` last. If a sentence could sit in another project's PDF unchanged, cut it.

The Diátaxis mode is **explanation**. You are answering why the series moved. Do not turn the page into a how-to.

## What you gather first

1. Name the series in one noun phrase you will keep everywhere. Example: "unique timed-out request ids".
2. Pick a complete period. Monday–Sunday in America/New_York unless the user names another. Drop a partial current week from the last bar. Mention that week in the footnote.
3. Count the same way in every period. Prefer unique ids over log lines. Say the query in the subtitle.
4. If a second series exists (Slack posts, tickets), plot it as the rust bars. Say when it is a lower bound.

If you cannot get unique ids, say so in the footnote and plot what you have. Do not silently mix log lines in one week with unique ids in another.

## Page shape

Keep this stack, in this order:

1. **h1.** The claim. A full sentence. A number or a multiple belongs in it when you have one. "Timeout cases went 4× last week. The three weeks before that were empty."
2. **`.sub`.** What you counted, where, the period grain, the pull date. Real query text in `<code>`.
3. **Four `.kpi` tiles.** Big number, then two short lines of what it is. The last tile is the week-on-week change.
4. **`.legend`.** One swatch per series.
5. **SVG grouped bars.** Ink `#1a1a1a` for the primary series. Rust `#c45c26` for the second. Peak or last-period primary bar `#9b1d1d`. Zero weeks still get an axis label and a `0`. A 1-count bar is 4px tall so it stays visible.
6. **Table.** Period, primary count, vs prior period, second series, one-line note. Mark jumps with `class="wow-up"`.
7. **`.note`.** How you counted, what you excluded, what the chart does not prove.

No second page. No mermaid. No logos. No decorative emoji.

## Chart rules

Copy the SVG scaffold in [template.html](template.html).

- `viewBox="0 0 920 300"`. Plot baseline `y=240`. Max bar height `200`.
- Scale to the max primary value. `px = value / max * 200`.
- Label every bar. Put the period under the axis.
- Y ticks at 0, 25%, 50%, 75%, 100% of max. Use friendly numbers (24, 48, 72, 96), not 23.7.
- Two bars per period, primary then rust, 36px wide, 4px gap.

## Files

Write under `~/projects/work-docs/analytics/<slug>/` unless the user names another folder.

```
<slug>/
  trend.html
  <slug>-trend-YYYY-MM-DD.pdf
```

Print:

```bash
bash ~/.cursor/skills/one-page-trend-pdf/print.sh \
  "$HOME/projects/work-docs/analytics/<slug>/trend.html" \
  "$HOME/projects/work-docs/analytics/<slug>/<slug>-trend-YYYY-MM-DD.pdf"
```

Then `open` the PDF. If Chrome is missing, say so and leave the HTML.

## Do not

- Raise a timeout or change a cap in the footnote as if it were a finding you proved on this page.
- Pad empty early weeks with a different metric so the chart looks alive.
- Write a topic h1 ("Weekly timeout volume").
- Restyle the type. Headline is Iowan Old Style / Palatino. Chrome UI chrome stays off (`--no-pdf-header-footer`).
