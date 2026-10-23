import { describe, expect, test } from "bun:test";
import { render } from "pele";
import { applyTones, Tone, toneOf } from "./tone.ts";

describe("toneOf", () => {
  test.each([
    ["PaymentFailed", Tone.Danger],
    ["timed out", Tone.Danger],
    ["attempts exhausted", Tone.Danger],
    ["retry after error", Tone.Danger],
    ["Retrying", Tone.Warning],
    ["awaiting_review_pending", Tone.Warning],
    ["Done", Tone.Success],
    ["merged", Tone.Success],
    ["Running", Tone.Active],
    ["Cancelled", Tone.Muted],
  ])("reads %p as %p", (label, tone) => {
    expect(toneOf([], label)).toBe(tone);
  });

  test("leaves neutral labels, partial words, and questions alone", () => {
    expect(toneOf([], "Parse request")).toBeNull();
    expect(toneOf([], "token book")).toBeNull();
    expect(toneOf([], "ok?")).toBeNull();
  });

  test("an explicit class wins over the label", () => {
    expect(toneOf(["changed"], "Done")).toBe(Tone.Changed);
    expect(toneOf(["Fail"], "Parse request")).toBe(Tone.Danger);
  });
});

describe("applyTones", () => {
  test("tags states, transitions, and their labels by meaning", () => {
    const svg = applyTones(
      render(`stateDiagram-v2
  [*] --> Running
  Running --> Failed: timed out
  Running --> Done
  class Running changed`).svg,
    );
    expect(svg).toContain('pele-state pele-tone-danger" data-id="Failed"');
    expect(svg).toContain('pele-state pele-tone-success" data-id="Done"');
    expect(svg).toContain('changed pele-tone-changed" data-id="Running"');
    expect(svg).toMatch(/class="pele-edge pele-transition pele-tone-danger" data-id="(edge\d+)"/);
    expect(svg).toMatch(/class="pele-edge-label pele-tone-danger"/);
    // The start dot has no text and must not borrow the next node's label.
    expect(svg).toContain('class="pele-node pele-state-start" data-id="root_start"');
  });
});
