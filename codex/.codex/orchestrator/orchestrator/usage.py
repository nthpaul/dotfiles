"""Local Grok usage snapshots. Missing counters stay missing; zeros are never invented."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

USAGE_FIELDS = {
    'inputTokens': 'input_tokens',
    'outputTokens': 'output_tokens',
    'cachedReadTokens': 'cached_read_tokens',
    'cacheCreationTokens': 'cache_creation_tokens',
    'reasoningTokens': 'reasoning_tokens',
    'totalTokens': 'total_tokens',
    'modelCalls': 'model_calls',
    'costUsdTicks': 'cost_usd_ticks',
    'turnCount': 'turn_count',
}
SIGNAL_FIELDS = {
    'contextTokensUsed': 'context_tokens',
    'contextWindowTokens': 'context_window_tokens',
    'sessionDurationSeconds': 'duration_ms',
}
ALLOWLIST = tuple(dict.fromkeys((*USAGE_FIELDS.values(), *SIGNAL_FIELDS.values())))
BUDGET_FIELDS = ('model_calls', 'input_tokens', 'output_tokens', 'context_tokens', 'time_ms')
BUDGET_USAGE = {
    'model_calls': 'model_calls',
    'input_tokens': 'input_tokens',
    'output_tokens': 'output_tokens',
    'context_tokens': 'context_tokens',
    'time_ms': 'duration_ms',
}


def _numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    return int(value)


def extract(record, mapping):
    if not isinstance(record, dict):
        return {}
    out = {}
    for source, dest in mapping.items():
        if source not in record:
            continue
        number = _numeric(record[source])
        if number is None:
            continue
        if dest == 'duration_ms' and source == 'sessionDurationSeconds':
            number *= 1000
        out[dest] = number
    return out


def session_dir(grok_home, session_id, cwd=None):
    root = Path(grok_home) / 'sessions'
    if not root.is_dir():
        return None
    if cwd:
        encoded = Path(cwd).resolve().as_posix().replace('/', '%2F')
        candidate = root / encoded / session_id
        if candidate.is_dir():
            return candidate
    matches = [path for path in root.glob('*/' + session_id) if path.is_dir()]
    return matches[0] if len(matches) == 1 else None


def read_files(directory):
    current = {}
    if directory is None:
        return current
    signals = directory / 'signals.json'
    if signals.is_file():
        try:
            current.update(extract(json.loads(signals.read_text()), SIGNAL_FIELDS))
        except (OSError, ValueError):
            pass
    for name in ('usage.json', 'grok-usage.json'):
        path = directory / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        record = data.get('session', data) if isinstance(data, dict) else {}
        current.update(extract(record, USAGE_FIELDS))
    return current


def read_grok_usage(session_id, grok_home):
    env = dict(os.environ)
    env['GROK_HOME'] = str(grok_home)
    try:
        raw = subprocess.run(['grok', 'usage', session_id], env=env, capture_output=True,
                             text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if raw.returncode != 0 or not raw.stdout.strip():
        return {}
    try:
        data = json.loads(raw.stdout)
    except ValueError:
        return {}
    return extract(data.get('session', data) if isinstance(data, dict) else {}, USAGE_FIELDS)


def snapshot(session_id, grok_home, cwd=None):
    current = read_files(session_dir(grok_home, session_id, cwd))
    current.update(read_grok_usage(session_id, grok_home))
    return current


def fresh_baseline():
    return {key: 0 for key in ALLOWLIST}


def delta(baseline, current):
    used, unknown = {}, []
    for key in ALLOWLIST:
        if key in current and key in baseline:
            used[key] = current[key] - baseline[key]
        else:
            unknown.append(key)
    return used, unknown


def envelope(session_id, fresh, baseline, current):
    used, unknown = delta(baseline, current)
    return {'session_id': session_id, 'fresh': bool(fresh), 'baseline': dict(baseline),
            'current': dict(current), 'delta': used, 'unknown': unknown}


def validate_budgets(value):
    if not isinstance(value, dict):
        raise ValueError('budgets must be an object')
    budgets = {}
    for key, raw in value.items():
        if key not in BUDGET_FIELDS:
            raise ValueError(f'Unknown budget: {key}')
        number = _numeric(raw)
        if number is None or number <= 0:
            raise ValueError(f'Budget {key} must be a positive integer')
        budgets[key] = number
    return budgets


def exceeded(budgets, usage_delta):
    hits = []
    for budget_key, usage_key in BUDGET_USAGE.items():
        limit = budgets.get(budget_key)
        if limit is None or usage_key not in usage_delta:
            continue
        if usage_delta[usage_key] > limit:
            hits.append(budget_key)
    return hits


def prepare_grok_home(isolated, source=None):
    """Hardlink account files. Never read secret contents."""
    isolated = Path(isolated)
    isolated.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(isolated, 0o700)
    source = Path(source or Path.home() / '.grok')
    for name in ('auth.json', 'config.toml'):
        origin = source / name
        target = isolated / name
        if target.exists() or not origin.is_file():
            continue
        try:
            os.link(origin, target)
        except OSError:
            # Same-filesystem hardlink is required so secrets are not duplicated
            # into the runtime home as a copied byte stream we might later log.
            raise RuntimeError(f'Cannot hardlink {name} into isolated GROK_HOME') from None
    return isolated
