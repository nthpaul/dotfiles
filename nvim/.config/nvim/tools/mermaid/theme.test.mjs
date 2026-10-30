import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Resvg } from '@resvg/resvg-js';
import { render } from 'pele';
import { colorizeSvg } from '../../../../../home/.local/share/mermaid-theme/theme.mjs';

function node(label, classes = '', style = '') {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">
    <g class="pele-node ${classes}" data-id="sample">
      <rect width="40" height="40" fill="#1d1d1d" style="${style}"/>
      <text x="50" y="50">${label}</text>
    </g></svg>`;
}

function center(svg, theme) {
  const rendered = new Resvg(colorizeSvg(svg, theme), { font: { loadSystemFonts: false } }).render();
  const offset = (20 * rendered.width + 20) * 4;
  return [...rendered.pixels.subarray(offset, offset + 4)];
}

test('rasterizes inferred success into themed colors in both backgrounds', () => {
  assert.deepEqual(center(node('Completed'), 'dark'), [25, 47, 28, 255]);
  assert.deepEqual(center(node('Completed'), 'neutral'), [228, 240, 231, 255]);
});

test('semantic classes override labels and neutral opts out', () => {
  assert.deepEqual(center(node('Failed', 'success'), 'dark'), [25, 47, 28, 255]);
  assert.deepEqual(center(node('Completed', 'neutral'), 'dark'), [29, 29, 29, 255]);
});

test('questions, negations, and component descriptions retain their neutral fill', () => {
  for (const label of ['No errors', 'Not ready', 'Error handler', 'Completed?']) {
    assert.deepEqual(center(node(label), 'dark'), [29, 29, 29, 255], label);
  }
});

test('explicit diagram fill wins over inferred and semantic colors', () => {
  assert.deepEqual(center(node('Failed', 'danger', 'fill:#00ffff'), 'dark'), [0, 255, 255, 255]);
});

test('author fill without a text color retains Pele contrast and borders', () => {
  const svg = render('flowchart TB\nA[Failed]\nstyle A fill:#ff0000').svg;
  const options = { font: { loadSystemFonts: false } };
  assert.equal(new Resvg(colorizeSvg(svg, 'dark'), options).toString(), new Resvg(svg, options).toString());
});

test('text-only shapes remain transparent instead of acquiring a box', () => {
  const svg = node('Failed').replace('fill="#1d1d1d"', 'fill="none" stroke="none"');
  assert.deepEqual(center(svg, 'dark'), [0, 0, 0, 0]);
});

test('explicit edge colors, arrowheads, widths, and labels survive unchanged', () => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">
    <g class="pele-edge" data-id="e" style="stroke:#00ffff;stroke-width:4">
      <path d="M2 20H30"/>
      <path class="pele-marker" d="M30 15L38 20L30 25Z" fill="#00ffff" stroke="none"/>
    </g>
    <g class="pele-edge-label" data-id="e"><text x="50" y="50">Failed</text></g>
  </svg>`;
  const options = { font: { loadSystemFonts: false } };
  const original = new Resvg(svg, options).render().pixels;
  const themed = new Resvg(colorizeSvg(svg, 'dark'), options).render().pixels;
  assert.deepEqual(themed, original);
});
