---
name: craft
description: "Produce precise, coherent, carefully verified work across code, writing, research, analysis, design, planning, and operations. Apply to all substantive task work, including small edits and explanations; scale effort to scope and stakes. Use for craft, care, quality, polish, or thorough verification."
---

# Craft

Make care repeatable. Establish what a good result must accomplish, ground it in the real subject, build a form that makes sense, and inspect the delivered result before calling it finished.

Apply this discipline throughout the task. Use relevant domain skills for their actual tools and constraints. Preserve the user's intent, format, scope, time budget, and existing authorization. This skill grants no permission to publish, deploy, message, or change unrelated work.

## Scale the effort

Keep the process as small as the task permits while retaining its essential checks.

- **Small, reversible work:** identify the intended outcome, check the changed material and its immediate context, and deliver. Usually keep the criteria and inspection internal. No mandatory plan, new test suite, or written report.
- **Substantial work:** establish acceptance criteria and likely failures before building; inspect structure, important details, and actual use. Keep enough evidence to make the result reviewable.
- **Consequential or fragile work:** check the relevant dependencies, failure paths, uncertainty, and recovery behavior. Use repeatable checks and independent review where they add confidence. Honor the authorized scope and budget.

The same care can produce a two-sentence answer or a tested application. More files, detail, tools, or process are justified only by the result they improve.

## Establish the standard and the truth

Before choosing an implementation or presentation:

1. Identify the user's desired outcome and who will use it. Translate words such as "precise," "beautiful," or "production-ready" into observable qualities relevant to this task. Include correctness and the experience of using or reading the result.
2. Inspect the available source, existing behavior, and closest strong example. Separate established facts, assumptions, and unknowns. Verify material uncertainty using the appropriate source or tool.
3. Establish the facts and rules that each representation must share. A calculation, explanation, display, and behavior should agree because they use the same underlying model. When a pure module, authoritative dataset, or shared definition prevents real divergence, use it.
4. Identify the few failures that would defeat the purpose. For each, decide what evidence would detect it. A vague instruction to be meticulous is not a verification plan.

Keep these decisions internal for simple tasks. Write them down when they help coordinate substantial work or make its reasoning reviewable. Ask only when missing information materially blocks the outcome; continue independent work meanwhile.

## Choose a form that explains its structure

Choose the shape around the subject and its intended use. Code should make its domain rules and ownership apparent. Writing should let the reader follow the evidence and reasoning. Plans should expose dependencies and responsibilities. A visual should make the mechanism understandable.

Give each part a job: explain, substantiate, enable an action, or implement a required behavior. Remove details that serve none of those purposes. Resolve the connections between parts: claims need supporting evidence, interfaces need compatible contracts, steps need the inputs they depend on, and failures need a usable next action.

Reuse proven examples, native capabilities, and existing tools where they fit. Keep one coherent set of terms, units, rules, and conventions across the result. Preserve meaningful distinctions rather than smoothing away an awkward fact to make the output look cleaner.

## Build something inspectable early

Make a working slice of the intended result early enough to discover a bad assumption or unsuitable form. Inspect it against the standard before deepening the work. Choose between competing approaches when the difference matters; avoid multiple prototypes for a routine choice with a clear precedent.

Build supporting tools when repeated work or a fragile operation warrants them. Prefer rerunnable checks to repeatedly performing the same error-prone inspection by hand. Use tools that check real properties; a generic "quality score" cannot establish correctness or taste.

## Inspect the result at several scales

Inspect the actual artifact or behavior using complementary evidence:

- **Whole:** does it accomplish the user's purpose, communicate its structure, and feel coherent?
- **Detail:** do the important calculations, claims, parts, names, units, and boundaries hold up under close inspection?
- **Connections and use:** do transitions, dependencies, handoffs, and the relevant failure or recovery paths work in the conditions the user will encounter?

Choose checks for the failures they can catch. Run appropriate automated checks for measurable properties, then read, view, or use the actual result for meaning, usability, and finish. A successful build, a generated screenshot, or another agent's self-report is insufficient evidence for a property it does not establish. Inspect the screenshot; exercise the behavior; read the published value when publishing was authorized.

For concrete checks by medium, read only the relevant section of [references/verification.md](references/verification.md). Independent review is useful for consequential assumptions and connected behavior; delegate a bounded question with raw evidence when available.

State what the evidence establishes. Sampled checks cover sampled conditions, and judgment remains judgment. Do not present either as universal proof. Expose material uncertainty when it changes how someone should use the result.

## Return failures to their cause

Keep a known relevant fault unresolved until it is repaired and its check passes. Changing the presentation, navigating elsewhere, or rerunning an unchanged check does not resolve it.

Trace the fault to the responsible fact, model, design, implementation, or integration. Repair there, then rerun the checks affected by that repair. Do not change an expected result or weaken a check merely to make the work pass. Reconsider a check when evidence shows its expectation is wrong.

When an observed mistake is likely to recur, put the lesson into a focused example, type, constraint, check, or recipe that prevents it. Keep the correction scoped to the demonstrated failure; avoid accumulating universal rules for hypothetical cases.

## Finish with evidence

Deliver the usable result in the requested form. Explain the outcome and include the verification evidence and limitations that matter to the user's next action. Keep this brief for small work.

Do not claim completion while a required criterion has a known unresolved failure. If a constraint prevents completion, identify the unmet criterion, available evidence, and the specific blocker without expanding the assignment or implying the artifact is ready.

Once the relevant checks pass and the artifact meets the standard, finish. Broaden verification only when new changes, failures, or unresolved concerns justify it.
