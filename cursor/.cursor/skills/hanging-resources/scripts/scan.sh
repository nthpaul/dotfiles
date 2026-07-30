#!/usr/bin/env bash
# Scan for hanging local agent/dev resources. List only — never kill.
set -euo pipefail

AGENT_IDLE_MIN=30
ONLY=""
WORKTREES_ROOT="${TRABA_WORKTREES_ROOT:-$HOME/.traba/worktrees}"
KNOWN_REPOS=(
  "$HOME/projects/traba/traba"
  "$HOME/projects/traba/the-matrix"
)

usage() {
  cat <<'EOF'
Usage: scan.sh [--only agents|worktrees|hermes|codex|docker] [--agent-idle-min N]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --only)
      ONLY="${2:-}"
      shift 2
      ;;
    --agent-idle-min)
      AGENT_IDLE_MIN="${2:-30}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

want() {
  [[ -z "$ONLY" || "$ONLY" == "$1" ]]
}

# Convert ps etime ( [[dd-]hh:]mm:ss ) to minutes.
etime_to_min() {
  local e="$1"
  local days=0 rest="$e" hh=0 mm=0 ss=0
  if [[ "$e" == *-* ]]; then
    days="${e%%-*}"
    rest="${e#*-}"
  fi
  local IFS=':'
  # shellcheck disable=SC2086
  set -- $rest
  if [[ $# -eq 3 ]]; then
    hh=$1; mm=$2; ss=$3
  elif [[ $# -eq 2 ]]; then
    mm=$1; ss=$2
  else
    ss=$1
  fi
  echo $(( days * 1440 + 10#$hh * 60 + 10#$mm ))
}

rss_mb() {
  # ps rss is KB on macOS
  awk -v kb="$1" 'BEGIN { printf "%.0f", kb/1024 }'
}

findings=0
emit() {
  findings=$((findings + 1))
  printf '%s\n' "$1"
}

section() {
  printf '\n## %s\n' "$1"
}

# --- Idle cursor-agent ---
if want agents; then
  section "Idle cursor-agent"
  found=0
  # pid ppid etime %cpu rss command
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    pid=$(awk '{print $1}' <<<"$line")
    etime=$(awk '{print $3}' <<<"$line")
    cpu=$(awk '{print $4}' <<<"$line")
    rss=$(awk '{print $5}' <<<"$line")
    mins=$(etime_to_min "$etime")
    # ~0% CPU and older than threshold
    cpu_int=${cpu%.*}
    if (( mins < AGENT_IDLE_MIN )); then
      continue
    fi
    if (( cpu_int > 1 )); then
      continue
    fi
    cwd=$(lsof -a -d cwd -p "$pid" 2>/dev/null | awk 'NR==2 {print $NF}')
    mb=$(rss_mb "$rss")
    emit "- pid $pid · age $etime · cpu ${cpu}% · ~${mb}MB · cwd ${cwd:-?}"
    found=1
  done < <(ps -ax -o pid=,ppid=,etime=,%cpu=,rss=,command= \
    | awk '/\/cursor-agent( |$)/ && $0 !~ /worker-server/ && $0 !~ /awk/ {print}')
  if (( found == 0 )); then
    echo "(none)"
  fi
fi

# --- Stuck Hermes gateway ---
if want hermes; then
  section "Stuck Hermes gateway"
  found=0
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    pid=$(awk '{print $1}' <<<"$line")
    etime=$(awk '{print $2}' <<<"$line")
    cpu=$(awk '{print $3}' <<<"$line")
    rss=$(awk '{print $4}' <<<"$line")
    mb=$(rss_mb "$rss")
    emit "- pid $pid · age $etime · cpu ${cpu}% · ~${mb}MB · hermes_cli.main gateway restart"
    found=1
  done < <(ps -ax -o pid=,etime=,%cpu=,rss=,command= \
    | awk '/hermes_cli\.main gateway restart/ && $0 !~ /awk/ {print}')
  if (( found == 0 )); then
    echo "(none)"
  fi
fi

# --- Idle Codex sandbox ---
if want codex; then
  section "Idle Codex sandbox"
  found=0
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    pid=$(awk '{print $1}' <<<"$line")
    etime=$(awk '{print $2}' <<<"$line")
    cpu=$(awk '{print $3}' <<<"$line")
    rss=$(awk '{print $4}' <<<"$line")
    mins=$(etime_to_min "$etime")
    cpu_int=${cpu%.*}
    # Codex sandboxes: flag if >60m and idle
    if (( mins < 60 || cpu_int > 1 )); then
      continue
    fi
    cmd=$(awk '{for (i=5;i<=NF;i++) printf "%s ", $i; print ""}' <<<"$line")
    # Prefer short label
    label="codex sandbox"
    if [[ "$cmd" == */bin/node_repl* || "$cmd" == *" node_repl"* ]]; then
      label="codex node_repl"
    fi
    wd=""
    if [[ "$cmd" == *"--working-dir "* ]]; then
      wd=$(sed -n 's/.*--working-dir \([^ ]*\).*/\1/p' <<<"$cmd")
    fi
    mb=$(rss_mb "$rss")
    emit "- pid $pid · age $etime · cpu ${cpu}% · ~${mb}MB · $label${wd:+ · $wd}"
    found=1
  done < <(ps -ax -o pid=,etime=,%cpu=,rss=,command= \
    | awk '/codex sandbox|cua_node\/bin\/node_repl/ && $0 !~ /awk/ {print}')
  if (( found == 0 )); then
    echo "(none)"
  fi
fi

# --- Leftover worktrees ---
if want worktrees; then
  section "Leftover worktrees"
  found=0
  declare -A seen=()
  for repo in "${KNOWN_REPOS[@]}"; do
    [[ -d "$repo/.git" || -f "$repo/.git" ]] || continue
    while IFS= read -r wt_line; do
      [[ -z "$wt_line" ]] && continue
      path=$(awk '{print $1}' <<<"$wt_line")
      # Skip primary checkout
      [[ "$path" == "$repo" ]] && continue
      # Prefer paths under worktrees root; still report other registered extras
      key="$path"
      [[ -n "${seen[$key]+x}" ]] && continue
      seen[$key]=1
      branch=$(sed -n 's/.*\[\([^]]*\)\].*/\1/p' <<<"$wt_line")
      emit "- $path${branch:+ · [$branch]} · from $(basename "$repo")"
      found=1
    done < <(git -C "$repo" worktree list 2>/dev/null || true)
  done
  # Also list orphan dirs under worktrees root not already reported
  if [[ -d "$WORKTREES_ROOT" ]]; then
    while IFS= read -r dir; do
      [[ -z "$dir" ]] && continue
      [[ -n "${seen[$dir]+x}" ]] && continue
      # Only leaf worktree dirs (repo-slug/branch-slug)
      emit "- $dir · (dir present, not in git worktree list)"
      found=1
    done < <(find "$WORKTREES_ROOT" -mindepth 2 -maxdepth 2 -type d 2>/dev/null || true)
  fi
  if (( found == 0 )); then
    echo "(none)"
  fi
fi

# --- Docker ---
if want docker; then
  section "Docker"
  if ! docker info >/dev/null 2>&1; then
    echo "(daemon not running)"
  else
    count=$(docker ps -aq 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$count" == "0" ]]; then
      echo "(none)"
    else
      docker ps -a --format 'table {{.ID}}\t{{.Status}}\t{{.Names}}\t{{.Image}}' 2>/dev/null \
        | while IFS= read -r row; do
            [[ "$row" == ID* ]] && continue
            emit "- $row"
          done
    fi
  fi
fi

printf '\n---\n'
if (( findings == 0 )); then
  echo "Verdict: clean"
else
  echo "Verdict: $findings hanging item(s)"
fi
