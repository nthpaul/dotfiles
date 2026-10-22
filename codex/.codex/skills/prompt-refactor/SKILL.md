---
name: prompt-refactor
description: Audit or restructure an LLM prompt so it is unambiguous, free of contradictions, and maintainable, using mutually exclusive Background/Behavior/Output sections. Use when explicitly asked for a prompt refactor, prompt audit, or prompt review of a system prompt, agent or tool instructions, an LLM call template, a skill, or an AGENTS.md/CLAUDE.md file.
disable-model-invocation: true
---

# Prompt refactor

Prompts degrade by accretion. Each fix adds lines, nobody removes the lines they supersede, and nobody rereads the whole. The result contradicts itself, leans on context only the authors have, and repeats rules in drifting variants. This skill finds those defects and, when asked, rewrites the prompt into a structure where every rule has one owner.

Default to a review: report findings and proposed fixes. Rewrite only when the user asks for a rewrite or fixes.

## 1. Assemble the prompt the model actually receives

- Resolve the target: a file, a prompt-builder function, a deployed prompt in a prompt manager or vendor console, or a set of skill and instruction files. If the deployed version lives outside the repository, fetch it; do not review a stale local copy.
- Trace the assembly. Find every fragment injected conditionally (by feature flag, user type, mode, tool availability, or locale) and the conditions that select it. List the variants that occur in practice and review each assembled variant, or at minimum the base plus each fragment against the base.
- Include tool names, tool descriptions, and parameter descriptions. The model reads them as instructions.
- Collect the evidence available: eval cases, recent failing traces, and any recorded product decisions. A trace shows which branches matter; an eval shows what the team said it wanted.

## 2. Read it end to end, without the team's context

Read every line the way the model must: literally, with no knowledge of the company beyond what the prompt says. For each instruction, ask what it actually says, not what its author meant. Record findings in these categories:

| Category | What to look for |
| --- | --- |
| Contradiction | Two instructions that demand different actions for some input, including across conditional fragments. |
| Ambiguity | More than one reasonable reading. Undefined referenced sets ("competitors", "sensitive topics"), vague thresholds ("brief", "when appropriate", "if needed"), and unstated priority between rules. |
| Gap | A core branch of the request space with no specified behavior, especially one that appears in traces or evals. |
| Duplication | The same rule stated more than once, often in slowly diverging wording. |
| Misplacement | A rule outside the section that owns it, such as output formatting inside tool instructions or internal reasoning rules inside output rules. |
| Stale content | Workarounds for an older model, rules for removed features or tools, and examples the current model no longer needs. |

For every finding, give a concrete input that triggers it. A contradiction without a triggering input is a style note, not a defect.

## 3. Separate defects from product decisions

Many findings cannot be fixed without deciding what the product should do: should the agent answer fast or research first, ask for approval or proceed, reply in English or in the user's language. These are product decisions. State the question and the options, and ask the user. Do not resolve a product decision by picking the wording that reads best.

When an eval exists for the behavior, writing or reading its expected result often exposes the missing decision. Point that out.

## 4. Restructure (when asked to rewrite)

Organize the prompt as a tree of sections that are mutually exclusive (each concern lives in exactly one place) and collectively exhaustive (together they specify the intended behavior). Keep the three top-level sections and, where they fit, the second-level ones. Lower levels are examples; adapt them to the agent.

```
# Background                 the background for the agent
## Aim                       the agent's high-level aim
## Context                   the product it operates within; domain terms and named sets
# Behavior                   non-output behavior only, i.e. process
## Proactiveness             how proactive to be versus asking to clarify
## Workflow                  plan first, follow a rough workflow, or act straight away
## Tool use
### Parallel tool use        which tools to call in parallel
### Tool X vs Y vs Z         when to use each; guidance that fits no single tool description
#### tool_y                 a tricky tool and its interactions with other tools
# Output                     output behavior only
## Output format             e.g. markdown, no bullet points
## Output rules              e.g. never mention competitors X, Y, Z
```

Tool descriptions stay about their own tool. Choices between tools, parallel use, and interactions belong under `Tool use`, where they can be read together.

Behavior is the backend and Output is the frontend. Keep them independent: an agent can reason in a structured way and reply in prose, or analyze data with code it never shows the user.

Rewrite rules:

- Preserve every intended behavior. Build a coverage map from each original instruction to its new location, or to a recorded reason for deletion. Nothing disappears silently.
- Change behavior only where the user made a decision in step 3. A restructure that changes behavior is a product change and must be reported as one.
- State each rule once, in the section that owns it. Delete duplicates rather than cross-referencing them.
- Write decisions as conditions: "If X, do Y; otherwise Z." Specify the main branches and the criteria for judgment calls; do not script every edge case.
- Define each referenced set in `Context`, or name its members where the rule uses it, as in "never mention competitors X, Y, Z."
- Keep exact tool names, template variables, placeholders, and output schemas byte-for-byte unless the change is the point.
- Keep the conditional assembly working. When fragments are injected, give each fragment one home section in the tree, and check that no variant reintroduces a contradiction.

## 5. Verify

- Run the existing eval or test suite for the prompt before and after, when one exists and running it is cheap or authorized. Report regressions and improvements separately.
- Without evals, replay a small set of representative inputs, including the triggering inputs from step 2, and compare behavior before and after.
- Reread the final assembled prompt end to end once more for new contradictions.
- Report token counts before and after when the change affects cost or latency.

## Report

Return, in this order:

1. A short verdict: the prompt's main structural problem and the highest-impact fix.
2. Findings, most consequential first. Each gives its location, the quoted text, the category, a triggering input, and the proposed fix.
3. Open product decisions, each as a question with options.
4. For a rewrite: the new prompt or diff, the coverage map, and verification results, with anything not verified named as such.
