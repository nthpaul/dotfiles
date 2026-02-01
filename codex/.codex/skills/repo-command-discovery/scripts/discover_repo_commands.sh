#!/bin/sh
set -eu

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

match_in_files() {
  pattern="$1"
  shift
  found=0
  for f in "$@"; do
    if [ -f "$f" ]; then
      found=1
      if have_cmd rg; then
        rg -n "$pattern" "$f" >/dev/null 2>&1 && return 0
      else
        grep -n "$pattern" "$f" >/dev/null 2>&1 && return 0
      fi
    fi
  done
  if [ "$found" -eq 1 ]; then
    return 1
  fi
  return 1
}

append_line() {
  var="$1"
  val="$2"
  eval "cur=\${$var:-}"
  if [ -n "$cur" ]; then
    eval "$var=\"$cur\n$val\""
  else
    eval "$var=\"$val\""
  fi
}

append_cmd() {
  var="$1"
  val="$2"
  append_line "$var" "$val"
  CMD_COUNT=$((CMD_COUNT + 1))
}

print_list() {
  label="$1"
  value="$2"
  if [ -n "${value:-}" ]; then
    echo "$label:"
    printf "%s\n" "$value" | sed 's/^/  - /'
  else
    echo "$label: (none)"
  fi
}

resolve_root() {
  start="$1"
  if [ -f "$start" ]; then
    start=$(dirname "$start")
  fi
  start=$(cd "$start" && pwd -P)
  root="$start"
  while :; do
    if [ -e "$root/.git" ] || [ -e "$root/package.json" ] || [ -e "$root/pyproject.toml" ] || \
       [ -e "$root/setup.cfg" ] || [ -e "$root/tox.ini" ] || [ -e "$root/Makefile" ]; then
      echo "$root"
      return
    fi
    parent=$(dirname "$root")
    if [ "$parent" = "$root" ]; then
      echo "$start"
      return
    fi
    root="$parent"
  done
}

START="${1:-.}"
ROOT=$(resolve_root "$START")
cd "$ROOT" || exit 1

CMD_COUNT=0
FAST_TESTS=""
FULL_TESTS=""
LINT=""
TYPECHECK=""
BUILD=""
E2E=""
NOTES=""

PM=""
if [ -f "pnpm-lock.yaml" ]; then
  PM="pnpm"
elif [ -f "yarn.lock" ]; then
  PM="yarn"
elif [ -f "package-lock.json" ] || [ -f "package.json" ]; then
  PM="npm"
fi

pkg_count=0
if have_cmd rg; then
  pkg_count=$(rg --files --no-messages -g 'package.json' -g '!**/node_modules/**' . | wc -l | tr -d ' ')
else
  pkg_count=$(find . -path './node_modules' -prune -o -name package.json -print | wc -l | tr -d ' ')
fi
if [ "$pkg_count" -gt 1 ]; then
  append_line NOTES "Multiple package.json files detected ($pkg_count). You may be in a monorepo."
fi

if [ -f "package.json" ]; then
  if have_cmd node; then
    NODE_OUT=$(PM="$PM" node -e "const fs=require('fs');const pm=process.env.PM||'npm';const pkg=JSON.parse(fs.readFileSync('package.json','utf8'));const scripts=pkg.scripts||{};const keys=Object.keys(scripts);const cmd=(s)=>pm==='yarn'?`yarn ${s}`:`${pm} run ${s}`;const emit=(k,re)=>keys.filter(x=>re.test(x)).forEach(x=>console.log(`${k}|${cmd(x)}`));emit('TEST_FAST',/^(test:(unit|fast|smoke))$/);emit('TEST_FULL',/^(test$|test:(ci|all))$/);emit('E2E',/^(e2e|test:e2e|cypress|playwright)(:.*)?$/);emit('LINT',/^(lint$|lint:(ci|check))$/);emit('TYPECHECK',/^(typecheck$|tsc$)$/);emit('BUILD',/^(build$|build:(ci|prod))$/);")
    if [ -n "$NODE_OUT" ]; then
      printf "%s\n" "$NODE_OUT" | while IFS='|' read -r kind cmd; do
        case "$kind" in
          TEST_FAST) append_cmd FAST_TESTS "$cmd" ;;
          TEST_FULL) append_cmd FULL_TESTS "$cmd" ;;
          E2E) append_cmd E2E "$cmd" ;;
          LINT) append_cmd LINT "$cmd" ;;
          TYPECHECK) append_cmd TYPECHECK "$cmd" ;;
          BUILD) append_cmd BUILD "$cmd" ;;
        esac
      done
    else
      append_line NOTES "package.json found but no standard scripts matched (test/lint/typecheck/build/e2e)."
    fi
  else
    append_line NOTES "package.json found but node is unavailable; script names were not parsed."
    if [ -n "$PM" ]; then
      append_line NOTES "Try: $PM test, $PM run test, $PM run lint, $PM run typecheck."
    fi
  fi
fi

if [ -f "Makefile" ]; then
  if grep -n '^test:' Makefile >/dev/null 2>&1; then
    append_cmd FAST_TESTS "make test"
  fi
  if grep -n '^lint:' Makefile >/dev/null 2>&1; then
    append_cmd LINT "make lint"
  fi
  if grep -n '^typecheck:' Makefile >/dev/null 2>&1; then
    append_cmd TYPECHECK "make typecheck"
  fi
  if grep -n '^build:' Makefile >/dev/null 2>&1; then
    append_cmd BUILD "make build"
  fi
  if grep -n '^e2e:' Makefile >/dev/null 2>&1; then
    append_cmd E2E "make e2e"
  fi
fi

if [ -f "tox.ini" ]; then
  append_cmd FULL_TESTS "tox"
fi
if [ -f "noxfile.py" ]; then
  append_cmd FULL_TESTS "nox"
fi

if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] || [ -f "setup.cfg" ]; then
  if match_in_files "pytest" pyproject.toml setup.cfg pytest.ini; then
    append_cmd FAST_TESTS "pytest"
  fi
fi

if [ -f "ruff.toml" ] || [ -f "pyproject.toml" ]; then
  if match_in_files "ruff" pyproject.toml ruff.toml; then
    append_cmd LINT "ruff check ."
  fi
fi

if [ -f "mypy.ini" ] || [ -f "pyproject.toml" ]; then
  if match_in_files "mypy" pyproject.toml mypy.ini; then
    append_cmd TYPECHECK "mypy ."
  fi
fi

if [ -f "pyrightconfig.json" ]; then
  append_cmd TYPECHECK "pyright"
fi

if [ -f ".pre-commit-config.yaml" ]; then
  append_line NOTES "pre-commit config found; a common lint sweep is: pre-commit run --all-files"
fi

if [ -f "tsconfig.json" ] && [ -z "$TYPECHECK" ]; then
  append_line NOTES "tsconfig.json found; consider: tsc -p . (if no typecheck script exists)"
fi

CONFIDENCE="low"
if [ "$CMD_COUNT" -ge 3 ]; then
  CONFIDENCE="high"
elif [ "$CMD_COUNT" -ge 1 ]; then
  CONFIDENCE="medium"
fi

if [ -z "$PM" ]; then
  PM="unknown"
fi

echo "ROOT=$ROOT"
echo "PACKAGE_MANAGER=$PM"
echo "CONFIDENCE=$CONFIDENCE"
print_list "FAST_TESTS" "$FAST_TESTS"
print_list "FULL_TESTS" "$FULL_TESTS"
print_list "LINT" "$LINT"
print_list "TYPECHECK" "$TYPECHECK"
print_list "BUILD" "$BUILD"
print_list "E2E" "$E2E"
print_list "NOTES" "$NOTES"
