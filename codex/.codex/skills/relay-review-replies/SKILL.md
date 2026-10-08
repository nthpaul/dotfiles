---
name: relay-review-replies
description: Assess reviewer comments and Paul's existing replies on Relay documents, or edit his replies in place in his concise lowercase style. Use for requests such as "assess my replies" or "edit my comments". Editing replies does not include revising the document.
---

# Relay review replies

Read the current conversation, identify which replies need correction, and preserve Paul's voice when editing them. Follow the user's chosen scope: assessment, suggested wording, or live edits.

## Read before writing

- Identify the document from the current conversation. Pull fresh threads with `relay review pull <library-path> --out <local-json>` and read the relevant published document with `relay library get <library-path> --out <local-html>`.
- Read each reviewer's comment and the full reply chain. A reply the user just edited is the best style sample. Preserve it unless the requested change applies to it.
- Verify technical disagreements against available code, configuration, or linked PRs. Distinguish a wrong answer from an answer that merely needs clearer wording. Short replies such as "agreed" can be sufficient.
- An assessment request authorizes reading and recommendations. A request to edit the user's replies authorizes updating those replies. Keep document edits, new replies, and thread resolution within the user's requested scope.

## Paul's reply style

Use lowercase prose by default for these review replies, including names such as dos, sms, scout, and navi. Preserve case-sensitive code identifiers when quoting them exactly; follow any more specific user direction.

Match the user's latest sample. Favor short sentences, contractions, and one or two brief paragraphs. Phrases such as "agreed. will...", "yep, will add...", and "i think it should..." fit when they reflect the actual decision. Avoid formal introductions, elaborate formatting, canned praise, or extra explanation the thread already provides.

Answer the concrete question and state the intended change. Preserve the user's uncertainty where the design is unresolved. Do not turn a proposed implementation into an accomplished change or invent commitments.

Style example:

> agreed. will name existing ops lists as the v1 onboarding receiver and define when ops accepts ownership.
>
> lists will distinguish pending vetting from workers who passed vetting or don't need it

## Edit existing messages in place

Retain each message's id, author, thread, and reply relationship. Keep the reviewer's comments, unaffected user replies, and thread statuses intact.

**Relay CLI gotcha:** `relay review push` skips message ids already on the server. Changing an existing message's text in a pulled JSON file does not edit it. Do not assign a new id to work around this; that posts an additional reply.

Use the existing-message edit endpoint:

```http
PATCH /api/reviews/threads/<thread-id>/messages/<message-id>
Content-Type: application/json

{"text":"replacement reply"}
```

The endpoint is author-only. Use the user's existing Relay authentication. On Paul's machine, the maintained client is `RelayClient` in `/Users/ple/projects/relay/cli/src/client.ts`; Bun can import it and call `RelayClient.fromDisk()` and `client.json("PATCH", path, { text })`. Inspect the current client and route before relying on this integration. Keep credentials inside the client, out of tool output.

For a fresh read through the API, use `GET /api/reviews?path=<encoded-library-path>`. Raw API messages use `author`; the CLI review JSON uses `by`.

Before each edit, compare the current server text with the text used to prepare the replacement and confirm authorship. If the user changed it meanwhile, reread and incorporate that change before writing. Apply edits sequentially. On an authorization failure, stop and report it; do not change authors or create substitute replies.

Read the threads back after editing. Confirm the exact replacement text and unchanged message ids, message counts, other messages, and thread statuses. If an edit fails partway through, check which edits saved before retrying.

Finish with a short confirmation of which replies changed and whether the user's latest edited reply was preserved. Link the document when useful. Do not claim the document was revised when only comments changed.
