import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.grok_pilot import collect_usage


class GrokPilotTests(unittest.TestCase):
    def test_usage_keeps_coordinator_separate_and_unfinished_worker_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            usage = {'input_tokens': 100, 'cached_input_tokens': 50, 'output_tokens': 10}
            (root / 'events.jsonl').write_text(json.dumps({'type': 'turn.completed', 'usage': usage}) + '\n')
            for name in ('complete', 'unfinished'):
                (root / 'bridge' / 'runs' / name).mkdir(parents=True)
            (root / 'bridge' / 'runs' / 'complete' / 'result.json').write_text(json.dumps({
                'state': 'completed', 'usage': {'input_tokens': 20}, 'metrics': {'num_turns': 1}}))
            result = collect_usage(root)
            self.assertEqual(result['coordinator_turn_usage'], [usage])
            self.assertEqual(result['worker_usage']['runs'], 2)
            self.assertEqual(result['worker_usage']['totals']['input_tokens'], 20)
            self.assertEqual(result['worker_usage']['measured_runs']['input_tokens'], 1)
            self.assertEqual(result['worker_states'], {'completed': 1, 'unknown': 1})
