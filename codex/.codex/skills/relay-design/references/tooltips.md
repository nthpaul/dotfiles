# Tooltips in Relay docs

A tooltip must render on top of everything and never be clipped. Two things break that: the
browser's native tooltip (`title=`, `<abbr>`) does not survive Relay's render, and any ancestor
that is a clipping or stacking container (`overflow: hidden`, `overflow-x: auto`) cuts the bubble
off. Draw the bubble in CSS and keep clipping containers out of its ancestry.

## Markup

```html
<span class="tt" tabindex="0" data-tip="The routing policy selects the next step from the current requirements and evidence.">routing policy</span>
```

Add `tt-right` to the class for triggers in the right half of the page or a right-hand table column, so the bubble opens leftward instead of off-screen.

`tabindex="0"` lets a click or tap focus the trigger, which opens the bubble — hover alone fails
on touch. Keep the tip to plain text; for rich content (code, a link, a list) use a collapsible
`<details>` instead.

## CSS

```css
.tt{position:relative;cursor:help;text-decoration:underline dotted;
  text-underline-offset:.22em;text-decoration-thickness:1px}
/* Lift the trigger while open, so the bubble outranks elements painted after it. */
.tt:hover,.tt:focus{z-index:60}
.tt::after{content:attr(data-tip);position:absolute;left:0;top:calc(100% + .5rem);
  z-index:60;width:max-content;max-width:min(26rem,80vw);
  background:var(--ink);color:var(--paper);
  font-size:.82rem;line-height:1.45;font-weight:400;text-align:left;white-space:normal;
  text-transform:none;letter-spacing:normal;
  padding:.6rem .75rem;border-radius:6px;box-shadow:0 4px 14px rgba(0,0,0,.18);
  opacity:0;visibility:hidden;pointer-events:none;
  transition:opacity .12s ease .05s,visibility 0s linear .17s}
.tt:hover::after,.tt:focus::after{opacity:1;visibility:visible;transition:opacity .12s ease,visibility 0s}
/* Triggers in the right half of the page anchor the bubble to their right edge. */
.tt.tt-right::after{left:auto;right:0}
@media (max-width:560px){
  .tt::after,.tt.tt-right::after{
    position:fixed;left:10vw;right:auto;top:auto;bottom:1.5rem;
    width:80vw;max-width:80vw
  }
}
/* A table cell holding an open tooltip must outrank the rows after it. */
td:has(.tt:hover),td:has(.tt:focus){position:relative;z-index:60}
```

`--ink` and `--paper` are the doc's text and background tokens; the bubble inverts them, so it
reads in both themes.

## Containers

- Round table corners on the first and last cells, not with `overflow: hidden` on the table.
- Let wide tables wrap instead of wrapping them in an `overflow-x: auto` scroller.
- On narrow screens the tooltip uses a fixed bottom panel. Keep its ancestors free
  of transforms that would change the fixed-position containing block. Put required
  explanations in visible prose or `<details>`, not only in the tooltip.
- After publishing, hover a tooltip inside a table, one near the right edge, and one near the
  bottom of a collapsed section; each must show in full.
