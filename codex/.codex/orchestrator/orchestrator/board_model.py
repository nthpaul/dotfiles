"""Read-only multi-home board snapshot. Never writes and never opens receipts."""
from __future__ import annotations

import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

TABLES = ('teams', 'agents', 'sessions', 'tasks', 'runs', 'events',
          'deliveries', 'issues', 'operations', 'resources', 'artifacts')
DROP_BODY = {'thinking', 'reasoning', 'log', 'prompt', 'token', 'raw', 'messages', 'token_hash'}
USAGE_KEYS = (
    'input_tokens', 'output_tokens', 'cached_read_tokens', 'cache_creation_tokens',
    'reasoning_tokens', 'total_tokens', 'model_calls', 'cost_usd_ticks', 'turn_count',
    'context_tokens', 'context_window_tokens', 'duration_ms',
)


def sanitize_text(text):
    return ''.join(c for c in str(text) if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127))


def parse_json(value, default=None):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value:
        return {} if default is None else default
    try:
        loaded = json.loads(value)
    except ValueError:
        return {} if default is None else default
    return loaded if isinstance(loaded, dict) else ({} if default is None else default)


def parse_list(value):
    if isinstance(value, list):
        return value
    try:
        loaded = json.loads(value or '[]')
    except ValueError:
        return []
    return loaded if isinstance(loaded, list) else []


def open_readonly(home):
    path = Path(home).expanduser().resolve() / 'state.sqlite3'
    database = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    database.row_factory = sqlite3.Row
    return database


def usage_fields(value):
    if not isinstance(value, dict):
        return None
    out = {}
    for key in USAGE_KEYS:
        if key in value and isinstance(value[key], (int, float)) and not isinstance(value[key], bool):
            out[key] = value[key]
    return out or None


def stored_usage(payload):
    """Project usage exactly as stored. Do not invent zeros or recompute delta."""
    if not isinstance(payload, dict):
        return None
    result = {}
    for key in ('as_of', 'session_id'):
        if key in payload:
            result[key] = payload[key]
    for key in ('baseline', 'current', 'delta'):
        fields = usage_fields(payload.get(key))
        if fields:
            result[key] = fields
    direct = usage_fields(payload)
    if direct and 'current' not in result:
        result['current'] = direct
    return result or None


def redact_body(body, limit=160):
    data = parse_json(body)
    clean = {}
    for key, value in data.items():
        if key in DROP_BODY or 'token' in key.lower() or 'reason' in key.lower() and key not in (
                'reason', 'compatibility_reason'):
            if key in ('reason', 'compatibility_reason') and isinstance(value, str):
                clean[key] = sanitize_text(value)[:limit]
            continue
        if key in DROP_BODY:
            continue
        if isinstance(value, str):
            clean[key] = sanitize_text(value)[:limit]
        elif isinstance(value, (int, float, bool)) or value is None:
            clean[key] = value
        elif key in ('expected_head', 'head', 'passed', 'stack', 'enforcement', 'fingerprint',
                     'reused', 'exit_code', 'action', 'generation', 'desired', 'scope'):
            clean[key] = value
    return clean


def probe_pane(socket, window, pane, team=None, agent=None, purpose=None):
    try:
        result = subprocess.run(
            ['tmux', '-S', socket, 'display-message', '-p', '-t', pane,
             '#{pane_id}\t#{window_id}\t#{@orch_team}\t#{@orch_agent}\t#{@orch_purpose}\t#{pane_dead}'],
            capture_output=True, text=True, timeout=1)
    except (OSError, subprocess.SubprocessError) as error:
        return {'state': 'unknown', 'reason': str(error)}
    if result.returncode != 0 or not result.stdout.strip():
        return {'state': 'missing'}
    pid, found_window, found_team, found_agent, found_purpose, dead = (result.stdout.strip().split('\t') + [''] * 6)[:6]
    if dead == '1':
        return {'state': 'dead', 'pane': pid, 'window': found_window}
    if (window and found_window and found_window != window) or (team and found_team and found_team != team) or (
            agent and found_agent and found_agent != agent) or (purpose and found_purpose and found_purpose != purpose):
        return {'state': 'stale', 'reason': 'tmux tags or window do not match the resource record',
                'pane': pid, 'window': found_window, 'team': found_team}
    return {'state': 'live', 'socket': socket, 'window': found_window or window, 'pane': pid,
            'team': found_team, 'agent': found_agent, 'purpose': found_purpose}


def _rows(database, table):
    try:
        return [dict(row) for row in database.execute(f'SELECT * FROM {table}').fetchall()]
    except sqlite3.Error:
        return []


def _usage_for_run(home, run_id, events):
    latest = None
    for event in events:
        if event.get('run_id') == run_id and event.get('type') == 'runner_usage':
            latest = event
    if latest:
        return stored_usage(parse_json(latest.get('body')))
    path = Path(home) / 'runs' / run_id / 'usage.json'
    try:
        return stored_usage(json.loads(path.read_text()))
    except (OSError, ValueError):
        return None


def _ci_projection(operation):
    intent = parse_json(operation.get('intent'))
    outcome = parse_json(operation.get('outcome'))
    expected = intent.get('expected_head') or outcome.get('expected_head')
    if expected is None and operation.get('kind') not in ('ci_watch', 'ci', 'integration'):
        if 'expected_head' not in intent and 'head' not in outcome and 'passed' not in outcome:
            return None
    projection = {
        'kind': operation.get('kind'),
        'state': operation.get('state'),
        'expected_head': expected,
        'head': outcome.get('head'),
        'passed': outcome.get('passed'),
        'stack': outcome.get('stack'),
        'reason': outcome.get('reason') or '',
    }
    if projection['passed'] is None and projection['head'] is None and not projection['expected_head']:
        if operation.get('kind') not in ('ci_watch', 'ci'):
            return None
        projection['passed'] = None
    return projection


def load_home(home, probe=None):
    home = Path(home).expanduser().resolve()
    snapshot = {'home': str(home), 'error': None, 'schema_tables': 0}
    db_path = home / 'state.sqlite3'
    if not db_path.exists():
        snapshot['error'] = 'missing state.sqlite3'
        return snapshot
    probe = probe or probe_pane
    try:
        database = open_readonly(home)
    except sqlite3.Error as error:
        snapshot['error'] = str(error)
        return snapshot
    with closing(database):
        try:
            names = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            snapshot['schema_tables'] = len(names & set(TABLES))
            loaded = {table: _rows(database, table) for table in TABLES if table in names}
        except sqlite3.Error as error:
            snapshot['error'] = str(error)
            return snapshot

    events = loaded.get('events', [])
    runs = loaded.get('runs', [])
    for run in runs:
        run['usage'] = _usage_for_run(home, run['id'], events)
        run['drift'] = run.get('desired') != run.get('observed')

    for table, rows in loaded.items():
        for row in rows:
            row.pop('token_hash', None)
            row.pop('token', None)
            for key in ('config', 'spec', 'intent', 'outcome', 'detail', 'body'):
                if key in row and isinstance(row[key], str):
                    parsed = parse_json(row[key], default=row[key])
                    row[key] = redact_body(parsed) if key == 'body' else parsed
            if 'holds' in row:
                row['holds'] = parse_list(row['holds'])

    resources = loaded.get('resources', [])
    for resource in resources:
        detail = resource.get('detail') if isinstance(resource.get('detail'), dict) else {}
        resource['detail'] = detail
        if resource.get('kind') != 'pane':
            resource['pane_state'] = None
            continue
        identity = resource.get('identity') or ''
        socket, _, pane = identity.partition(':')
        pane = pane or detail.get('pane')
        resource['pane_state'] = probe(
            detail.get('socket') or socket, detail.get('window'), pane,
            detail.get('team') or resource.get('team_id'), detail.get('agent'), detail.get('purpose'))

    operations = loaded.get('operations', [])
    for operation in operations:
        operation['ci'] = _ci_projection(operation)

    snapshot.update(loaded)
    snapshot['teams'] = loaded.get('teams', [])
    return snapshot


def load_homes(homes, probe=None):
    return [load_home(home, probe=probe) for home in homes]


def load_coordinator_credentials(home):
    path = Path(home).expanduser().resolve() / 'coordinator.json'
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or 'token' not in data:
        return None
    return {key: data[key] for key in ('token', 'epoch', 'session_id', 'team_id') if key in data}
