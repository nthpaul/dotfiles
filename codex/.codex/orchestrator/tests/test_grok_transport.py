import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid
from orchestrator.grok_transport import Result, command, prompt, report, parse_report


class GrokTransportTests(unittest.TestCase):
    def setUp(self):
        self.sid = str(uuid.uuid4())
        self.report = {'outcome': 'completed', 'summary': 'done', 'changes': [],
                       'validation': ['test passed'], 'unresolved': [], 'artifacts': []}

    def result(self, **extra):
        return json.dumps({'type': 'result', 'subtype': 'success', 'result': json.dumps(self.report), **extra})

    def test_partial_text_cannot_complete_and_reasoning_is_not_progress(self):
        result = Result(self.sid)
        self.assertEqual(result.consume(json.dumps({'type': 'stream_event', 'event': {'delta': {
            'type': 'thinking_delta', 'thinking': 'secret'}}})), {})
        result.consume(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'done'}]}}))
        self.assertEqual(result.finish(0)['state'], 'failed')
        result.consume(self.result())
        self.assertEqual(result.finish(0)['report'], self.report)

    def test_errors_override_apparent_success(self):
        for lines, code in [([self.result()], 1), ([self.result(), self.result()], 0),
                            ([self.result(is_error=True)], 0),
                            ([json.dumps({'type': 'system', 'session_id': str(uuid.uuid4())}), self.result()], 0)]:
            with self.subTest(lines=lines, code=code):
                result = Result(self.sid)
                for line in lines:
                    result.consume(line)
                self.assertEqual(result.finish(code)['state'], 'failed')

    def test_report_validation_preserves_blocked(self):
        self.report['outcome'] = 'blocked'
        self.assertEqual(report(json.dumps(self.report))['outcome'], 'blocked')
        for value in ['done', '[]', json.dumps({'outcome': 'completed'}), json.dumps({**self.report, 'changes': 'file'})]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                report(value)

    def test_unambiguous_wrappers_are_normalized_without_changing_report(self):
        raw = json.dumps(self.report)
        self.assertEqual(parse_report(raw), (self.report, False))
        for text in [f'Findings follow.\n{raw}', f'```json\n{raw}\n```', raw + '\n}',
                     f'Code: {{ ok: true }} and {{ ... }}\n{raw}',
                     f'PASS with notes.\n```json\n{raw}\n```']:
            with self.subTest(text=text):
                result = Result(self.sid)
                result.consume(json.dumps({'type': 'result', 'subtype': 'success', 'result': text}))
                done = result.finish(0)
                self.assertEqual(done['report'], self.report)
                self.assertTrue(done['report_normalized'])
                self.assertEqual(result.text, text)
                self.assertEqual(result.finish(1)['state'], 'failed')

    def test_ambiguous_and_incomplete_reports_remain_invalid(self):
        raw = json.dumps(self.report)
        for text in [raw + raw, raw + '\nActually, this failed.', raw[:-1], raw + '}}',
                     '[' + raw + ']', '[' + raw, '{' + raw, '{"nested":' + raw + '}',
                     raw.replace('"outcome": "completed"', '"outcome":"blocked","outcome":"completed"'),
                     'Findings: {"broken":\n' + raw]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                report(text)

    def test_terminal_usage_and_metrics_are_per_invocation(self):
        result = Result(self.sid)
        usage = {'input_tokens': 100, 'cache_read_input_tokens': 400, 'output_tokens': 20}
        result.consume(self.result(usage=usage, num_turns=2, total_cost_usd=.01, duration_ms=500))
        done = result.finish(0)
        self.assertEqual(done['usage'], usage)
        self.assertEqual(done['metrics'], {'num_turns': 2, 'total_cost_usd': .01, 'duration_ms': 500})

    def test_command_exact_resume_and_prompt_file(self):
        cmd = command('/tmp/a b', self.sid, Path('/tmp/prompt file'), 'xhigh', True)
        self.assertIn('--no-subagents', cmd)
        self.assertIn('--resume', cmd)
        self.assertNotIn('--session-id', cmd)
        self.assertEqual(cmd[-1], '/tmp/prompt file')
        with self.assertRaises(ValueError):
            command('/tmp', 'latest', Path('/tmp/prompt'))

    def test_fixture_runs_real_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'prompt.txt'
            path.write_text(prompt('FAKE_SCRIPT=' + json.dumps({'report': self.report}), []))
            child = subprocess.run(command(directory, self.sid, path, adapter='fake'), capture_output=True, text=True)
            result = Result(self.sid)
            for line in child.stdout.splitlines():
                result.consume(line)
            self.assertEqual(result.finish(child.returncode)['report'], self.report)
