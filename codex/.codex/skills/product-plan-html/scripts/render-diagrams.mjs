#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import { instance } from '../assets/vendor/viz.js';

const directory = path.resolve(process.argv[2] || '.');
const manifest = JSON.parse(await fs.readFile(path.join(directory, 'diagrams/manifest.json'), 'utf8'));
const viz = await instance();
const rendered = [];
for (const diagram of manifest) {
  if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(diagram.id)) {
    throw new Error(`Invalid diagram id: ${diagram.id}`);
  }
  const dot = await fs.readFile(path.join(directory, 'diagrams', `${diagram.id}.dot`), 'utf8');
  const result = viz.render(dot, { format: 'svg', engine: 'dot' });
  if (result.status !== 'success') {
    throw new Error(`Diagram ${diagram.id}: ${JSON.stringify(result.errors)}`);
  }
  const title = diagram.title.replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;',
  }[char]));
  const svg = result.output.slice(result.output.indexOf('<svg'))
    .replace(/<title>G<\/title>/, `<title>${title}</title>`)
    .replace(/font-family="Poppins"/g, 'font-family="Poppins, sans-serif"');
  await fs.writeFile(path.join(directory, 'diagrams', `${diagram.id}.svg`), svg);
  rendered.push({ ...diagram, svg });
}
await fs.writeFile(path.join(directory, 'diagrams.js'), `window.DIAGRAMS = ${JSON.stringify(rendered)};\n`);
for (const name of ['spec.js', 'diagrams.js', 'prototype.js', 'viewer.js']) {
  const source = await fs.readFile(path.join(directory, name), 'utf8');
  new vm.Script(source, { filename: name });
  const inline = source.replace(/<\/script/gi, value => '<\\/' + value.slice(2))
    .replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
  new vm.Script(inline, { filename: `inline:${name}` });
}
process.stdout.write(JSON.stringify({ ok: true, diagrams: rendered.length }) + '\n');
