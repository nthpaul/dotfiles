import unittest

from orchestrator.grok_usage import summarize_runs


class GrokUsageTests(unittest.TestCase):
    def test_partial_coverage_and_separate_cache_counters(self):
        summary = summarize_runs([
            {'usage': {'input_tokens': 10, 'cache_read_input_tokens': 100, 'output_tokens': 2},
             'metrics': {'num_turns': 3, 'total_cost_usd': .02}},
            {'usage': {'input_tokens': 4, 'cache_read_input_tokens': 0}},
            {'usage': None}, {}])
        self.assertEqual(summary['runs'], 4)
        self.assertEqual(summary['totals'], {'input_tokens': 14, 'cache_read_input_tokens': 100,
                         'output_tokens': 2, 'num_turns': 3, 'total_cost_usd': .02})
        self.assertEqual(summary['measured_runs']['input_tokens'], 2)
        self.assertEqual(summary['measured_runs']['total_cost_usd'], 1)
        self.assertNotIn('duration_ms', summary['totals'])

    def test_invalid_counters_are_unknown_and_zero_is_measured(self):
        for invalid in [-1, float('nan'), float('inf'), True, '12', None]:
            with self.subTest(value=invalid):
                self.assertEqual(summarize_runs([{'usage': {'input_tokens': invalid}}])['totals'], {})
        self.assertEqual(summarize_runs([{'usage': {'input_tokens': 0}}])['measured_runs'], {'input_tokens': 1})
