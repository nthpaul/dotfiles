"""Headless Grok transport, independent of legacy team state."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
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


def report(text):
    value = json.loads(text)
    if not isinstance(value, dict) or value.get('outcome') not in ('completed', 'blocked', 'partial'):
        raise ValueError('report requires outcome completed, blocked, or partial')
    if not isinstance(value.get('summary'), str) or not value['summary'].strip():
        raise ValueError('report requires a nonempty summary')
    for field in LIST_FIELDS:
        if not isinstance(value.get(field), list) or not all(isinstance(v, str) for v in value[field]):
            raise ValueError(f'report requires {field} as a list of strings')
    return {key: value[key] for key in ('outcome', 'summary', *LIST_FIELDS)}


class Result:
    def __init__(self, session_id):
        self.session_id = session_id
        self.terminal = False
        self.text = None
        self.error = None
        self.usage = None

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
        return {'text': event['text']} if 'text' in event else {}

    def finish(self, exit_code):
        error = self.error
        if exit_code != 0:
            error = error or f'Provider exited with code {exit_code}'
        if not self.terminal or self.text is None:
            error = error or 'Provider exited without a successful terminal result'
        parsed = None
        if not error:
            try:
                parsed = report(self.text)
            except (ValueError, TypeError) as failure:
                error = 'Invalid worker report: ' + str(failure)
        return {'state': 'failed' if error else 'completed', 'report': parsed,
                'error': error, 'usage': self.usage}


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
