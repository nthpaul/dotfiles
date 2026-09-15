"""Deterministic interactive-pane fixture. Writes Grok-shaped session files, no model."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import time
import uuid


def encode_cwd(cwd: str) -> str:
    return str(Path(cwd).resolve()).replace('/', '%2F')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cwd', default='.')
    parser.add_argument('--fullscreen', action='store_true')
    parser.add_argument('--no-subagents', action='store_true')
    parser.add_argument('--always-approve', action='store_true')
    parser.add_argument('--model', default='grok-4.6')
    parser.add_argument('--reasoning-effort', default='high')
    parser.add_argument('--session-id')
    parser.add_argument('--resume')
    parser.add_argument('prompt', nargs='?')
    args = parser.parse_args()
    session_id = args.session_id or args.resume or str(uuid.uuid4())
    uuid.UUID(session_id)
    home = Path(os.environ.get('GROK_HOME') or (Path.home() / '.grok'))
    cwd = str(Path(args.cwd).resolve())
    directory = home / 'sessions' / encode_cwd(cwd) / session_id
    directory.mkdir(parents=True, exist_ok=True)
    script = {}
    for line in (args.prompt or '').splitlines():
        if line.startswith('FAKE_SCRIPT='):
            script = json.loads(line.removeprefix('FAKE_SCRIPT='))
            break
    result = str(script.get('result', 'Fake TUI completed assignment.'))
    (directory / 'summary.json').write_text(json.dumps({
        'info': {'id': session_id, 'cwd': cwd}, 'current_model_id': args.model}))
    (directory / 'signals.json').write_text(json.dumps({
        'turnCount': 1, 'contextTokensUsed': 10, 'contextWindowTokens': 100,
        'sessionDurationSeconds': 1}))
    (directory / 'usage.json').write_text(json.dumps({
        'sessionId': session_id,
        'session': {'inputTokens': 4, 'outputTokens': 2, 'modelCalls': 1, 'turnCount': 1,
                    'totalTokens': 6, 'cachedReadTokens': 0, 'cacheCreationTokens': 0,
                    'reasoningTokens': 0, 'costUsdTicks': 1}}))
    update = {'params': {'sessionId': session_id, 'update': {
        'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': result}}}}
    (directory / 'updates.jsonl').write_text(json.dumps(update) + '\n')
    print(result, flush=True)
    stop = {'value': bool(script.get('error'))}

    def halt(*_):
        stop['value'] = True

    signal.signal(signal.SIGTERM, halt)
    signal.signal(signal.SIGINT, halt)
    deadline = time.monotonic() + float(script.get('delay', 0.2))
    while time.monotonic() < deadline and not stop['value']:
        time.sleep(0.05)
    if script.get('error'):
        return int(script.get('exit_code', 1))
    while not stop['value'] and not script.get('exit_after', True):
        time.sleep(0.05)
    return int(script.get('exit_code', 0))


if __name__ == '__main__':
    raise SystemExit(main())
