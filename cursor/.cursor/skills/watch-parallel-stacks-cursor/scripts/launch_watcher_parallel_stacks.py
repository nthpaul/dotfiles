#!/usr/bin/env python3
"""Launch a durable watcher agent for dependency-aware parallel stacked work."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def run(
    command: list[str],
    *,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        text=True,
        capture_output=capture_output,
    )


def zsh(
    command: str,
    *,
    capture_output: bool = False,
    interactive: bool = False,
) -> subprocess.CompletedProcess[str]:
    flag = "-ic" if interactive else "-lc"
    return run(["zsh", flag, command], capture_output=capture_output)


def ensure_binary(name: str) -> None:
    result = run(["zsh", "-lc", f"command -v {shlex.quote(name)} >/dev/null"], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"required command not found: {name}")


def load_plan(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("plan must be a JSON object")
    if not str(data.get("source", "")).strip():
        raise ValueError("plan.source is required")
    lanes = data.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("plan.lanes must be a non-empty array")
    return data


def sanitize_name(value: str) -> str:
    cleaned = value.strip().lower().replace("/", "-").replace(" ", "-")
    cleaned = cleaned.replace(".", "_").replace(":", "_")
    return cleaned or "watcher"


def lane_session_name(project: str, worktree: str) -> str:
    return f"wt/{project}/{worktree}".replace(".", "_").replace(":", "_")


def watcher_session_name(plan_path: Path, explicit_name: str | None) -> str:
    if explicit_name:
        return explicit_name
    return f"watch/{sanitize_name(plan_path.stem)}"


def tmux_session_exists(session_name: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        check=False,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def resolve_worktree_path(project: str, worktree: str) -> str:
    cmd = f"source ~/.zshrc && wt {shlex.quote(project)} {shlex.quote(worktree)} pwd"
    result = zsh(cmd, capture_output=True, interactive=True)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("/"):
            return line
    raise RuntimeError(
        f"failed to resolve worktree path for project={project} worktree={worktree}; output was:\n{result.stdout}"
    )


def validate_plan(plan: dict[str, Any]) -> None:
    lane_ids: set[str] = set()
    issue_ids: set[str] = set()
    known_issues: set[str] = set()

    for index, lane in enumerate(plan["lanes"], start=1):
        if not isinstance(lane, dict):
            raise ValueError(f"lane #{index} must be an object")
        lane_id = str(lane.get("id", "")).strip()
        project = str(lane.get("project", "")).strip()
        worktree = str(lane.get("worktree", "")).strip()
        tasks = lane.get("tasks")
        if not lane_id:
            raise ValueError(f"lane #{index} is missing id")
        if lane_id in lane_ids:
            raise ValueError(f"duplicate lane id: {lane_id}")
        lane_ids.add(lane_id)
        if not project:
            raise ValueError(f"lane {lane_id} is missing project")
        if not worktree:
            raise ValueError(f"lane {lane_id} is missing worktree")
        if not isinstance(tasks, list) or not tasks:
            raise ValueError(f"lane {lane_id} must have a non-empty tasks array")
        for task_index, task in enumerate(tasks, start=1):
            if not isinstance(task, dict):
                raise ValueError(f"lane {lane_id} task #{task_index} must be an object")
            issue_id = str(task.get("issue_id", "")).strip()
            if not issue_id:
                raise ValueError(f"lane {lane_id} task #{task_index} is missing issue_id")
            if issue_id in issue_ids:
                raise ValueError(f"duplicate issue_id in plan: {issue_id}")
            issue_ids.add(issue_id)
            known_issues.add(issue_id)

    for lane in plan["lanes"]:
        lane_id = str(lane["id"])
        for task in lane["tasks"]:
            depends_on = task.get("depends_on", [])
            if depends_on in ("", None):
                continue
            if not isinstance(depends_on, list):
                raise ValueError(f"task {task['issue_id']} in lane {lane_id} has non-array depends_on")
            for dep in depends_on:
                dep_id = str(dep).strip()
                if dep_id and dep_id not in known_issues:
                    raise ValueError(f"task {task['issue_id']} depends on unknown issue_id: {dep_id}")


def build_metadata(plan: dict[str, Any], run_root: Path) -> dict[str, Any]:
    prompts_dir = run_root / "prompts"
    logs_dir = run_root / "logs"
    state_dir = run_root / "state"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    lanes: list[dict[str, Any]] = []
    for lane in plan["lanes"]:
        lane_id = str(lane["id"]).strip()
        project = str(lane["project"]).strip()
        worktree = str(lane["worktree"]).strip()
        worktree_path = resolve_worktree_path(project, worktree)
        safe_lane = sanitize_name(lane_id)
        lanes.append(
            {
                "id": lane_id,
                "project": project,
                "worktree": worktree,
                "worktree_path": worktree_path,
                "session_name": lane_session_name(project, worktree),
                "prompt_path": str(prompts_dir / f"lane-{safe_lane}.prompt.txt"),
                "log_path": str(logs_dir / f"lane-{safe_lane}.log"),
                "tasks": lane["tasks"],
            }
        )

    return {
        "source": plan["source"],
        "spec": str(plan.get("spec", "")).strip() or None,
        "watcher_workspace": str(plan.get("watcher_workspace", "")).strip() or str(Path.cwd()),
        "lanes": lanes,
    }


def build_initial_state(metadata: dict[str, Any], done_path: Path) -> dict[str, Any]:
    task_states: dict[str, Any] = {}
    lane_states: dict[str, Any] = {}
    for lane in metadata["lanes"]:
        lane_states[lane["id"]] = {
            "status": "pending",
            "session_name": lane["session_name"],
            "worktree_path": lane["worktree_path"],
            "current_issue_id": None,
            "last_update": None,
            "notes": [],
        }
        for task in lane["tasks"]:
            depends_on = task.get("depends_on", [])
            task_states[task["issue_id"]] = {
                "lane_id": lane["id"],
                "status": "pending",
                "depends_on": [str(dep).strip() for dep in depends_on if str(dep).strip()],
                "last_update": None,
                "pr_url": None,
                "notes": [],
            }
    return {
        "done_file": str(done_path),
        "lanes": lane_states,
        "tasks": task_states,
        "compressions": [],
        "events": [],
    }


def build_watcher_prompt(
    *,
    plan_path: Path,
    metadata_path: Path,
    state_path: Path,
    done_path: Path,
    run_root: Path,
    watcher_session: str,
) -> str:
    metadata = json.loads(metadata_path.read_text())
    lane_lines = []
    for lane in metadata["lanes"]:
        issues = ", ".join(task["issue_id"] for task in lane["tasks"])
        lane_lines.append(
            f"- lane `{lane['id']}`: session `{lane['session_name']}`, worktree `{lane['worktree_path']}`, tasks [{issues}]"
        )

    lines = [
        "Read and follow the `watch-parallel-stacks-cursor` skill before taking any other action.",
        "You are the long-running watcher and coordinator for a multi-ticket project.",
        "You own orchestration only. Child lane workers do the implementation.",
        f"Plan file: {plan_path}",
        f"Metadata file: {metadata_path}",
        f"State file: {state_path}",
        f"Completion sentinel: {done_path}",
        f"Run root: {run_root}",
        f"Your tmux session name: {watcher_session}",
        "",
        "Lane inventory:",
        *lane_lines,
        "",
        "Rules:",
        "- Read the plan, metadata, and state before launching or nudging any lane.",
        "- Keep `state.json` up to date after every launch, intervention, compression, completion, or blocker change.",
        "- Launch ready lanes in parallel, but do not start blocked tasks early.",
        "- Reuse the same lane session and same worktree for every issue in that lane.",
        "- When a lane finishes one issue, only hand it the next issue if its dependencies are satisfied.",
        "- Dependent issues in the same lane should be handled as a Graphite PR stack.",
        "- If any session context rises above 50%, wait for a natural pause, send `/compress`, press Enter, and record that in state.",
        "- Keep monitoring until every task is complete. If you ever think you are done, verify every task in state first.",
        f"- Only when every task is complete, create the file `{done_path}` and then you may exit.",
        "",
        "Use `python ~/.cursor/skills/watch-parallel-stacks-cursor/scripts/launch_lane_worker.py ...` to start each lane worker session.",
    ]
    return "\n".join(lines) + "\n"


def build_wrapper_script(
    *,
    wrapper_path: Path,
    watcher_workspace: str,
    prompt_path: Path,
    done_path: Path,
    attempts_path: Path,
    worker_bin: str,
) -> None:
    wrapper_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env zsh",
                "set -u",
                f"cd {shlex.quote(watcher_workspace)}",
                f"PROMPT_FILE={shlex.quote(str(prompt_path))}",
                f"DONE_FILE={shlex.quote(str(done_path))}",
                f"ATTEMPTS_FILE={shlex.quote(str(attempts_path))}",
                "",
                "while [[ ! -f \"$DONE_FILE\" ]]; do",
                "  ATTEMPT=1",
                "  if [[ -f \"$ATTEMPTS_FILE\" ]]; then",
                "    ATTEMPT=$(( $(<\"$ATTEMPTS_FILE\") + 1 ))",
                "  fi",
                "  printf '%s\\n' \"$ATTEMPT\" >! \"$ATTEMPTS_FILE\"",
                "  if [[ \"$ATTEMPT\" -eq 1 ]]; then",
                "    PROMPT=\"$(<\"$PROMPT_FILE\")\"",
                f"    {shlex.quote(worker_bin)} --force \"$PROMPT\"",
                "  else",
                f"    {shlex.quote(worker_bin)} --force --continue",
                "  fi",
                "  STATUS=$?",
                "  if [[ -f \"$DONE_FILE\" ]]; then",
                "    break",
                "  fi",
                "  printf '\\n[watch-parallel-stacks-cursor] Watcher exited with status %s before completion. Restarting in 5s.\\n' \"$STATUS\"",
                "  sleep 5",
                "done",
                "printf '\\n[watch-parallel-stacks-cursor] watcher.done detected. Exiting wrapper.\\n'",
                "exec zsh -l",
                "",
            ]
        )
    )
    wrapper_path.chmod(0o755)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch a durable watcher tmux session for dependency-aware parallel stacked work."
    )
    parser.add_argument("plan", help="Path to the JSON execution plan.")
    parser.add_argument(
        "--run-root",
        help="Directory for prompts, logs, and state. Defaults to ~/.cursor/tmp/watch-parallel-stacks-cursor/<timestamp>/",
    )
    parser.add_argument(
        "--worker-bin",
        default="agent",
        help="Agent executable to use. Defaults to 'agent'.",
    )
    parser.add_argument(
        "--session-name",
        help="Override the watcher tmux session name. Defaults to watch/<plan-stem>.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare metadata and print the launch plan without starting the watcher session.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_plan(plan_path)
    validate_plan(plan)

    ensure_binary("tmux")
    ensure_binary(args.worker_bin)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_root = (
        Path(args.run_root).expanduser().resolve()
        if args.run_root
        else Path.home() / ".cursor" / "tmp" / "watch-parallel-stacks-cursor" / timestamp
    )
    run_root.mkdir(parents=True, exist_ok=True)

    metadata = build_metadata(plan, run_root)
    watcher_workspace = str(Path(metadata["watcher_workspace"]).expanduser().resolve())
    session_name = watcher_session_name(plan_path, args.session_name)

    metadata_path = run_root / "state" / "metadata.json"
    state_path = run_root / "state" / "state.json"
    prompt_path = run_root / "prompts" / "watcher.prompt.txt"
    log_path = run_root / "logs" / "watcher.log"
    done_path = run_root / "state" / "watcher.done"
    attempts_path = run_root / "state" / "watcher.attempts"
    wrapper_path = run_root / "watcher-wrapper.sh"

    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    state_path.write_text(json.dumps(build_initial_state(metadata, done_path), indent=2) + "\n")
    prompt_path.write_text(
        build_watcher_prompt(
            plan_path=plan_path,
            metadata_path=metadata_path,
            state_path=state_path,
            done_path=done_path,
            run_root=run_root,
            watcher_session=session_name,
        )
    )
    build_wrapper_script(
        wrapper_path=wrapper_path,
        watcher_workspace=watcher_workspace,
        prompt_path=prompt_path,
        done_path=done_path,
        attempts_path=attempts_path,
        worker_bin=args.worker_bin,
    )

    status = "dry_run"
    if tmux_session_exists(session_name):
        status = "skipped_existing_session"
    elif not args.dry_run:
        run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                session_name,
                "-c",
                watcher_workspace,
                "zsh",
                "-lc",
                shlex.quote(str(wrapper_path)),
            ]
        )
        run(
            [
                "tmux",
                "pipe-pane",
                "-o",
                "-t",
                session_name,
                f"cat >> {str(log_path)}",
            ]
        )
        status = "launched"

    output = {
        "run_root": str(run_root),
        "watcher_session_name": session_name,
        "watcher_workspace": watcher_workspace,
        "watcher_prompt_path": str(prompt_path),
        "watcher_log_path": str(log_path),
        "watcher_state_path": str(state_path),
        "watcher_metadata_path": str(metadata_path),
        "watcher_done_path": str(done_path),
        "status": status,
        "lanes": [
            {
                "id": lane["id"],
                "project": lane["project"],
                "worktree": lane["worktree"],
                "worktree_path": lane["worktree_path"],
                "session_name": lane["session_name"],
                "prompt_path": lane["prompt_path"],
                "log_path": lane["log_path"],
                "issue_ids": [task["issue_id"] for task in lane["tasks"]],
            }
            for lane in metadata["lanes"]
        ],
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, file=sys.stderr, end="")
        if exc.stderr:
            print(exc.stderr, file=sys.stderr, end="")
        raise
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
