#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
TARGET="${1:-.}"

sh "$SCRIPT_DIR/discover_repo_commands.sh" "$TARGET"
