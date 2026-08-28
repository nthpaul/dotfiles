---
name: slack-as-paul
description: >
  Send Slack messages as Paul through Slack MCP. Use when the user asks to
  send, post, share, or reply in Slack, including #pauls-fleet, or when this
  session has no Slack MCP tools. Use when the user runs /slack-as-paul.
---

# Slack as Paul

Post as Paul (`U09FL4PT8AE`) through Slack MCP authenticated as Paul.
Infisical `SLACK_*` tokens are bot identities. Do not use them. Do not post as Moreno.

Message shape is in `slack-messaging`.

## Send

1. If this session has Slack MCP tools (`slack_send_message` or `slack__*`), call them as Paul.
2. If it does not, write the exact message text to a file and spawn Cursor:

```bash
~/.local/bin/cursor-agent --print --force --trust --workspace "$PWD" "$PROMPT"
```

`$PROMPT` uses this template. Substitute the user's text; do not paraphrase it.

```
Slack only. You are Paul (U09FL4PT8AE). Use the Cursor Slack MCP already authenticated as Paul. Never Infisical Slack tokens. Never post as a bot or as Moreno.

1. Post to <channel> channel_id <id> via slack_send_message.

Parent text is EXACTLY the contents of <file>
Then reply in that thread with EXACTLY the contents of <thread-file>

Do not edit repo files. Do not summarize or rewrite the text. When done, print channel_id and message timestamps.
```

Omit the thread line when there is no follow-up.

## Channel ids

- `#pauls-fleet` → `C0AC7GN9NET`

Look up other channels with Slack MCP `slack_search_channels` (in the Cursor spawn if this session lacks Slack tools). Once an id is stable, add it here.

## Done when

Print `https://trabaworkspace.slack.com/archives/<channel_id>/p<ts with the dot removed>`.
