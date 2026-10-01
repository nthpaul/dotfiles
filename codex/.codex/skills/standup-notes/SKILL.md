---
name: standup-notes
description: >-
  Fill or revise Paul Le's EPDD standup notes in Superhuman Docs using recent work,
  Granola meetings, Slack conversations, and PRs. Use grouped P:/T: bullets with one
  action per line. Applies to standups, not 1:1 agendas or project reports.
---

# Standup notes

Update Paul's row in the supplied standup page. Use the page's date and pod to
choose the time window and scope. A formatting-only request changes the existing
notes without restarting research.

## Format

Use **P:** for previous work and **T:** for today's work. Group related actions
under a short parent bullet naming the project or topic. Each nested bullet has
one action, on its own line. Let the editor wrap long lines naturally.

```markdown
P:
- Recruiting / Match Maker
  - Fixed applicants getting skipped during recruiting admission.
  - Fixed repeated follow-up messages.
- Comms broker
  - Unblocked bulk invitations.

T:
- Recruiting / Match Maker
  - Investigate delayed replies.
  - Prepare the next pilot location.
- Navi / vetting
  - Land the daily review digest.
```

- Keep child bullets short and concrete. Split independent actions instead of
  joining them with semicolons or packing them into a paragraph.
- Include the outcome or blocker needed to understand an action. Trim technical
  mechanics and secondary details before removing useful context.
- Link a few key claims to their source PR, Slack thread, or meeting notes.
- Preserve the P:/T: structure when applying other writing skills.

## Research

- Read the target page and the most recent relevant standup. Cover work since
  that update unless Paul specifies another window; avoid repeating old wins.
- Check Granola meetings and recent Slack conversations. For recruiting and
  staffing updates, include `#project-regional-worker-placement-model`
  (`C0BS82YVB8C`). Paul's Slack ID is `U09FL4PT8AE`.
- Check relevant PRs in `trabapro/traba` and `trabapro/the-matrix`. Paul's GitHub
  handle is `nthpaul`; include work he drove through Devin or collaborators when
  the evidence connects it to him.
- Read important threads through their latest replies. Verify PR state before
  describing work as merged; distinguish merged, deployed, in review, and planned.
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
3. After editing, **click outside the update box** to commit the change.
4. Open the page in a fresh tab and read Paul's saved row. Confirm the content,
   P:/T: sections, and nested bullets persisted before reporting success.
5. Give a brief confirmation with the page link and any proof required by the
   browser tools. If access or saving fails, report the blocker and retain the
   drafted notes rather than claiming the page was updated.
