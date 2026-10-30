import assert from 'node:assert/strict';
import { test } from 'node:test';
import { applyTones, Tone, toneOf } from './tone.mjs';

test('infers clear states and short subjects followed by a state', () => {
  for (const [label, tone] of [
    ['PaymentFailed', Tone.Danger],
    ['payment_failed', Tone.Danger],
    ['timed out', Tone.Danger],
    ['attempts exhausted', Tone.Danger],
    ['request rejected', Tone.Danger],
    ['Retrying', Tone.Warning],
    ['Queued', Tone.Warning],
    ['approval pending', Tone.Warning],
    ['Done', Tone.Success],
    ['build completed', Tone.Success],
    ['Checks passed', Tone.Success],
    ['merged', Tone.Success],
    ['Running', Tone.Active],
    ['job in progress', Tone.Active],
    ['Cancelled', Tone.Muted],
    ['job skipped', Tone.Muted],
    ['No-op', Tone.Muted],
  ]) assert.equal(toneOf([], label), tone, label);
});

test('leaves decisions, negations, component names, and mixed descriptions neutral', () => {
  for (const label of [
    'No errors', 'Not ready', 'Error handler', 'Ready to retry', 'retry after error',
    'Failed requests?', 'Errors？', 'Is healthy?', 'Parse request', 'token book',
    'Handle errors', 'Ignore errors', 'Failed requests queued', 'Running job failed',
    'Wait until ready', 'No-op handler', 'New worker', 'Removed',
    'This very long payment workflow eventually failed',
  ]) assert.equal(toneOf([], label), null, label);
});

test('explicit semantic classes win, and neutral opts out', () => {
  assert.equal(toneOf(['changed'], 'Done'), Tone.Changed);
  assert.equal(toneOf(['Fail'], 'No errors'), Tone.Danger);
  assert.equal(toneOf(['success'], 'Failed requests?'), Tone.Success);
  assert.equal(toneOf(['added'], 'Parse request'), Tone.Changed);
  assert.equal(toneOf(['deleted'], 'Parse request'), Tone.Removed);
  assert.equal(toneOf(['neutral'], 'PaymentFailed'), null);
  assert.equal(toneOf(['success', 'neutral'], 'Done'), null);
  assert.equal(toneOf(['constructor'], 'Parse request'), null);
});

test('tags nodes and groups while preserving shape metadata and unrelated attributes', () => {
  const svg = '<svg><g class="pele-cluster" data-id="jobs"><text>Queued</text></g>'
    + '<g class="pele-node pele-state changed" data-id="Running" transform="translate(4,8)"><text>Running</text></g></svg>';
  const result = applyTones(svg);
  assert.match(result, /class="pele-cluster pele-tone-warning" data-id="jobs"/);
  assert.match(result, /class="pele-node pele-state changed pele-tone-changed" data-id="Running" transform="translate\(4,8\)"/);
});

test('does not borrow a neighbor label, and reads all lines of its own label', () => {
  const svg = '<svg><g class="pele-node pele-state-start" data-id="root_start"><circle r="7"/></g>'
    + '<g class="pele-node" data-id="handler"><text>Error</text><text>handler</text></g>'
    + '<g class="pele-node" data-id="done"><text>Done</text></g></svg>';
  const result = applyTones(svg);
  assert.match(result, /class="pele-node pele-state-start" data-id="root_start"/);
  assert.match(result, /class="pele-node" data-id="handler"/);
  assert.match(result, /class="pele-node pele-tone-success" data-id="done"/);
});

test('gives an edge and its label the same inferred or explicit tone', () => {
  const svg = '<svg><g class="pele-edge pele-transition" data-id="timeout"><path d="M0 0"/></g>'
    + '<g class="pele-edge-label" data-id="timeout"><text>timed out</text></g>'
    + '<g class="pele-edge success" data-id="explicit"><path d="M0 0"/></g>'
    + '<g class="pele-edge-label" data-id="explicit"><text>No errors</text></g></svg>';
  const result = applyTones(svg);
  assert.match(result, /class="pele-edge pele-transition pele-tone-danger" data-id="timeout"/);
  assert.match(result, /class="pele-edge-label pele-tone-danger" data-id="timeout"/);
  assert.match(result, /class="pele-edge success pele-tone-success" data-id="explicit"/);
  assert.match(result, /class="pele-edge-label pele-tone-success" data-id="explicit"/);
});

test('an explicit neutral edge also keeps its outcome label neutral', () => {
  const svg = '<svg><g class="pele-edge neutral" data-id="e1"><path d="M0 0"/></g>'
    + '<g class="pele-edge-label" data-id="e1"><text>Failed</text></g></svg>';
  assert.equal(applyTones(svg), svg);
});

test('preserves an explicitly colored edge and its marker instead of adding tone styles', () => {
  const svg = '<svg><g class="pele-edge" data-id="e1" style="stroke:#00ffff;stroke-width:4px">'
    + '<path d="M0 0"/><path class="pele-marker" fill="#00ffff" d="M1 1"/></g>'
    + '<g class="pele-edge-label" data-id="e1"><text>Failed</text></g></svg>';
  assert.equal(applyTones(svg), svg);
});

test('tones state edges with contrast attributes between class and data-id', () => {
  const svg = '<svg><g class="pele-edge pele-transition" stroke="var(--pele-fg-on-light,#1f1f1f)" data-id="edge1"><path d="M0 0"/></g>'
    + '<g data-id="edge1" transform="translate(4,8)" class="pele-edge-label"><text>Failed</text></g></svg>';
  const expected = '<svg><g class="pele-edge pele-transition pele-tone-danger" stroke="var(--pele-fg-on-light,#1f1f1f)" data-id="edge1"><path d="M0 0"/></g>'
    + '<g data-id="edge1" transform="translate(4,8)" class="pele-edge-label pele-tone-danger"><text>Failed</text></g></svg>';
  assert.equal(applyTones(svg), expected);
});

test('keeps author-colored nodes and their contrast labels unchanged beside an inferred node', () => {
  const custom = '<g class="pele-node pele-state success" fill="#fff" data-id="custom">'
    + '<rect style="rx:12px;fill:#000;stroke:#00ffff"/>'
    + '<text fill="var(--pele-fg-on-dark,#fff)">Done</text></g>';
  const neighbor = '<g data-id="neighbor" class="pele-node"><rect/><text>Failed</text></g>';
  assert.equal(applyTones(`<svg>${custom}${neighbor}</svg>`), `<svg>${custom}`
    + '<g data-id="neighbor" class="pele-node pele-tone-danger"><rect/><text>Failed</text></g></svg>');
});

test('author colors belong only to their own group and do not suppress neighboring nodes', () => {
  const group = '<g class="pele-cluster" data-id="group"><rect style="fill:#fff"/>'
    + '<text fill="#000">Queued</text></g>';
  const node = '<g class="pele-node" data-id="node"><rect/><text>Done</text></g>';
  assert.equal(applyTones(`<svg>${group}${node}</svg>`), `<svg>${group}`
    + '<g class="pele-node pele-tone-success" data-id="node"><rect/><text>Done</text></g></svg>');
});
