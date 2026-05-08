#!/usr/bin/env python3
"""Launch one detached interactive worker session per task in a wt-managed worktree."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Task:
    issue_id: str
    project: str
    worktree: str
    task_summary: str
    extra_prompt: str


def slugify_issue(issue_id: str) -> str:
    return issue_id.strip().lower().replace(" ", "-")


def tmux_session_name(project: str, worktree: str) -> str:
    dir_name = worktree.replace("/", "-")
    return f"wt/{project}/{dir_name}".replace(".", "_").replace(":", "_")


def load_plan(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("plan must be a JSON object")
    if not data.get("source"):
        raise ValueError("plan.source is required")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("plan.tasks must be a non-empty array")
    return data


def parse_tasks(raw_tasks: list[dict[str, Any]]) -> list[Task]:
    tasks: list[Task] = []
    for index, raw in enumerate(raw_tasks, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"task #{index} must be an object")
        issue_id = str(raw.get("issue_id", "")).strip()
        project = str(raw.get("project", "")).strip()
        if not issue_id:
            raise ValueError(f"task #{index} is missing issue_id")
        if not project:
            raise ValueError(f"task #{index} is missing project")
        worktree = str(raw.get("worktree") or slugify_issue(issue_id)).strip()
        tasks.append(
            Task(
                issue_id=issue_id,
                project=project,
                worktree=worktree,
                task_summary=str(raw.get("task_summary", "")).strip(),
                extra_prompt=str(raw.get("extra_prompt", "")).strip(),
            )
        )
    return tasks


def run(command: list[str], *, check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        text=True,
        capture_output=capture_output,
    )


def zsh(command: str, *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return run(["zsh", "-lc", command], capture_output=capture_output)


def ensure_binary(name: str) -> None:
    result = run(["zsh", "-lc", f"command -v {shlex.quote(name)} >/dev/null"], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"required command not found: {name}")


def resolve_worktree_path(task: Task) -> str:
    cmd = (
        "source ~/.zshrc && "
        f"wt {shlex.quote(task.project)} {shlex.quote(task.worktree)} pwd"
    )
    result = zsh(cmd, capture_output=True)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("/"):
            return line
    raise RuntimeError(
        f"failed to resolve worktree path for {task.issue_id}; output was:\n{result.stdout}"
    )


def build_prompt(task: Task, source: str, spec: str | None) -> str:
    sections = [
        f"Follow the linear-ticket-work workflow for Linear issue {task.issue_id}.",
        "This run is one task from a larger parallelized execution. Keep scope limited to this issue only.",
        f"Primary orchestration source: {source}",
    ]
    if spec:
        sections.append(f"Additional TRD/spec guidance: {spec}")
    if task.task_summary:
        sections.append(f"Task summary: {task.task_summary}")
    if task.extra_prompt:
        sections.append(f"Additional task guidance: {task.extra_prompt}")
    sections.append(
        "Work in the current repository worktree, follow repo instructions, run required validation, and raise the PR when the ticket is complete."
    )
    return "\n\n".join(sections) + "\n"


def tmux_session_exists(session_name: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        check=False,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def launch_task(
    *,
    task: Task,
    source: str,
    spec: str | None,
    worktree_path: str,
    run_root: Path,
    codex_bin: str,
    dry_run: bool,
) -> dict[str, str]:
    prompts_dir = run_root / "prompts"
    logs_dir = run_root / "logs"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    safe_name = task.worktree.replace("/", "-")
    prompt_path = prompts_dir / f"{safe_name}.prompt.txt"
    log_path = logs_dir / f"{safe_name}.log"
    prompt_path.write_text(build_prompt(task, source, spec))

    session_name = tmux_session_name(task.project, task.worktree)
    if tmux_session_exists(session_name):
        return {
            "issue_id": task.issue_id,
            "project": task.project,
            "worktree": task.worktree,
            "worktree_path": worktree_path,
            "session_name": session_name,
            "prompt_path": str(prompt_path),
            "log_path": str(log_path),
            "status": "skipped_existing_session",
        }

    shell_command = (
        f'PROMPT="$(cat {shlex.quote(str(prompt_path))})"; '
        f'{shlex.quote(codex_bin)} '
        f'--cd {shlex.quote(worktree_path)} '
        '--dangerously-bypass-approvals-and-sandbox '
        '--no-alt-screen '
        '"$PROMPT"; '
        f"printf '\\n[parallelize-work] Worker session exited for {task.issue_id}. "
        f"Log: {str(log_path)}\\n'; "
        "exec zsh -l"
    )

    if not dry_run:
        run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                session_name,
                "-c",
                worktree_path,
                "zsh",
                "-lc",
                shell_command,
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

    return {
        "issue_id": task.issue_id,
        "project": task.project,
        "worktree": task.worktree,
        "worktree_path": worktree_path,
        "session_name": session_name,
        "prompt_path": str(prompt_path),
        "log_path": str(log_path),
        "status": "dry_run" if dry_run else "launched",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch one wt worktree and detached interactive worker session per task from a JSON plan."
    )
    parser.add_argument("plan", help="Path to the JSON execution plan.")
    parser.add_argument(
        "--run-root",
        help="Directory for generated prompts and logs. Defaults to ~/.cursor/tmp/parallelize-work/<timestamp>/",
    )
    parser.add_argument(
        "--codex-bin",
        default="codex",
        help="Worker executable to use. Defaults to 'codex'.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve worktrees and print the launch plan without starting tmux sessions.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_plan(plan_path)
    tasks = parse_tasks(plan["tasks"])

    ensure_binary("tmux")
    ensure_binary(args.codex_bin)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_root = (
        Path(args.run_root).expanduser().resolve()
        if args.run_root
        else Path.home() / ".cursor" / "tmp" / "parallelize-work" / timestamp
    )
    run_root.mkdir(parents=True, exist_ok=True)

    spec = str(plan.get("spec", "")).strip() or None
    results: list[dict[str, str]] = []

    for task in tasks:
        worktree_path = resolve_worktree_path(task)
        results.append(
            launch_task(
                task=task,
                source=str(plan["source"]),
                spec=spec,
                worktree_path=worktree_path,
                run_root=run_root,
                codex_bin=args.codex_bin,
                dry_run=args.dry_run,
            )
        )

    print(json.dumps({"run_root": str(run_root), "results": results}, indent=2))
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
