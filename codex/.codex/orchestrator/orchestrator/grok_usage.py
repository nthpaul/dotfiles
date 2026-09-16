"""Sum per-invocation provider counters without treating missing usage as zero."""
import math

USAGE_KEYS = ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens', 'output_tokens')
METRIC_KEYS = ('num_turns', 'duration_ms', 'duration_api_ms', 'total_cost_usd')


def summarize_runs(records):
    totals, measured = {}, {}
    count = 0
    for record in records:
        count += 1
        for field, keys in (('usage', USAGE_KEYS), ('metrics', METRIC_KEYS)):
            source = record.get(field) or {}
            for key in keys:
                value = source.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                if value < 0 or not math.isfinite(value):
                    continue
                totals[key] = totals.get(key, 0) + value
                measured[key] = measured.get(key, 0) + 1
    return {'runs': count, 'totals': totals, 'measured_runs': measured}
