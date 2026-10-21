#!/bin/sh
# Claude Code Stop hook entry point. Bazaar registers hooks without "async", and Claude Code
# waits for a Stop hook to exit, so this script returns at once and renders in the background.
# It always exits 0 and prints nothing: on Stop, exit 2 or a "decision" on stdout would make
# Claude keep going.

[ "$MERMAID_PREVIEW" = "0" ] && exit 0

dir=$(cd "$(dirname "$0")" && pwd) || exit 0

# Hooks inherit Claude Code's environment, which may not have the user's shell PATH.
runtime=""
for candidate in "$(command -v bun)" "$HOME/.bun/bin/bun" "$(command -v node)" \
  /opt/homebrew/bin/node /usr/local/bin/node; do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    runtime=$candidate
    break
  fi
done
[ -z "$runtime" ] && exit 0

input=$(mktemp "${TMPDIR:-/tmp}/mermaid-preview.XXXXXX") || exit 0
cat >"$input"

# Most replies have no diagram; skip starting a runtime for them.
if ! grep -qi 'mermaid' "$input"; then
  rm -f "$input"
  exit 0
fi

log_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/mermaid-preview"
mkdir -p "$log_dir"
("$runtime" "$dir/render.mjs" <"$input"; rm -f "$input") >/dev/null 2>>"$log_dir/errors.log" &
exit 0
