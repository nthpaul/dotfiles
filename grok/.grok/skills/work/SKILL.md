---
name: work
description: >
  Run poteto-mode and attach ponytail at the right layer for a feature or a
  whole project. One entry point. Use when the user runs /work, or asks to
  work a feature or project end to end with poteto and ponytail together.
disable-model-invocation: true
mode: true
argument-hint: "[lite|full|ultra] <ask>"
metadata:
  short-description: "Poteto + ponytail, routed"
---

# Work

The ask is `$ARGUMENTS`. If empty, the rest of the user message is the ask.
Optional first word `lite` / `full` / `ultra` is intensity; default `full`.
Remainder is the ask.

1. Read and apply the **poteto-mode** skill in full. Match a playbook from it.
   Copy that playbook's steps into the todolist verbatim.
2. Attach ponytail using **Attach**. Do not guess, and do not run `/ponytail`
   on a coordinator chat.
3. First user-visible line: `playbook: <name>. ponytail: <this chat | workers | off>, <intensity>.`
4. Do the ask.

## Attach

Who writes code decides where ponytail lives. Ponytail is ACTIVE EVERY
RESPONSE; on a coordinator it will YAGNI the playbook.

| This chat's job | Playbooks | Ponytail |
|---|---|---|
| Implements or reviews diffs | Feature, Bug fix, Refactoring, Perf issue, Hillclimb, Prototype, Visual parity, Eval, Authoring a skill, Autonomous run, Multi-phase or multi-PR plan, Session pickup, Shipping, Babysit when you will edit | Apply the **ponytail** skill at the intensity. Stay on. Paste **Payload** into every code-writing Task prompt. After each coding diff, apply **ponytail-review** and take the cuts you accept. |
| Coordinates; workers implement | Orchestrate, Autopilot-full, Autopilot-stack | Do not apply ponytail on this chat. Put the ask's intensity in **Payload** (default `full`). Paste **Payload** into `preferences.md` and every worker brief. |
| No code | Investigation, Runtime forensics, Trace forensics, Pause safely, Worktree and simulator cleanup, Babysit watch-only | Off. |

`figure-it-out` uses the implements row unless the bespoke playbook is a coordinator program.

Never apply ponytail ultra to coordinator turns.

Feature vs Orchestrate: one agent can finish inside this session's budget → not Orchestrate. Outlives any single agent → Orchestrate. Poteto-mode owns every other playbook match.

## Payload

Self-contained. Workers and compacted subagents may not load the ponytail skill.

```
Implement per ponytail <intensity>.
Ladder: YAGNI → reuse in-repo → stdlib/native → installed dep → one line → minimum.
No new dependency. No interface with one implementation. No config for a constant.
Shortest working diff after you have traced the real flow.
Mark a real cut corner as `# ponytail: <ceiling>, <upgrade when>`.
```
