// Shared semantic labels for Pele's browser and terminal renderers.
export const Tone = Object.freeze({
  Danger: 'danger',
  Warning: 'warning',
  Success: 'success',
  Active: 'active',
  Changed: 'changed',
  Removed: 'removed',
  Muted: 'muted',
});

const CLASS_TONES = {
  danger: Tone.Danger, fail: Tone.Danger, failed: Tone.Danger, error: Tone.Danger,
  warning: Tone.Warning, warn: Tone.Warning, pending: Tone.Warning,
  success: Tone.Success, ok: Tone.Success, done: Tone.Success,
  active: Tone.Active, current: Tone.Active, info: Tone.Active,
  changed: Tone.Changed, new: Tone.Changed, added: Tone.Changed,
  removed: Tone.Removed, deleted: Tone.Removed,
  muted: Tone.Muted, skipped: Tone.Muted,
};

// Match a status or a short subject followed by a status, never a word anywhere in prose.
const STATE_WORDS = [
  [Tone.Danger, 'failed|failure|errors?|errored|rejected|denied|crashed|aborted|timeouts?|timed out|invalid|panicked|refused|exhausted|dead letters?|dlq'],
  [Tone.Warning, 'retry|retrying|retries|pending|waiting|blocked|paused|stale|on hold|backoff|throttled|degraded|warning|queued'],
  [Tone.Success, 'done|success|successful|succeeded|complete|completed|approved|passed|ok|merged|resolved|delivered|confirmed|accepted|healthy|ready'],
  [Tone.Active, 'running|processing|in progress|active|started|executing|sending|syncing'],
  [Tone.Muted, 'cancelled|canceled|skipped|ignored|expired|archived|noop|closed'],
];
const STATES = STATE_WORDS.map(([tone, states]) => [tone, new RegExp(`^(?:([a-z][a-z0-9]*(?: [a-z][a-z0-9]*){0,2}) )?(?:${states})$`)]);
const STATUS_IN_SUBJECT = new RegExp(`\\b(?:${STATE_WORDS.map(([, states]) => states).join('|')})\\b`);

function words(text) {
  return text
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_\-./:]+/g, ' ')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/\bno op\b/g, 'noop')
    .trim();
}

export function toneOf(classes, label) {
  const names = classes.map((name) => name.toLowerCase());
  if (names.includes('neutral')) return null;
  for (const name of names) {
    if (Object.hasOwn(CLASS_TONES, name)) return CLASS_TONES[name];
  }

  const text = words(label);
  // Negation, decisions, and compound instructions do not describe a clear outcome.
  if (/[?？]/.test(text) || /\b(no|not|never|without|after|before|if|unless|until|while|when|to|then|and|or|but|because)\b/.test(text)) return null;
  for (const [tone, pattern] of STATES) {
    const match = pattern.exec(text);
    if (!match) continue;
    const subject = match[1] ?? '';
    if (/\b(handle|handles|handling|show|shows|count|counts|log|logs|ignore|ignores|detect|detects|report|reports|return|returns|send|sends|mark|marks)\b/.test(subject)) return null;
    // A second status in the subject makes the phrase ambiguous ("failed requests queued").
    if (STATUS_IN_SUBJECT.test(subject)) return null;
    return tone;
  }
  return null;
}

const ELEMENT = /<g\b(?=[^>]*\sclass="(pele-(?:node|cluster|edge|edge-label)(?: [^"]*)?)")(?=[^>]*\sdata-id="([^"]*)")[^>]*>/g;
const TEXT = /<text\b[^>]*>([\s\S]*?)<\/text>/g;

function ownElement(svg, offset) {
  const from = svg.indexOf('>', offset) + 1;
  const next = svg.slice(from).search(/<g\b[^>]*\sclass="pele-[^"]*"/);
  return svg.slice(offset, next === -1 ? undefined : from + next);
}

function labelAt(svg, offset) {
  return [...ownElement(svg, offset).matchAll(TEXT)].map((match) => match[1]).join(' ');
}

function hasAuthorColor(svg, offset) {
  const shapes = /<(?:g|rect|path|circle|ellipse|polygon|polyline|line)\b[^>]*\sstyle="([^"]*)"/g;
  return [...ownElement(svg, offset).matchAll(shapes)]
    .some((match) => /(?:^|;)\s*(?:stroke|fill)\s*:/.test(match[1]));
}

export function applyTones(svg) {
  // Edge paths and labels are separate groups. Share explicit classes and the label's tone.
  const edges = new Map();
  for (const match of svg.matchAll(ELEMENT)) {
    const [, classAttr, id] = match;
    const [kind, ...classes] = classAttr.split(' ');
    if (kind !== 'pele-edge' && kind !== 'pele-edge-label') continue;
    const edge = edges.get(id) ?? { classes: [], label: '', styled: false };
    edge.classes.push(...classes);
    if (kind === 'pele-edge-label') edge.label = labelAt(svg, match.index);
    if (kind === 'pele-edge' && hasAuthorColor(svg, match.index)) edge.styled = true;
    edges.set(id, edge);
  }
  const edgeTones = new Map([...edges].map(([id, edge]) => [id, edge.styled ? null : toneOf(edge.classes, edge.label)]));

  return svg.replace(ELEMENT, (tag, classAttr, id, offset) => {
    const [kind, ...classes] = classAttr.split(' ');
    const tone = kind === 'pele-edge' || kind === 'pele-edge-label'
      ? edgeTones.get(id)
      : hasAuthorColor(svg, offset) ? null : toneOf(classes, labelAt(svg, offset) || id);
    return tone ? tag.replace(/\sclass="[^"]*"/, (attribute) => `${attribute.slice(0, -1)} pele-tone-${tone}"`) : tag;
  });
}
