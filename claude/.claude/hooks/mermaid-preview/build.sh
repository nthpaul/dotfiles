#!/bin/sh
# Rebuilds render.mjs from main.ts and page.ts with Pele bundled in. Subscriber machines never
# run an install step, so render.mjs has to carry its dependencies. Commit the rebuilt file.
set -eu
cd "$(dirname "$0")"
bun install --frozen-lockfile
bun test
bun build main.ts --target=node --format=esm --outfile=render.mjs.tmp
{
  echo "// Built by build.sh from main.ts and page.ts. Edit those, then rebuild."
  echo "// Bundles pele $(bun -e 'console.log(require("pele/package.json").version)'), MIT License:"
  sed 's|^|// |' node_modules/pele/LICENSE
  cat render.mjs.tmp
} >render.mjs
rm render.mjs.tmp
