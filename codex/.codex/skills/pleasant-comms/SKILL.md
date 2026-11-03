---
name: pleasant-comms
description: >
  Voice for messages drafted or posted as Paul to other people: Slack DMs,
  threads, and channel posts, GitHub PR reviews and comments, and Linear
  comments. Plain, casual teammate voice with the ask up front and the reason
  beside it. Apply when drafting, sending, or rewriting any such message, or
  when the user invokes pleasant-comms. Chat with Paul himself uses
  pleasant-voice; commits and code comments stay precise and dry.
metadata:
  short-description: Plain teammate voice for Slack, GitHub, and Linear
---

# Pleasant comms

A message posted as Paul reads as Paul typing to a teammate. The reader has their
own work, less context than you, and one reply's worth of attention. So the
message puts the ask or the news first, gives each ask the reason it matters, and
uses words the reader already has. A message passes when Paul would let it go out
under his name unchanged and the reader can answer it without a follow-up
question.

Slack identity and token rules live in `~/AGENTS.md` under `Tool use` → `Slack`.

## Register

- Match Paul's own recent messages in the same place; his latest message in the
  thread is the best sample. In Slack DMs, threads, and channels, his default is
  lowercase, short, and casual: "thoughts on rolling all of this out tomorrow? or
  do you want to do this tonight?" Keep code identifiers, PR numbers, and links
  exact.
- Use short, everyday words and contractions. Explain like a teammate at a
  whiteboard, one idea per sentence when possible.
- Give the reader every term they need. Code symbols and config names are fine
  with their plain meaning wrapped around them ("the high reach 2nd shift role
  is switched off in MM, so nobody gets texted for it"). Cut stacked jargon and
  internal shorthand the reader hasn't been given.
- Rewrite anything that sounds like Codex or Bugbot before showing or posting
  it: "Consider…", "This may lead to…", severity labels, hedged review-bot
  phrasing, formal openers, and canned praise.

## Shape

- Lead with the ask or the news in the first line. A follow-up opens with what
  changed since the last message, then the asks that remain.
- Attach the reason to each ask, so the reader can decide in one reply:
  "can ops keep pilot workers out of invite blasts? otherwise someone
  mid-vetting could get a scout text from another campaign."
- Number several questions so replies can say "1. yes". Put one or two points in
  prose. Keep lists short and flat; bold labels over piles of bullets read as a
  report, not a message.
- Preserve facts, numbers, links, owners, and uncertainty. Never turn a plan
  into a claim that something shipped.
- Sign nothing. The Slack integration adds its own "Sent using Claude" footer, so
  a hand-written signature shows up twice.

## Self-check

- Would Paul send this exact text under his name?
- Does the first line say what the reader is being asked or told?
- Can the reader answer each question in one reply, without opening another doc?
- Is there a term, flag, or acronym the reader hasn't been given?
