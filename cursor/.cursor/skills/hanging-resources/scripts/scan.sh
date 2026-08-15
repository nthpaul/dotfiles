#!/usr/bin/env bash
# Back-compat: same as `hanging-resources scan`
exec "$(dirname "$0")/hanging-resources" scan "$@"
