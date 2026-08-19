---
name: engineering-prose
description: >
  Rewrite blogs, essays, and technical explanations in the voice of
  Cursor's "Git at any scale" post: concrete, opinionated, no AI slop.
  Use when writing or editing prose, deslopping a draft, matching that
  blog voice, or when the user runs /engineering-prose.
---

# Engineering prose

Write like [Git at any scale](https://cursor.com/blog/git-at-any-scale). Not a coat of paint. A staff engineer would publish this.

This skill owns voice and shape. The banned-pattern catalog lives in `unslop`. Apply that catalog, then rewrite into this voice. Do not dump the catalog here.

Stay off this voice for UI copy, commit messages, legal text, and reference tables. Those stay dry.

## Process

1. Find the claim. One sentence. If you cannot say it, you do not understand it yet. Stop and learn.
2. Walk the constraint, then the approaches that failed, then what you built. Teach by elimination. Do not open with the product.
3. Strip slop (`unslop`). Then put the voice back in. Sterile is still AI.
4. Self-audit with the checklist at the bottom. Fix what fails.

## The claim comes first

Open on a fact with a spine, not a table of contents.

> Hosting Git repositories at scale is a nightmare.

Not "In this post we'll explore the challenges of hosting Git." The reader already knows it is a post.

Give history only when it earns the claim. Linus wanted a BitKeeper replacement for his own kernel workflow. Twenty years later the distributed model is a hindrance for the average company. That sequence is the argument. A timeline of Git releases is not.

## Teach by failed approaches

Name the naive design. Say why it looks right. Say the number, the protocol, or the round-trip that kills it. Then the next design.

The source walks object-in-a-DHT, then NFS/GFS/DRBD, then Spokes, then Continuity. Each section exists because the last one died for a specific reason: DAG walks make DHT round-trips fatal; packfile deltas make networked filesystems crawl; 3PC has a floor too high and a ceiling too low.

Do not list "pros and cons." Kill the approach, then move.

When the solution arrives, say what it stole from the dead ones. "We do the same thing that Spokes does because I think Spokes got that exactly right." Credit is cheaper than pretending you invented NVMe.

## Voice

Talk like the person who built it, on a good day, to a peer.

- First person is allowed. "I think." "Trust me, bad things happen all the time." "My former mentor Shawn Pearce."
- "We" for the team. "You" for the reader. Never "one" and never "the user" when you mean "you."
- Have a view. "Very pragmatic. It didn't work." "They were *terrible* to operate." Neutral recitation is the tell.
- Humor is dry and specific, or absent. "Linus is not going to come over and check." "hashtag blessed." No jokes about the reader's journey. No "buckle up."
- Name people, systems, and numbers. Shawn Pearce, JGit, DRBD, 3PC, 120 pushes/s, a 304 in under 10ms. "Industry experts" and "at scale" with no number are empty.
- Italics on the first use of a term you will keep using (*packfiles*, *distributed*). Bold only for an invariant you need the reader to remember: **We never acknowledge a push until it has been fully persisted.** If everything is bold, nothing is.
- Sentence-case headings. Prefer a question or a short noun phrase ("What's hard about Git?", "Git without packfiles"). Never "A Deep Dive Into Our Novel Architecture."
- Repeat a thesis when the design actually repeats. "The system is designed to always be correct when degraded, and always fast when healthy." Once is a slogan. Twice, in the two places it is true, is structure.

Mix sentence length on purpose. Short sentences land the kill. "But this actually doesn't work." "It didn't work." Long sentences carry one mechanism: the DAG walk, the delta chain, the 3PC tail. If a long sentence carries two thoughts, split it. If every sentence is the same length, it is a model.

## What the source does not do

Do not copy the sales close. "We're hoping you'll place your trust in us" is a landing page. End on a fact, a limit, or the next problem.

Do not write "let's dive in," "it's important to note," "robust and seamless," "not just X, but Y" as a reflex, "in conclusion," emoji, or title-case headings. Contrast is fine when you earned it: "more of a hindrance than an advantage" follows twenty years of evidence. "Not just a Git host, but a reimagining of version control" did not.

Em dashes are in the source. Use one for an aside, then a period. If a paragraph has three, you are performing.

Colons are for a claim, then the expansion. Not as a drumroll before every list.

## Shape of an explanation

For a system, roughly this order. Skip a beat if it has nothing to say.

1. The nightmare, in one paragraph.
2. Why the obvious design is obvious, and why it fails.
3. What people actually tried, named, with the failure mode.
4. The two or three choices that turned out to be right. Number them only if the count is load-bearing.
5. What you built. Mechanism before brand. WAL in S3, then the name Continuity.
6. The remaining sharp edge. No system is perfect. Say the one that will bite.

Put the constraint the reader cannot change on the table early. You do not control the Git client. You do have to speak packfiles on the wire. Everything else is available.

When you have a measurement, use it. When you do not, do not write "blazing fast."

## Before and after

Before:

> In today's rapidly evolving landscape, hosting Git at scale presents unique challenges. Teams must leverage distributed architectures to ensure robustness, scalability, and a seamless developer experience. In this post, we'll dive into how our novel storage layer reimagines version control for the AI era.

After:

> Hosting Git repositories at scale is a nightmare. Git is distributed, which sounds like it should make hosting easy: put an HTTP daemon in front of a repo on disk and you have a server. The ceiling on that design is very low. Packfiles are large binary files. They have to live on a filesystem Git can mmap. The average company wants the repo on many disks and many machines, and Git was not designed for that.

The first draft announces a post. The second makes a claim, shows the naive design, and names the thing that breaks.

## Self-audit

Read the draft once as a skeptic. Fix anything that fails:

- Could this sentence appear, unchanged, on another company's blog? Cut it.
- Did I explain a failed approach with a real reason, or just say it "didn't scale"?
- Is there a number, a protocol, a file, or a person's name where I wrote a vibe?
- Am I still hedging ("somewhat," "relatively," "it could be argued")? Pick a side or delete the sentence.
- Did I bold more than a handful of invariants?
- Does the ending sell, or does it still teach?
- Did I apply `unslop`, then put a human voice back, or did I stop at sterile?
