# Relay publication

Publishing is optional and requires a user request. The builder always produces a local
self-contained `preview.html`. Keep the destination in the user's namespace and use the
actual path in the returned library URL. Use the destination the user supplied. When
they request a new document without a destination, resolve their authenticated Relay
namespace; if it is unavailable, ask for the destination. Do not assume the author's
namespace applies to another user.

Before replacement, read the current document with the detected Relay executable:

```bash
relay library get /<namespace>/<project>/<document>.html --out <previous-version.html>
```

Review the previous contents and preserve material outside the authorized change.
Inspect help if CLI syntax differs from the supported commands. Then publish explicitly:

```bash
python3 <skill-dir>/scripts/plan.py publish <output-dir>/preview.html \
  --path /<namespace>/<project>/<document>.html
```

The command validates the bundle, runs `relay library put`, reads it back with
`relay library get --out`, and compares bytes. A differing readback fails verification
and remains available for inspection. Open the published rendering in the user's chosen
browser when possible. Return `https://relay.traba.work/library/<namespace>/<project>/<document>.html`.

An absent Relay CLI does not block construction. Report local completion and unavailable
publication without inventing credentials or silently using a different destination.
Do not message reviewers or start review rounds unless the user asks.
