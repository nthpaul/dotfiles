// Tags Pele's SVG output with a tone class (pele-tone-<tone>) so diagram.css can color it by
// meaning. A tone comes from an explicit Mermaid class (`class Failed fail`) when the source has
// one, otherwise from words in the label. Pele marks every node, cluster, edge, and edge label
// with a class and data-id, which is what the patterns below rely on.

export enum Tone {
  Danger = "danger",
  Warning = "warning",
  Success = "success",
  Active = "active",
  Changed = "changed",
  Removed = "removed",
  Muted = "muted",
}

// Class names a diagram author can apply with `class <id> <name>`, mapped to their tone.
const CLASS_TONES: Record<string, Tone> = {
  danger: Tone.Danger, fail: Tone.Danger, failed: Tone.Danger, error: Tone.Danger,
  warning: Tone.Warning, warn: Tone.Warning, pending: Tone.Warning,
  success: Tone.Success, ok: Tone.Success, done: Tone.Success,
  active: Tone.Active, current: Tone.Active, info: Tone.Active,
  changed: Tone.Changed, new: Tone.Changed, added: Tone.Changed,
  removed: Tone.Removed, deleted: Tone.Removed,
  muted: Tone.Muted, skipped: Tone.Muted,
};

// Checked in order, so "retry after error" reads as danger. Changed and removed are explicit
// only: whether a component changed is a fact about the PR, not something a label reveals.
const WORD_TONES: [Tone, RegExp][] = [
  [Tone.Danger, /\b(fail\w*|errors?|errored|reject\w*|denied|deny|crash\w*|abort\w*|timeouts?|timed out|invalid|panic\w*|dead letter\w*|dlq|refus\w*|exhausted)\b/],
  [Tone.Warning, /\b(retry\w*|retries|pending|waiting|wait|blocked|paused?|stale|on hold|backoff|throttl\w*|degraded|warn\w*|queued)\b/],
  [Tone.Success, /\b(done|success\w*|succeed\w*|complete[ds]?|approved?|passed|pass|ok|merged|resolved|delivered|confirmed|accepted|healthy|ready)\b/],
  [Tone.Active, /\b(running|processing|in progress|active|started|executing|sending|syncing)\b/],
  [Tone.Muted, /\b(cancel\w*|skip\w*|ignored?|expired|archived|noop|no-op|closed)\b/],
];

const ELEMENT = /<g class="(pele-(?:node|cluster|edge|edge-label)(?: [^"]*)?)" data-id="([^"]*)"/g;
const TEXT = /<text[^>]*>([\s\S]*?)<\/text>/;
const NEXT_ELEMENT = '<g class="pele-';

// "PaymentFailed", "payment_failed", and "payment-failed" all become "payment failed".
function words(text: string): string {
  return text
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_\-./:]+/g, " ")
    .toLowerCase();
}

// The element's own first text, stopping at the next element so a node without text (a start
// dot) does not borrow its neighbor's label.
function labelAt(svg: string, offset: number): string {
  const end = svg.indexOf(NEXT_ELEMENT, offset + 1);
  return TEXT.exec(svg.slice(offset, end === -1 ? undefined : end))?.[1] ?? "";
}

export function toneOf(classes: string[], label: string): Tone | null {
  for (const name of classes) {
    const tone = CLASS_TONES[name.toLowerCase()];
    if (tone) return tone;
  }
  const text = words(label);
  // A question ("ok?") is a decision, not a state, so its wording says nothing about outcome.
  if (text.trim().endsWith("?")) return null;
  for (const [tone, pattern] of WORD_TONES) if (pattern.test(text)) return tone;
  return null;
}

export function applyTones(svg: string): string {
  // Edge paths carry no text; their label lives in a separate group with the same data-id.
  const edgeTones = new Map<string, Tone>();
  for (const match of svg.matchAll(ELEMENT)) {
    const [, classAttr, id] = match;
    if (!classAttr.startsWith("pele-edge-label")) continue;
    const tone = toneOf([], labelAt(svg, match.index));
    if (tone) edgeTones.set(id, tone);
  }

  return svg.replace(ELEMENT, (tag, classAttr: string, id: string, offset: number) => {
    const [kind, ...classes] = classAttr.split(" ");
    let tone: Tone | null;
    if (kind === "pele-edge" || kind === "pele-edge-label") {
      tone = toneOf(classes, "") ?? edgeTones.get(id) ?? null;
    } else {
      tone = toneOf(classes, labelAt(svg, offset) || id);
    }
    return tone ? `<g class="${classAttr} pele-tone-${tone}" data-id="${id}"` : tag;
  });
}
