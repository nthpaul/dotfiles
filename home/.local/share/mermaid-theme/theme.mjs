import { applyTones } from './tone.mjs';

// Shared semantic accents; each renderer keeps its own neutral background and fonts.
export const palettes = {
  light: {
    danger: '#cf222e', warning: '#9a6700', success: '#1a7f37', active: '#0969da',
    changed: '#8250df', removed: '#cf222e', muted: '#6e7781',
  },
  dark: {
    danger: '#f85149', warning: '#d29922', success: '#3fb950', active: '#4493f8',
    changed: '#a371f7', removed: '#f85149', muted: '#8b949e',
  },
};

function variables(colors) {
  return Object.entries(colors).map(([tone, color]) => `--tone-${tone}:${color};`).join('');
}

export const browserPaletteCss = `svg.pele {${variables(palettes.light)}}
@media (prefers-color-scheme: dark) {svg.pele {${variables(palettes.dark)}}}`;

function mix(color, background, weight) {
  const channels = [1, 3, 5].map((offset) => {
    const front = parseInt(color.slice(offset, offset + 2), 16);
    const back = parseInt(background.slice(offset, offset + 2), 16);
    return Math.round(front * weight + back * (1 - weight)).toString(16).padStart(2, '0');
  });
  return `#${channels.join('')}`;
}

// resvg supports ordinary SVG stylesheets, but not CSS variables or color-mix().
// Inline styles from the diagram still take precedence over these theme rules.
export function colorizeSvg(svg, theme) {
  const dark = theme === 'dark';
  const background = dark ? '#111111' : '#ffffff';
  const foreground = dark ? '#e0e0e0' : '#1f1f1f';
  const shapes = ['rect', 'circle', 'ellipse', 'path', 'polygon', 'polyline'];
  const css = Object.entries(palettes[dark ? 'dark' : 'light']).map(([tone, color]) => {
    const node = `.pele-node.pele-tone-${tone}`;
    const cluster = `.pele-cluster.pele-tone-${tone}`;
    const edge = `.pele-edge.pele-tone-${tone}`;
    const label = `.pele-edge-label.pele-tone-${tone}`;
    const fill = mix(color, background, dark ? 0.18 : 0.12);
    const text = mix(color, foreground, 0.75);
    const selectors = [node, cluster].flatMap((group) => shapes.map((shape) => `${group} > ${shape}`));
    return `${selectors.join(',')} {fill:${fill};fill-opacity:1;stroke:${color};stroke-width:1.5}
${selectors.map((selector) => `${selector}[fill="none"]`).join(',')} {fill:none}
${selectors.map((selector) => `${selector}[stroke="none"]`).join(',')} {stroke:none}
${node} text,${cluster} text {fill:${text};font-weight:600}
${edge} {stroke:${color}}
${edge} > path {stroke-width:1.75}
${edge} .pele-marker {fill:${color}}
${label} text {fill:${color};font-weight:600}
${label} rect {fill:${fill}}`;
  }).join('\n');
  const distinctions = `
.pele-node.pele-tone-changed > rect {stroke-width:2.5}
.pele-node.pele-tone-removed > rect {stroke-dasharray:5 3}
.pele-node.pele-tone-removed text {text-decoration:line-through}
.pele-node.pele-tone-muted text {font-weight:400;font-style:italic}
.pele-edge.pele-tone-muted {stroke-dasharray:4 3}`;
  return applyTones(svg).replace(/^(<svg\b[^>]*>)/, `$1<style>${css}${distinctions}</style>`);
}
