"""Headless Grok transport, independent of legacy team state."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
from .adapters import parse_line

EFFORTS = ('low', 'medium', 'high', 'xhigh')
LIST_FIELDS = ('changes', 'validation', 'unresolved', 'artifacts')


def prompt(task, write_scope):
    return ('You are a bounded Grok worker reporting to Astra. Do not spawn subagents. '
            'Follow repository AGENTS.md and task authorization. Complete relevant validation; '
            'report blockers rather than waiting for input. Only edit within the write scope; '
            'empty scope means read-only. Do not publish changes, contact others, or resolve '
            'review threads unless explicitly authorized in the task.\n'
            f'Write scope relative to cwd: {json.dumps(write_scope)}\n'
            'Keep the summary brief; put detailed evidence in artifacts. '
            'Return a final JSON object without markdown fences: '
            '{"outcome":"completed|blocked|partial","summary":"result",'
            '"changes":["findings or edits"],"validation":["checks and outcomes"],'
            '"unresolved":["blockers"],"artifacts":["paths or URLs"]}.\n\nTask:\n' + task)


def command(cwd, session_id, prompt_path, effort='medium', resume=False, adapter='grok'):
    session_id = str(uuid.UUID(session_id))
    if effort not in EFFORTS:
        raise ValueError('effort must be low, medium, high, or xhigh')
    if adapter == 'fake':
        return [sys.executable, '-m', 'orchestrator.grok_fixture', '--session-id', session_id,
                '--prompt-file', str(prompt_path)]
    if adapter != 'grok':
        raise ValueError('adapter must be grok or fake')
    return ['grok', '--cwd', cwd, '--no-subagents', '--always-approve',
            '--output-format', 'streaming-messages-json', '--include-partial-messages',
            '--model', 'grok-4.6', '--reasoning-effort', effort,
            '--resume' if resume else '--session-id', session_id, '--prompt-file', str(prompt_path)]


def unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f'duplicate report key: {key}')
        value[key] = item
    return value


def parse_report(text):
    decoder = json.JSONDecoder(object_pairs_hook=unique_keys)
    normalized = False
    try:
        value = decoder.decode(text)
    except json.JSONDecodeError:
        candidate = re.search(r'\{\s*(?:"|})', text)
        if candidate is None:
            raise ValueError('report requires a JSON object')
        if text[:candidate.start()].lstrip().startswith(('[', '{', '"')):
            raise ValueError('incomplete JSON wrapper')
        value, end = decoder.raw_decode(text, candidate.start())
        suffix = text[end:].strip()
        if not re.fullmatch(r'(?:}\s*)?(?:```)?', suffix):
            raise ValueError('ambiguous or truncated report suffix')
        normalized = True
    if not isinstance(value, dict) or value.get('outcome') not in ('completed', 'blocked', 'partial'):
        raise ValueError('report requires outcome completed, blocked, or partial')
    if not isinstance(value.get('summary'), str) or not value['summary'].strip():
        raise ValueError('report requires a nonempty summary')
    for field in LIST_FIELDS:
        if not isinstance(value.get(field), list) or not all(isinstance(v, str) for v in value[field]):
            raise ValueError(f'report requires {field} as a list of strings')
    return {key: value[key] for key in ('outcome', 'summary', *LIST_FIELDS)}, normalized


def report(text):
    return parse_report(text)[0]


class Result:
    def __init__(self, session_id):
        self.session_id = session_id
        self.terminal = False
        self.text = None
        self.error = None
        self.usage = None
        self.metrics = None

    def consume(self, line):
        event = parse_line('grok', line)
        if event.get('external_session_id') not in (None, self.session_id):
            self.error = 'Provider session identity mismatch'
        if 'error' in event:
            self.error = event['error']
        try:
            raw = json.loads(line)
        except ValueError:
            return {}
        if not isinstance(raw, dict):
            return {}
        if raw.get('type') == 'result':
            if self.terminal:
                self.error = 'Provider emitted multiple terminal results'
            self.terminal = True
            self.text = event.get('result')
            if isinstance(raw.get('usage'), dict):
                self.usage = raw['usage']
            self.metrics = {key: raw[key] for key in (
                'num_turns', 'duration_ms', 'duration_api_ms', 'total_cost_usd') if key in raw}
        return {'text': event['text']} if 'text' in event else {}

    def finish(self, exit_code):
        error = self.error
        if exit_code != 0:
            error = error or f'Provider exited with code {exit_code}'
        if not self.terminal or self.text is None:
            error = error or 'Provider exited without a successful terminal result'
        parsed = None
        normalized = False
        if not error:
            try:
                parsed, normalized = parse_report(self.text)
            except (ValueError, TypeError) as failure:
                error = 'Invalid worker report: ' + str(failure)
        return {'state': 'failed' if error else 'completed', 'report': parsed,
                'error': error, 'usage': self.usage, 'metrics': self.metrics,
                'report_normalized': normalized}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd', default='.')
    parser.add_argument('--prompt-file', type=Path, required=True)
    parser.add_argument('--session-id', default=str(uuid.uuid4()))
    parser.add_argument('--effort', default='medium', choices=EFFORTS)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--adapter', default='grok', choices=('grok', 'fake'))
    args = parser.parse_args()
    result = Result(args.session_id)
    child = subprocess.run(command(str(Path(args.cwd).resolve()), args.session_id,
                                   args.prompt_file.resolve(), args.effort, args.resume, args.adapter),
                           stdin=subprocess.DEVNULL, capture_output=True, text=True)
    for line in child.stdout.splitlines():
        result.consume(line)
    output = result.finish(child.returncode)
    print(json.dumps(output))
    return 0 if output['state'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
