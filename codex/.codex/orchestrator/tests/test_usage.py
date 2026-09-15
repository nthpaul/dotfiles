import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator.usage import ALLOWLIST, USAGE_FIELDS, delta, envelope, exceeded, extract, fresh_baseline, snapshot, validate_budgets


class UsageTests(unittest.TestCase):
    def test_allowlist_drops_unknown_and_non_numeric(self):
        record = {'inputTokens': 10, 'outputTokens': 3, 'mystery': 99, 'modelCalls': True, 'turnCount': 2}
        self.assertEqual(extract(record, USAGE_FIELDS),
                         {'input_tokens': 10, 'output_tokens': 3, 'turn_count': 2})

    def test_resume_missing_baseline_stays_unknown(self):
        baseline = {'input_tokens': 10, 'model_calls': 2}
        current = {'input_tokens': 15, 'model_calls': 3, 'output_tokens': 8000}
        used, unknown = delta(baseline, current)
        self.assertEqual(used, {'input_tokens': 5, 'model_calls': 1})
        self.assertIn('output_tokens', unknown)
        self.assertNotIn('output_tokens', used)

    def test_fresh_baseline_zeros_are_explicit(self):
        baseline = fresh_baseline()
        self.assertEqual(baseline['output_tokens'], 0)
        current = {'output_tokens': 8, 'input_tokens': 4}
        used, unknown = delta(baseline, current)
        self.assertEqual(used['output_tokens'], 8)
        self.assertEqual(used['input_tokens'], 4)
        body = envelope('sid', True, baseline, current)
        self.assertTrue(body['fresh'])
        self.assertEqual(body['delta']['output_tokens'], 8)

    def test_snapshot_reads_session_files_not_invented_zeros(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            session = home / 'sessions' / 'cwd' / 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
            session.mkdir(parents=True)
            (session / 'usage.json').write_text(json.dumps({'session': {'inputTokens': 4, 'modelCalls': 1}}))
            (session / 'signals.json').write_text(json.dumps({'contextTokensUsed': 9, 'sessionDurationSeconds': 2}))
            with patch('orchestrator.usage.read_grok_usage', return_value={}):
                current = snapshot(session.name, home)
            self.assertEqual(current['input_tokens'], 4)
            self.assertEqual(current['model_calls'], 1)
            self.assertEqual(current['context_tokens'], 9)
            self.assertEqual(current['duration_ms'], 2000)
            self.assertNotIn('output_tokens', current)

    def test_budget_bounds_and_exceed(self):
        with self.assertRaises(ValueError):
            validate_budgets({'model_calls': 0})
        with self.assertRaises(ValueError):
            validate_budgets({'tokens': 1})
        self.assertEqual(exceeded({'model_calls': 2}, {'model_calls': 3}), ['model_calls'])
        self.assertEqual(exceeded({'model_calls': 2}, {}), [])
        self.assertEqual(set(ALLOWLIST), set(fresh_baseline()))


if __name__ == '__main__':
    unittest.main()
