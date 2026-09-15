import json
import subprocess
import unittest
import uuid

from orchestrator.adapters import build_command, build_wake_command, capabilities, parse_line


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.session = str(uuid.uuid4())

    def test_exact_resume_and_argument_boundaries(self):
        prompt = "--last; $(touch /tmp/not-executed)\nsecond line"
        for adapter in ("codex", "grok", "fake"):
            command = build_command(adapter, "model", "medium", self.session, prompt, "/tmp/a b")
            self.assertIn(self.session, command)
            self.assertEqual(command[-1], {"codex": prompt, "grok": "--single=" + prompt,
                                          "fake": "--prompt=" + prompt}[adapter])
            self.assertNotIn("--last", command)
            with self.assertRaises(ValueError):
                build_command(adapter, "model", "medium", "last", prompt, "/tmp")
        command = build_command("codex", "model", "medium", self.session, prompt, "/tmp")
        self.assertEqual(command[command.index("resume") + 1], self.session)
        command = build_command("grok", "model", "medium", None, prompt, "/tmp")
        uuid.UUID(command[command.index("--session-id") + 1])
        self.assertIn("--no-subagents", command)
        self.assertIn("--always-approve", command)
        self.assertNotIn("dontAsk", command)
        self.assertTrue(any(item.startswith("--single=") for item in command))

    def test_interactive_grok_preallocates_uuid_without_single(self):
        from orchestrator.adapters import build_interactive_command, capabilities, is_interactive
        command = build_interactive_command("grok-4.6", "high", self.session, "do work", "/tmp/work")
        self.assertEqual(command[0], "grok")
        self.assertNotIn("--single", command)
        self.assertFalse(any(item.startswith("--single=") or item.startswith("--prompt") for item in command))
        self.assertEqual(command[command.index("--session-id") + 1], self.session)
        self.assertEqual(command[-1], "do work")
        resume = build_interactive_command("grok-4.6", "high", self.session, "again", "/tmp/work", resume=True)
        self.assertEqual(resume[resume.index("--resume") + 1], self.session)
        self.assertNotIn("--session-id", resume)
        self.assertTrue(is_interactive({"adapter": "grok"}))
        self.assertFalse(is_interactive({"adapter": "grok", "mode": "exec"}))
        self.assertTrue(capabilities("grok")["visible_tui"])
        self.assertFalse(capabilities("grok", "exec")["visible_tui"])
        with self.assertRaises(ValueError):
            build_interactive_command("grok-4.6", "high", "latest", "x", "/tmp")

    def test_wake_requires_uuid(self):
        self.assertEqual(build_wake_command(self.session, "wake"),
                         ["codex", "queue", "--thread", self.session, "--message", "wake"])
        with self.assertRaises(ValueError):
            build_wake_command("latest", "wake")

    def test_noise_is_not_a_result(self):
        for adapter in ("codex", "grok", "fake"):
            for line in ("not json", "[]", "null", '{"type":"unknown"}'):
                self.assertEqual(parse_line(adapter, line), {})
        with self.assertRaises(ValueError):
            capabilities("unknown")

    def test_codex_result_and_failure(self):
        self.assertEqual(parse_line("codex", json.dumps({"type": "thread.started", "thread_id": self.session})),
                         {"external_session_id": self.session})
        self.assertEqual(parse_line("codex", '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}'),
                         {"text": "done", "result": "done"})
        self.assertEqual(parse_line("codex", '{"type":"turn.failed","error":{"message":"failed"}}'),
                         {"error": "failed"})

    def test_grok_avoids_duplicate_and_thinking_text(self):
        delta = {"type": "stream_event", "event": {"type": "content_block_delta",
                 "delta": {"type": "text_delta", "text": "hello"}}}
        self.assertEqual(parse_line("grok", json.dumps(delta)), {"text": "hello"})
        delta["event"]["delta"] = {"type": "thinking_delta", "thinking": "private"}
        self.assertEqual(parse_line("grok", json.dumps(delta)), {})
        self.assertEqual(parse_line("grok", '{"type":"assistant","message":{"content":[{"type":"text","text":"hello"}]}}'), {})
        self.assertEqual(parse_line("grok", '{"type":"result","subtype":"success","result":"hello"}'), {"result": "hello"})
        self.assertEqual(parse_line("grok", '{"type":"result","is_error":true,"result":"bad"}'), {"error": "bad"})

    def test_fake_success_followup_and_failure(self):
        for script, code in (({"result": "first"}, 0), ({"result": "revision"}, 0), ({"error": "blocked"}, 1)):
            prompt = "assignment\nFAKE_SCRIPT=" + json.dumps(script)
            command = build_command("fake", "fake", "medium", self.session, prompt, "/tmp")
            response = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(response.returncode, code)
            events = [parse_line("fake", line) for line in response.stdout.splitlines()]
            self.assertEqual(events[0]["external_session_id"], self.session)
            if code:
                self.assertEqual(events[-1]["error"], "blocked")
            else:
                self.assertEqual([e["result"] for e in events if "result" in e][-1], script["result"])


if __name__ == "__main__":
    unittest.main()
