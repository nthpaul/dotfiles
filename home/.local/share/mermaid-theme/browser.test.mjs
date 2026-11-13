import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { adaptAuthoredNodeColors } from './theme.mjs';

test('adapts authored node and cluster fills and explicit label colors', () => {
  const svg = '<svg><g class="pele-node warning"><polygon style="fill:#fff4d6;stroke:#b8860b;"/>'
    + '<text style="fill:#222;font-weight:700;">Contacted</text></g>'
    + '<g class="pele-cluster"><rect fill="#e8f0ff" fill-opacity="0.5"/>'
    + '<text fill="#222222">Group</text></g></svg>';
  const adapted = adaptAuthoredNodeColors(svg);
  assert.match(adapted, /--pele-author-fill:#fff4d6;fill:color-mix\(in srgb,var\(--pele-author-fill\) var\(--pele-author-fill-weight\),var\(--_bg\)\)/);
  assert.match(adapted, /--pele-author-fill:#e8f0ff/);
  assert.match(adapted, /--pele-author-text:#222;fill:color-mix\(in srgb,var\(--pele-author-text\) var\(--pele-author-text-weight\),var\(--_fg\)\)/);
  assert.match(adapted, /--pele-author-text:#222222/);
  assert.match(adapted, /stroke:#b8860b/);
  assert.match(adapted, /font-weight:700/);
  assert.match(adapted, /fill-opacity="0.5"/);
  assert.doesNotMatch(adapted, /style=";/);
  assert.equal(adaptAuthoredNodeColors(adapted), adapted);
});

test('leaves transparent colors, paint servers and edges untouched', () => {
  for (const fill of ['none', 'transparent', 'url(#gradient)', '#ffffff00', 'rgba(255,255,255,0)', 'rgb(255,255,255,0)']) {
    const svg = `<svg><g class="pele-node"><rect style="fill:${fill};"/><text style="fill:#222;">Label</text></g></svg>`;
    assert.equal(adaptAuthoredNodeColors(svg), svg, fill);
  }
  const edges = '<svg><g class="pele-edge" style="stroke:#00ffff;stroke-width:4">'
    + '<path style="fill:#fff4d6;"/></g><g class="pele-edge-label">'
    + '<rect fill="#fff4d6"/><text style="fill:#222;">Link</text></g></svg>';
  assert.equal(adaptAuthoredNodeColors(edges), edges);
});

test('only adapts direct children of a node or cluster group', () => {
  const nested = '<svg><g class="pele-node"><g class="icon"><path style="fill:#fff;"/></g>'
    + '<rect style="fill:#f5f5f5;"/><text>Node</text></g></svg>';
  const adapted = adaptAuthoredNodeColors(nested);
  assert.match(adapted, /<g class="icon"><path style="fill:#fff;"\/><\/g>/);
  assert.match(adapted, /--pele-author-fill:#f5f5f5/);
});

test('dark preview colors keep authored dark text above 4.5:1 contrast on the RCA fills', () => {
  const css = readFileSync(new URL('../../../../claude/.claude/hooks/mermaid-preview/diagram.css', import.meta.url), 'utf8');
  const dark = css.slice(css.indexOf('@media (prefers-color-scheme: dark)'));
  const property = (name) => dark.match(new RegExp(`${name}:\\s*([^;]+)`))?.[1];
  const rgb = (hex) => [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16));
  const mix = (color, background, weight) => rgb(color).map((channel, index) =>
    channel * weight + rgb(background)[index] * (1 - weight));
  const luminance = (channels) => channels.map((channel) => {
    const value = channel / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
  const fillWeight = parseFloat(property('--pele-author-fill-weight')) / 100;
  const textWeight = parseFloat(property('--pele-author-text-weight')) / 100;
  for (const fill of ['#fff4d6', '#e8f0ff', '#f5f5f5']) {
    const background = luminance(mix(fill, property('--pele-bg'), fillWeight));
    const text = luminance(mix('#222222', property('--pele-fg'), textWeight));
    const contrast = (text + 0.05) / (background + 0.05);
    assert.ok(contrast >= 4.5, `${fill}: ${contrast.toFixed(2)}:1`);
  }
});
