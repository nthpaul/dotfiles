---
name: standup-notes
description: >-
  Fill or revise Paul Le's EPDD standup notes in Superhuman Docs using recent work,
  Granola meetings, Slack conversations, and PRs. Use grouped P:/T: bullets with one
  action per line. Applies to standups, not 1:1 agendas or project reports.
---

# Background

Update Paul's row in the supplied standup page. Use the page's date and pod to
choose the time window and scope. The update should tell teammates what changed,
why it matters to workers or ops, and what needs to happen next.

## Context sources

- [EPDD standups](https://docs.superhuman.com/d/EPDD-Standups_dKsKRXQizkw)
- [Staffing standups](https://docs.superhuman.com/d/EPDD-Standups_dKsKRXQizkw/Oct-27-2026_suIcl4UA#_luSTB3O4)
  — a writing example; find the relevant dated page for current work.
- [Staffing Team Unblocks](https://docs.superhuman.com/d/Team-Unblocks_dgUg-YSC_z4/Staffing_susqK-ji#_lu4cwQgw)

# Behavior

An explicitly formatting-only request changes the existing notes without
restarting research. When the user supplies a writing example, match its level of
meaning, context, and evidence as well as its layout; inspect the cited context
and follow source links where the existing wording is unclear.

## Research

- Read the target page and the most recent relevant standups. For staffing work,
  also read the relevant staffing standup and Team Unblocks entries to establish
  priorities, progress, rollout decisions, and dependencies. Cover work since
  the last update unless Paul specifies another window; avoid repeating old wins.
- Check Granola meetings and recent Slack conversations. For recruiting and
  staffing updates, include `#project-regional-worker-placement-model`
  (`C0BS82YVB8C`). Paul's Slack ID is `U09FL4PT8AE`.
- Check relevant PRs in `trabapro/traba` and `trabapro/the-matrix`. Paul's GitHub
  handle is `nthpaul`; include work he drove through Devin or collaborators when
  the evidence connects it to him.
- Read important threads through their latest replies. Verify PR state before
  describing work as merged; distinguish merged, deployed, in review, and planned.
  Read the source's result and rollout conditions before describing behavior as
  live; merged support code can still have no caller or remain disabled.
- Use meetings to identify decisions and today's follow-ups. Preserve ownership:
  a team result is context, and a teammate's action is not Paul's accomplishment.
- Keep today's work grounded in current commitments and active work. State
  unresolved dependencies without inventing completion or launch dates.
- Include only work relevant to the target audience. An AI Platform update can
  focus on Neutron and platform reliability; staffing notes emphasize recruiting,
  placement, and operator workflows.

## Edit and verify

1. Find Paul's author row. Tables may virtualize rows, so inspect beyond the
   initial viewport before adding a row. Preserve other authors and columns.
2. Read existing content before editing. Use native nested bullets or rich-text
   HTML lists so parent/child indentation survives; Markdown pasted as plain
   text may leave literal markup.
3. Before saving, read the update as a teammate unfamiliar with the PRs. Check
   that each action explains the change or next step and its significance, that
   blockers are actionable, and that links open useful supporting context.
4. When editing in the browser, **click outside the update box** to commit the change.
5. Read Paul's saved row; for browser edits, open the page in a fresh tab. Confirm the content,
   P:/T: sections, and nested bullets persisted before reporting success.
6. Give a brief confirmation with the page link and any proof required by the
   browser tools. If access or saving fails, report the blocker and retain the
   drafted notes rather than claiming the page was updated.

# Output

Use **P:** for previous work and **T:** for today's work. Group related actions
under a short parent bullet naming the project or topic. Each nested bullet has
one action, on its own line. Let the editor wrap long lines naturally.

- Write each action so a teammate can understand what changed or what's next,
  who or what it affects, and any blocker. Name a dependency's owner when known.
  Translate implementation labels into the worker or ops outcome; keep technical
  terms only when they help this audience. Trim mechanics before useful context.
- Use a few descriptive links to the relevant plan, rollout, QA report, decision,
  Slack thread, or PR. Link the words that explain the work, such as
  `[onboarding QA report](url)` or `[callback fix](url)`, rather than bare PR numbers.
  Choose the source that best supports the claim and helps the reader act.
- Keep child bullets short and concrete. Split independent actions instead of
  joining them with semicolons or packing them into a paragraph.
- Preserve the P:/T: structure when applying other writing skills.

```markdown
P:
- Vetting / onboarding
  - Fixed workers being failed when they ask Scout to call back mid-call.
  - Shared the [onboarding QA report](url), including rescheduling and recovery.

T:
- Vetting / onboarding
  - Get bookable sessions added for the Five Below pilot; rollout is blocked on these.
```
