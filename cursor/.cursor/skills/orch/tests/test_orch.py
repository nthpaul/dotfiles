#!/usr/bin/env python3
"""Tests for ~/.cursor/skills/orch/scripts/orch."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

ORCH_PATH = Path.home() / ".cursor" / "skills" / "orch" / "scripts" / "orch"


def load_orch() -> Any:
    loader = importlib.machinery.SourceFileLoader("orch_cli", str(ORCH_PATH))
    spec = importlib.util.spec_from_loader("orch_cli", loader)
    if spec is None:
        raise RuntimeError(f"cannot load {ORCH_PATH}")
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


orch = load_orch()


class OrchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.old_home = os.environ.get("ORCH_HOME")
        self.old_pid = os.environ.get("ORCH_PID")
        os.environ["ORCH_HOME"] = str(self.home)
        os.environ["ORCH_PID"] = str(os.getpid())

    def tearDown(self) -> None:
        if self.old_home is None:
            os.environ.pop("ORCH_HOME", None)
        else:
            os.environ["ORCH_HOME"] = self.old_home
        if self.old_pid is None:
            os.environ.pop("ORCH_PID", None)
        else:
            os.environ["ORCH_PID"] = self.old_pid
        self.tmp.cleanup()

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = orch.main(argv)
        return code, out.getvalue(), err.getvalue()

    def spawn_headless(
        self,
        team: str,
        job: str = "do the work",
        worker_id: str = "w1a2b3c4",
        kind: str = "grok",
        extra: list[str] | None = None,
    ) -> tuple[int, str, str]:
        args = ["spawn", "--team", team, "--id", worker_id, kind, *job.split()]
        if extra:
            args[1:1] = extra
        with patch.object(orch, "start_headless_wrapper", return_value=4242):
            return self.run_main(args)

    def workers(self, team: str) -> list[dict[str, Any]]:
        path = self.home / "teams" / team / "workers.json"
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return data

    def request(self, team: str, worker_id: str) -> dict[str, Any]:
        path = self.home / "teams" / team / "jobs" / worker_id / "request.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_help_is_cheat_sheet(self) -> None:
        for argv in ([], ["-h"], ["--help"], ["help"]):
            code, out, _err = self.run_main(argv)
            self.assertEqual(code, 0, argv)
            self.assertIn("orch spawn", out)
            self.assertIn("Examples:", out)
            self.assertNotIn("positional arguments", out)
            self.assertNotIn("optional arguments", out)

    def test_help_spawn(self) -> None:
        code, out, _err = self.run_main(["help", "spawn"])
        self.assertEqual(code, 0)
        self.assertIn("orch spawn --team", out)
        self.assertIn("Examples:", out)
        self.assertIn("--steal", out)

    def test_subcommand_help(self) -> None:
        code, out, _err = self.run_main(["spawn", "--help"])
        self.assertEqual(code, 0)
        self.assertIn("Examples:", out)
        self.assertIn("headless", out)
        code, out, _err = self.run_main(["kill", "-h"])
        self.assertEqual(code, 0)
        self.assertIn("orch kill --team", out)

    def test_unknown_command(self) -> None:
        code, _out, err = self.run_main(["nope"])
        self.assertEqual(code, 2)
        self.assertIn("Unknown command: nope", err)
        self.assertIn("Commands:", err)
        self.assertIn("spawn", err)

    def test_unknown_help_command(self) -> None:
        code, _out, err = self.run_main(["help", "nope"])
        self.assertEqual(code, 2)
        self.assertIn("Unknown command: nope", err)

    def test_spawn_headless_writes_request_and_workers(self) -> None:
        code, out, err = self.spawn_headless("fleet-ops", "fix the login flake")
        self.assertEqual(code, 0, err)
        self.assertIn("w1a2b3c4", out)
        req = self.request("fleet-ops", "w1a2b3c4")
        self.assertEqual(req["team"], "fleet-ops")
        self.assertEqual(req["id"], "w1a2b3c4")
        self.assertEqual(req["kind"], "grok")
        self.assertEqual(req["mode"], "headless")
        self.assertEqual(req["job"], "fix the login flake")
        self.assertIn("started_at", req)
        rows = self.workers("fleet-ops")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "w1a2b3c4")
        self.assertEqual(rows[0]["kind"], "grok")
        self.assertEqual(rows[0]["mode"], "headless")
        self.assertEqual(rows[0]["pid"], 4242)
        self.assertEqual(rows[0]["job"], "fix the login flake")
        self.assertIsNone(rows[0]["pane"])
        lock = json.loads(
            (self.home / "teams" / "fleet-ops" / "orch.json").read_text(encoding="utf-8")
        )
        self.assertEqual(lock["pid"], os.getpid())

    def test_list_team_and_all(self) -> None:
        self.spawn_headless("fleet-ops", "job one", "w11111111")
        self.spawn_headless("rbac", "job two", "w22222222")
        code, out, err = self.run_main(["list", "--team", "fleet-ops"])
        self.assertEqual(code, 0, err)
        self.assertIn("w11111111", out)
        self.assertNotIn("w22222222", out)
        code, out, err = self.run_main(["list", "--all"])
        self.assertEqual(code, 0, err)
        self.assertIn("w11111111", out)
        self.assertIn("w22222222", out)
        self.assertIn("fleet-ops", out)
        self.assertIn("rbac", out)

    def test_kill_removes_worker(self) -> None:
        self.spawn_headless("fleet-ops")
        self.assertEqual(len(self.workers("fleet-ops")), 1)
        with patch.object(orch, "terminate_pid") as term:
            code, out, err = self.run_main(["kill", "--team", "fleet-ops", "w1a2b3c4"])
        self.assertEqual(code, 0, err)
        self.assertIn("killed w1a2b3c4", out)
        self.assertEqual(self.workers("fleet-ops"), [])
        term.assert_called_once_with(4242)

    def test_tell_plus_grok_refused(self) -> None:
        code, _out, err = self.run_main(
            [
                "spawn",
                "--team",
                "demo",
                "--mode",
                "tell",
                "grok",
                "do",
                "it",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("Grok tell is not v1; use --mode headless", err)
        self.assertEqual(self.workers("demo"), [])
        self.assertFalse((self.home / "teams" / "demo" / "jobs").exists())

    def test_list_without_team_invalid(self) -> None:
        code, _out, err = self.run_main(["list"])
        self.assertEqual(code, 2)
        self.assertIn("--team", err)

    def test_kill_without_team_invalid(self) -> None:
        code, _out, err = self.run_main(["kill", "w1a2b3c4"])
        self.assertEqual(code, 2)
        self.assertIn("--team", err)

    def test_complete_teams_and_workers(self) -> None:
        self.spawn_headless("fleet-ops", "a", "w11111111")
        self.spawn_headless("rbac", "b", "w22222222")
        code, out, err = self.run_main(["complete", "teams"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), ["fleet-ops", "rbac"])
        code, out, err = self.run_main(["complete", "workers", "--team", "fleet-ops"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), ["w11111111"])
        code, out, err = self.run_main(["complete", "modes"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), ["headless", "tell"])
        code, out, err = self.run_main(["complete", "kinds"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), ["grok", "cursor"])

    def test_complete_workers_needs_team(self) -> None:
        code, _out, err = self.run_main(["complete", "workers"])
        self.assertEqual(code, 2)
        self.assertIn("--team", err)

    def test_team_name_validation(self) -> None:
        for bad in ("Fleet", "1ops", "has_under", "", "x" * 33):
            if not bad:
                continue
            code, _out, err = self.run_main(["claim", "--team", bad])
            self.assertEqual(code, 2, bad)
            self.assertIn("bad team name", err)
        code, _out, err = self.spawn_headless("BadName")
        self.assertEqual(code, 2)
        self.assertIn("bad team name", err)
        code, out, err = self.run_main(["claim", "--team", "fleet-ops"])
        self.assertEqual(code, 0, err)
        self.assertIn("claimed fleet-ops", out)

    def test_teams_empty_ok(self) -> None:
        code, out, err = self.run_main(["teams"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "")
        self.spawn_headless("alpha")
        code, out, err = self.run_main(["teams"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), ["alpha"])

    def test_live_lock_refuses_without_steal(self) -> None:
        other = os.getppid()
        team_dir = self.home / "teams" / "locked"
        team_dir.mkdir(parents=True)
        (team_dir / "orch.json").write_text(
            json.dumps({"pid": other, "claimed_at": "2026-08-19T00:00:00Z"}) + "\n",
            encoding="utf-8",
        )
        code, _out, err = self.spawn_headless("locked")
        self.assertNotEqual(code, 0)
        self.assertIn(str(other), err)
        self.assertEqual(self.workers("locked"), [])

    def test_steal_takes_live_lock(self) -> None:
        other = os.getppid()
        team_dir = self.home / "teams" / "locked"
        team_dir.mkdir(parents=True)
        (team_dir / "orch.json").write_text(
            json.dumps({"pid": other, "claimed_at": "2026-08-19T00:00:00Z"}) + "\n",
            encoding="utf-8",
        )
        code, out, err = self.spawn_headless(
            "locked", extra=["--steal"]
        )
        self.assertEqual(code, 0, err)
        self.assertIn("w1a2b3c4", out)
        lock = json.loads((team_dir / "orch.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["pid"], os.getpid())

    def test_stale_lock_is_stolen(self) -> None:
        team_dir = self.home / "teams" / "stale"
        team_dir.mkdir(parents=True)
        (team_dir / "orch.json").write_text(
            json.dumps({"pid": 999999999, "claimed_at": "2026-08-19T00:00:00Z"})
            + "\n",
            encoding="utf-8",
        )
        code, _out, err = self.spawn_headless("stale")
        self.assertEqual(code, 0, err)
        lock = json.loads((team_dir / "orch.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["pid"], os.getpid())

    def test_wrap_writes_result_json(self) -> None:
        bindir = self.home / "bin"
        bindir.mkdir()
        grok = bindir / "grok"
        grok.write_text("#!/bin/sh\necho hello from grok\n", encoding="utf-8")
        grok.chmod(0o755)
        team = "demo"
        worker_id = "w12345678"
        job = self.home / "teams" / team / "jobs" / worker_id
        job.mkdir(parents=True)
        (job / "request.json").write_text(
            json.dumps(
                {
                    "team": team,
                    "id": worker_id,
                    "kind": "grok",
                    "mode": "headless",
                    "cwd": str(self.home),
                    "job": "say hi",
                    "started_at": "2026-08-19T00:00:00Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        old_path = os.environ["PATH"]
        os.environ["PATH"] = f"{bindir}:{old_path}"
        try:
            code, _out, err = self.run_main(
                ["__wrap", "--team", team, "--id", worker_id]
            )
        finally:
            os.environ["PATH"] = old_path
        self.assertEqual(code, 0, err)
        result = json.loads((job / "result.json").read_text(encoding="utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("hello from grok", result["summary"])
        self.assertIn("finished_at", result)
        self.assertIn("hello from grok", (job / "stdout.log").read_text(encoding="utf-8"))

    def test_status_and_result(self) -> None:
        self.spawn_headless("demo")
        code, out, err = self.run_main(["status", "--team", "demo", "w1a2b3c4"])
        self.assertEqual(code, 0, err)
        self.assertIn("id: w1a2b3c4", out)
        self.assertIn("kind: grok", out)
        self.assertIn("result: (none yet)", out)
        result_path = self.home / "teams" / "demo" / "jobs" / "w1a2b3c4" / "result.json"
        result_path.write_text(
            json.dumps(
                {
                    "ok": True,
                    "exit_code": 0,
                    "finished_at": "2026-08-19T00:00:00Z",
                    "summary": "done",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        code, out, err = self.run_main(["result", "--team", "demo", "w1a2b3c4"])
        self.assertEqual(code, 0, err)
        self.assertIn('"ok": true', out)

    def test_logs(self) -> None:
        self.spawn_headless("demo")
        log = self.home / "teams" / "demo" / "jobs" / "w1a2b3c4" / "stdout.log"
        log.write_text("line one\n", encoding="utf-8")
        code, out, err = self.run_main(["logs", "--team", "demo", "w1a2b3c4"])
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "line one\n")

    def test_tell_headless_refused(self) -> None:
        self.spawn_headless("demo")
        code, _out, err = self.run_main(
            ["tell", "--team", "demo", "w1a2b3c4", "--ask", "ping"]
        )
        self.assertNotEqual(code, 0)
        self.assertIn("not tell mode", err)

    def test_release(self) -> None:
        self.run_main(["claim", "--team", "demo"])
        self.assertTrue((self.home / "teams" / "demo" / "orch.json").is_file())
        code, out, err = self.run_main(["release", "--team", "demo"])
        self.assertEqual(code, 0, err)
        self.assertIn("released demo", out)
        self.assertFalse((self.home / "teams" / "demo" / "orch.json").exists())


if __name__ == "__main__":
    unittest.main()
