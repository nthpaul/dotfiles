---
name: dynamic-extraction
description: >-
  Run the standing-prefix extraction gate for one ENG-24073 child. Gather
  Plan and Baseline before code, implement the extract, then fill Post-merge.
  Use when starting or resuming a dynamic-extraction ticket, when the user
  says /dynamic-extraction, or when they say go on the next extraction card.
disable-model-invocation: true
---

# Dynamic extraction card

One Linear child of [ENG-24073](https://linear.app/traba/issue/ENG-24073). Prefix may vary by surface, org, grant, tier, product. Not by intent.

Playbook (source of truth): `~/projects/work-docs/plans/dynamic-extraction-order-2026-08-27/baseline-gate.md`
Scoreboard: `~/projects/work-docs/plans/dynamic-extraction-order-2026-08-27/baselines.md`
Order: `~/projects/work-docs/plans/dynamic-extraction-order-2026-08-27/README.md`
Canvas: https://trabaworkspace.slack.com/docs/T025352QNPP/F0BT16NBC03

Do not write product code until the ticket Baseline has numbers, not TBD.

## Do in order

1. Read the ticket. Keep Summary / Scope / AC. Write **Plan** (what leaves the prefix, what stays, which surfaces).
2. Fill **Baseline** on the ticket. Measure. Copy SQL and Datadog pulls from the playbook. Name live path (Slack skills-on Neutron) separately from skills-off / Neo.
3. Check stale byte claims against the code constant this week.
4. Worktree: `~/.cursor/skills/worktree-home/scripts/wt-path.sh` then `git worktree add` from `origin/main`. Branch `ple/eng-<id>-<slug>`.
5. Implement the smallest extract. Availability from grants / surface / product. Never `questionIntent`. Do not dump bodies under `## Current Context`. Use `stampSkillBody` for this-run facts.
6. SHA pair must cover the intents this card kills. If DEBUGGING still forks, say so.
7. **Evals:** only if the moved body was model-visible. Name the ids. They must pass **3× in a row** before merge. A fail resets the count. Prefix-only cards write `Evals: n/a`. Do not use `compose-noskill-*` as the gate (fictional names vs live ids).
8. Open the PR. Drive to green. Do not merge unless asked.
9. After the prod image: fill **Post-merge** within 48h. Same fields. Same window. Add a scoreboard row. If SHA/event did not move and the ticket claimed it would, say so.

## Must record

Window + `main` SHA. Surfaces. Live vs side path. Block chars by path. Prefix total. Slack intent mix 7d. Unique SHA / events / SHA/event / singletons. Predicted SHA factor if this fork dies (`1.0` if live path already matches). Body load. SHA pair already green on `main`? Evals `n/a` or named ids + 3× result.

## Worked example

ENG-24138. Slack skills-on ops block was already 0. Live SHA factor 1.0. Skills-off GENERAL 268k→5.2k was the real cut. Measure first.
