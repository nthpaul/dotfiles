#!/usr/bin/env python3
"""Check explicit worktree paths across the parallel launchers with a real Git fixture."""

import runpy
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    skills_dir = Path(__file__).resolve().parents[2]
    launchers = [
        "parallelize-work/scripts/launch_parallel_ticket_work.py",
        "parallelize-work-cursor/scripts/launch_parallel_ticket_work.py",
        "watch-parallel-stacks-cursor/scripts/launch_watcher_parallel_stacks.py",
    ]
    with TemporaryDirectory(prefix="parallel-worktrees-") as temporary:
        fixture = Path(temporary).resolve()
        repo = fixture / "repo"
        worktree = fixture / "task worktree"
        subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
        subprocess.run(
            [
                "git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
                "commit", "--allow-empty", "--no-gpg-sign", "--quiet", "-m", "fixture",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--quiet", "--detach", str(worktree)],
            check=True,
        )
        subdirectory = worktree / "nested"
        subdirectory.mkdir()
        alias = fixture / "alias"
        alias.symlink_to(worktree, target_is_directory=True)

        for launcher in launchers:
            module = runpy.run_path(str(skills_dir / launcher))
            resolve = module["resolve_worktree_path"]
            assert resolve(str(worktree)) == str(worktree), launcher
            for invalid in ["relative", str(fixture), str(subdirectory), str(fixture / "missing")]:
                try:
                    resolve(invalid)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"{launcher} accepted invalid worktree path: {invalid}")

            if "parse_tasks" in module:
                task = {"issue_id": "ENG-123", "project": "repo", "worktree_path": str(worktree)}
                assert module["parse_tasks"]([task])[0].worktree_path == str(worktree)
                assert module["tmux_session_name"]("repo", "eng-123") == "work/repo/eng-123"
                duplicates = [dict(task), dict(task, issue_id="ENG-124", worktree="other", worktree_path=str(alias))]
                check_duplicate = lambda: module["parse_tasks"](duplicates)
                task.pop("worktree_path")
                validate = lambda: module["parse_tasks"]([task])
            else:
                lane = {
                    "id": "lane", "project": "repo", "worktree": "eng-123",
                    "worktree_path": str(worktree), "tasks": [{"issue_id": "ENG-123"}],
                }
                plan = {"source": "fixture", "lanes": [lane]}
                module["validate_plan"](plan)
                metadata = module["build_metadata"](plan, fixture / "run")
                assert metadata["lanes"][0]["worktree_path"] == str(worktree)
                assert metadata["lanes"][0]["session_name"] == "work/repo/eng-123"
                duplicates = {
                    "source": "fixture",
                    "lanes": [dict(lane), dict(lane, id="other", worktree="other", worktree_path=str(alias), tasks=[{"issue_id": "ENG-124"}])],
                }
                module["validate_plan"](duplicates)
                check_duplicate = lambda: module["build_metadata"](duplicates, fixture / "duplicates")
                lane.pop("worktree_path")
                validate = lambda: module["validate_plan"](plan)
            for check, message in [(validate, "worktree_path"), (check_duplicate, "separate worktree paths")]:
                try:
                    check()
                except ValueError as error:
                    assert message in str(error), launcher
                else:
                    raise AssertionError(f"{launcher} accepted invalid worktree paths: {message}")

    print("All three launchers accept prepared Git worktrees and reject invalid or missing paths.")


if __name__ == "__main__":
    main()
