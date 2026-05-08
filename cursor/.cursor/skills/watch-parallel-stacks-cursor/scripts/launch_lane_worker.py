#!/usr/bin/env python3
"""Launch one detached lane worker session in an existing worktree."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


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


def ensure_binary(name: str) -> None:
    result = run(["zsh", "-lc", f"command -v {shlex.quote(name)} >/dev/null"], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"required command not found: {name}")


def tmux_session_exists(session_name: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        check=False,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch a detached tmux worker session for one lane worktree."
    )
    parser.add_argument("--session-name", required=True, help="Tmux session name for the lane.")
    parser.add_argument("--worktree-path", required=True, help="Absolute path to the lane worktree.")
    parser.add_argument("--prompt-file", required=True, help="Prompt file for the worker.")
    parser.add_argument("--log-path", required=True, help="Log file path for pane output.")
    parser.add_argument(
        "--worker-bin",
        default="agent",
        help="Agent executable to use. Defaults to 'agent'.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be launched without starting the tmux session.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_binary("tmux")
    ensure_binary(args.worker_bin)

    worktree_path = Path(args.worktree_path).expanduser().resolve()
    prompt_file = Path(args.prompt_file).expanduser().resolve()
    log_path = Path(args.log_path).expanduser().resolve()
    if not worktree_path.is_dir():
        raise RuntimeError(f"worktree path does not exist: {worktree_path}")
    if not prompt_file.is_file():
        raise RuntimeError(f"prompt file does not exist: {prompt_file}")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    status = "dry_run"
    if tmux_session_exists(args.session_name):
        status = "skipped_existing_session"
    elif not args.dry_run:
        shell_command = (
            f'PROMPT="$(cat {shlex.quote(str(prompt_file))})"; '
            f"cd {shlex.quote(str(worktree_path))} && "
            f"{shlex.quote(args.worker_bin)} --force "
            '"$PROMPT"; '
            "printf '\\n[watch-parallel-stacks-cursor] Lane worker session exited.\\n'; "
            "exec zsh -l"
        )
        run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                args.session_name,
                "-c",
                str(worktree_path),
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
                args.session_name,
                f"cat >> {str(log_path)}",
            ]
        )
        status = "launched"

    print(
        json.dumps(
            {
                "session_name": args.session_name,
                "worktree_path": str(worktree_path),
                "prompt_file": str(prompt_file),
                "log_path": str(log_path),
                "status": status,
            },
            indent=2,
        )
    )
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
