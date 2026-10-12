# Relay guidance when relay-design is unavailable

Use this reference only when capability discovery cannot find relay-design, or the user
requests a standalone package. Installed guidance takes precedence.

Lead with the decision, what this artifact is and the next action. Keep it understandable
without chat history. Separate existing behavior from proposed behavior and unresolved
decisions. Layer detail with descriptive headings, an anchored contents list when useful,
collapsed supporting detail, and diagrams for ownership and flows. Label mockups and sample
data. Link exact source evidence and revisions; preserve units and material uncertainty.

Use CSS root tokens. Preserve the Traba white light theme and add readable dark tokens
for both the system preference and Relay's explicit toggle:

```css
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --page-bg: #141720; --panel-bg: #1D2230; --ink: #F2F3F7;
    --text: #D7DDE5; --muted: #A6B1C0; --line: #394252;
  }
}
:root[data-theme="dark"] {
  --page-bg: #141720; --panel-bg: #1D2230; --ink: #F2F3F7;
  --text: #D7DDE5; --muted: #A6B1C0; --line: #394252;
}
```

Apply tokens to every visible region and diagram label; check narrow layouts, wrapping,
contrast and clipping in the rendered artifact. If browser access is unavailable, state
that rendering was not inspected rather than presenting static checks as visual QA.

Publish when the user requests it. Use their destination or authenticated Relay
namespace, never a fixed author's namespace. Resolve the existing `relay` executable and inspect
help for unfamiliar commands. For a new document use
`relay library put <destination> <local-file>`. Read an existing destination before
replacement and preserve content outside the authorized revision. Read back with
`relay library get <destination> --out <local-readback>` and compare contents, then
inspect the published rendering when browser access is available. Return the actual
`https://relay.traba.work/library/<destination>` link.

Publishing a document does not authorize contacting reviewers or starting an ongoing
review session. Use `relay review` only when requested. Do not create new credentials or
invent approval requirements; follow the user's actual authorization.
