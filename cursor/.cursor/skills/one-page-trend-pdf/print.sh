#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: print.sh /abs/path/in.html /abs/path/out.pdf" >&2
  exit 2
fi

html="$1"
pdf="$2"
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [[ ! -f "$html" ]]; then
  echo "missing html: $html" >&2
  exit 1
fi

if [[ ! -x "$chrome" ]]; then
  echo "Google Chrome not found at $chrome" >&2
  exit 1
fi

mkdir -p "$(dirname "$pdf")"
"$chrome" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf="$pdf" "file://$html"
ls -la "$pdf"
