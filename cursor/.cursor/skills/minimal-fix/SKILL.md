---
name: minimal-fix
description: Diagnose before changing and fix bugs with the smallest correct intervention. Use when debugging any defect (code, UI, config, build, data, infra), when a fix attempt keeps growing into a rewrite, when repeated fixes create new symptoms, or when the user reports a small visual or behavioral bug.
---

# Minimal Fix

## Core rule

Understand the existing design first. Form one hypothesis about the smallest cause. Change one thing. Verify against the user's evidence. Stop when it works.

Not understanding a system is a signal to read more, never a license to rewrite it.

## Workflow

1. **Map the existing model.**
   - Read the code that produces the behavior before editing any of it.
   - Identify what each part is *for* and what mechanism produces the observed output (spacing, ordering, state, timing, precedence — whatever domain applies).
   - Assume the current design mostly works and the bug is a small deviation from intent, not evidence the architecture is wrong.

2. **Translate the symptom into the system's vocabulary.**
   - Vague symptom → sprawling fix. Precise symptom → localized cause.
   - "Gap between A and B" → what inserts space between A and B?
   - "X visible through Y" → what controls occlusion/ordering, not what positions X?
   - "Wrong value after step N" → what writes that value between N-1 and N?
   - If you cannot restate the symptom as a question about a specific mechanism, you have not read enough yet.

3. **One hypothesis → one change → one verification.**
   - Change a single variable. Prefer adjusting or deleting an existing value over adding new mechanisms.
   - If the change fixes it, stop. Do not "improve" surrounding code in the same pass.
   - If it doesn't, revert it before trying the next hypothesis. Never stack speculative changes.

4. **Verify against primary evidence.**
   - The user's report, screenshot, or failing output is ground truth.
   - Automated probes and metrics only measure what you told them to measure. Passing metrics plus a failing user report means the metric is wrong, not the user.
   - Reproduce the user's view (same page, same state) rather than a convenient approximation.

5. **Preserve invariants.**
   - A fix that silently alters unrelated behavior (spacing, API shape, timing, styling, defaults) is not minimal — it is a new bug with better marketing.
   - Before finishing, diff your change against the symptom: every line should be traceable to the reported problem.

## Escalation gate

Restructure (new layout strategy, new abstraction, new dependency, rewritten module) only when **all** of these hold:

- You can explain why the current design behaves the way it does.
- You can articulate why it *cannot* express the requirement — not merely that you haven't found the knob yet.
- At least one genuinely minimal fix has been tried and shown insufficient.

When escalating, carry over every behavior the user did not ask to change.

## Warning signs you are swinging blindly

- You are on your second architectural approach in one session.
- Each fix produces a new, different symptom.
- You changed several properties at once and can't say which one mattered.
- You cannot explain why the previous version behaved as it did.
- Your tooling says "fixed" but the user says otherwise.

When any of these appear: stop, revert to the last known-good state, and re-read the code.

## Case study (compressed)

Symptom: visible gap between a timeline bullet and the connecting line below it.

- **Blind swing:** rewrote the flex layout to absolute positioning, changed bullet fill to transparent, moved padding — fixed the gap, broke line-spacing and bullet occlusion. Two more rewrites followed.
- **Minimal fix:** read the structure (flex column: bullet, then rail with `flex-1` and a negative bottom margin bridging to the next item). The gap was a `mt-1` on the rail. Fix: `mt-1` → `mt-0`. Two lines changed, nothing else moved.

Side lesson from the same session: when a rule appears on the element but has no effect (computed style shows `auto`/`none`), the rule was never generated or applied — fix detection/tooling before touching layout.
