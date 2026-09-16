"""Small durable Grok bridge. Each run owns one detached supervisor process."""
from __future__ import annotations

from contextlib import closing, contextmanager
import fcntl
import json
import os
from pathlib import Path
import queue
import signal
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

from .grok_transport import EFFORTS, Result, command, prompt
from .grok_usage import summarize_runs
from .resources import ProcessIdentity, _snapshot, control_tree
from .runner import durable_json

TERMINAL = ('completed', 'failed', 'cancelled', 'interrupted')


def alive(identity):
    if not identity:
        return False
    try:
        return ProcessIdentity.state(identity['pid'], identity['start_identity']) not in ('exited', 'replaced', 'Z')
    except OSError:
        # Unobservable ownership must continue to fence recovery and completion.
        return True


def history_records(line):
    """Keep messages and tool evidence, excluding provider reasoning/signatures."""
    try:
        event = json.loads(line)
    except ValueError:
        return []
    if not isinstance(event, dict) or event.get('type') not in ('assistant', 'user'):
        return []
    message = event.get('message')
    if not isinstance(message, dict) or not isinstance(message.get('content'), list):
        return []
    records = []
    for part in message['content']:
        if not isinstance(part, dict):
            continue
        kind = part.get('type')
        if kind == 'text':
            records.append({'role': event['type'], 'text': part.get('text', '')})
        elif kind == 'tool_use':
            records.append({'role': 'tool_call', 'id': part.get('id'),
                            'name': part.get('name'), 'input': part.get('input')})
        elif kind == 'tool_result':
            records.append({'role': 'tool_result', 'id': part.get('tool_use_id'),
                            'content': part.get('content'), 'is_error': part.get('is_error', False)})
    return records


class Bridge:
    def __init__(self, home=None, min_free_bytes=None):
        self.home = Path(home or '~/.codex/grok-bridge').expanduser().resolve()
        self.min_free_bytes = int(os.environ.get('GROK_BRIDGE_MIN_FREE_BYTES', 1024 ** 3)
                                  if min_free_bytes is None else min_free_bytes)
        if self.min_free_bytes < 0:
            raise ValueError('min_free_bytes must be nonnegative')
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database = self.home / 'bridge.sqlite3'
        with closing(self.connect()) as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, cwd TEXT NOT NULL, adapter TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
                    request_id TEXT UNIQUE NOT NULL, request TEXT NOT NULL,
                    state TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0,
                    released INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL,
                    data TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS session_busy ON runs(session_id) WHERE released=0;
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL UNIQUE,
                    body TEXT NOT NULL);
            ''')
        os.chmod(self.database, 0o600)

    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def directory(self, run_id):
        return self.home / 'runs' / str(uuid.UUID(run_id))

    def row(self, run_id):
        with closing(self.connect()) as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
        if not row:
            raise ValueError('Unknown run ID')
        return dict(row)

    def update(self, run_id, **fields):
        with self.transaction() as db:
            row = db.execute('SELECT data FROM runs WHERE id=?', (run_id,)).fetchone()
            data = json.loads(row['data'])
            data.update(fields)
            db.execute('UPDATE runs SET data=? WHERE id=?', (json.dumps(data), run_id))

    def settle(self, run_id, state, data, released=True):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            if row['state'] in TERMINAL:
                return
            merged = json.loads(row['data'])
            saved = self.directory(run_id) / 'result.json'
            if saved.exists():
                # A durable envelope wins even if the previous DB commit failed.
                data = json.loads(saved.read_text())
                state, released = data['state'], data['released']
            merged.update(data, finished=data.get('finished', time.time()))
            # A cancellation accepted before settlement wins the race.
            if row['cancelled'] and released:
                state = 'cancelled'
            merged['state'] = state
            merged['released'] = bool(released)
            durable_json(self.directory(run_id) / 'result.json', merged)
            db.execute('UPDATE runs SET state=?,released=?,data=? WHERE id=?',
                       (state, int(released), json.dumps(merged), run_id))
            db.execute('INSERT INTO events(run_id,body) VALUES(?,?)',
                       (run_id, json.dumps({'run_id': run_id, 'session_id': row['session_id'],
                                            'state': state, 'report': merged.get('report'),
                                            'error': merged.get('error')})))

    def recover(self):
        with closing(self.connect()) as db:
            rows = list(db.execute('SELECT * FROM runs WHERE released=0'))
        for row in rows:
            data = json.loads(row['data'])
            worker = data.get('worker')
            if row['state'] in TERMINAL:
                if row['state'] == 'interrupted' and row['cancelled']:
                    self.cancel_interrupted(dict(row))
                continue
            if alive(worker):
                continue
            if worker is None and time.time() - row['created'] < 15:
                continue
            # The same lock fences a late supervisor claim and recovery. Re-read
            # under it: a snapshot taken before the claim is not proof of death.
            with (self.directory(row['id']) / 'owner.lock').open('a') as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                current = self.row(row['id'])
                if alive(json.loads(current['data']).get('worker')):
                    continue
                saved = self.directory(row['id']) / 'result.json'
                if saved.exists():
                    result = json.loads(saved.read_text())
                    self.settle(row['id'], result['state'], result, released=result['released'])
                    continue
                result = Result(row['session_id'])
                raw = self.directory(row['id']) / 'provider.jsonl'
                if raw.exists():
                    with raw.open() as stream:
                        for line in stream:
                            result.consume(line)
                evidence = result.finish(0)
                evidence.pop('state')
                evidence['error'] = 'Supervisor lost; exit/cleanup unverified. Inspect history and external effects before resuming'
                self.settle(row['id'], 'interrupted', evidence, released=False)
                if self.row(row['id'])['cancelled']:
                    self.cancel_interrupted(self.row(row['id']))

    def spawn(self, task, cwd, request_id, write_scope=None, effort='medium', adapter='grok'):
        return self._start(task, cwd, request_id, write_scope or [], effort, adapter)

    def resume(self, session_id, task, request_id, effort='medium', recovery_checked=False):
        session_id = str(uuid.UUID(session_id))
        self.recover()
        with closing(self.connect()) as db:
            session = db.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
            prior = db.execute('SELECT * FROM runs WHERE session_id=? ORDER BY created DESC LIMIT 1', (session_id,)).fetchone()
        if not session or not prior:
            raise ValueError('Unknown session ID')
        request = json.loads(prior['request'])
        return self._start(task, session['cwd'], request_id, request['write_scope'], effort,
                           session['adapter'], session_id, recovery_checked)

    def _start(self, task, cwd, request_id, write_scope, effort, adapter, session_id=None, recovery_checked=False):
        if not isinstance(task, str) or not task.strip() or not isinstance(request_id, str) or not request_id.strip():
            raise ValueError('Nonempty task and request_id required')
        if effort not in EFFORTS or adapter not in ('grok', 'fake'):
            raise ValueError('Unsupported effort or adapter')
        supplied = {'task': task, 'cwd': str(Path(cwd).expanduser().resolve()),
                    'write_scope': write_scope, 'effort': effort, 'adapter': adapter,
                    'resume_session': session_id, 'recovery_checked': recovery_checked}
        with closing(self.connect()) as db:
            previous = db.execute('SELECT * FROM runs WHERE request_id=?', (request_id,)).fetchone()
        if previous:
            original = json.loads(previous['request'])
            if any(original.get(key) != value for key, value in supplied.items()):
                raise ValueError('request_id already used with different input')
            return {'run_id': previous['id'], 'session_id': previous['session_id'], 'state': previous['state']}
        cwd = str(Path(cwd).expanduser().resolve(strict=True))
        if not Path(cwd).is_dir() or not isinstance(write_scope, list):
            raise ValueError('cwd must be a directory and write_scope a list')
        for scope in write_scope:
            if not isinstance(scope, str) or not scope or not (Path(cwd) / scope).resolve().is_relative_to(cwd):
                raise ValueError('write_scope must stay within cwd')
        for path in (self.home, Path(cwd)):
            free = shutil.disk_usage(path).free
            if free < self.min_free_bytes:
                raise ValueError(f'Insufficient disk space at {path}: {free} bytes free; '
                                 f'{self.min_free_bytes} required. Free space before retrying.')
        git = subprocess.run(['git', 'rev-parse', '--absolute-git-dir', '--git-common-dir'],
                             cwd=cwd, text=True, capture_output=True)
        gitdir, common = git.stdout.splitlines() if git.returncode == 0 else (None, None)
        worktree = str(Path(gitdir).resolve()) if gitdir else cwd
        if write_scope and adapter == 'grok':
            if not gitdir or Path(gitdir).resolve() == (Path(cwd) / common).resolve():
                raise ValueError('Writing workers require an isolated git worktree')
        if session_id:
            with closing(self.connect()) as db:
                previous = db.execute('SELECT request FROM runs WHERE session_id=? ORDER BY created LIMIT 1',
                                      (session_id,)).fetchone()
            if previous and json.loads(previous['request']).get('worktree', worktree) != worktree:
                raise ValueError('Session worktree identity changed')
        body = {'task': task, 'cwd': cwd, 'write_scope': write_scope, 'effort': effort, 'adapter': adapter,
                'resume_session': session_id, 'recovery_checked': recovery_checked, 'worktree': worktree}
        encoded = json.dumps(body, sort_keys=True)
        self.recover()
        with self.transaction() as db:
            existing = db.execute('SELECT * FROM runs WHERE request_id=?', (request_id,)).fetchone()
            if existing:
                if existing['request'] != encoded:
                    raise ValueError('request_id already used with different input')
                return {'run_id': existing['id'], 'session_id': existing['session_id'], 'state': existing['state']}
            if session_id:
                latest = db.execute('SELECT state FROM runs WHERE session_id=? ORDER BY created DESC LIMIT 1', (session_id,)).fetchone()
                if latest and latest['state'] == 'interrupted' and not recovery_checked:
                    raise ValueError('Session requires recovery_checked after an interrupted run')
            if session_id and recovery_checked:
                prior = db.execute('SELECT * FROM runs WHERE session_id=? AND released=0', (session_id,)).fetchone()
                if prior and prior['state'] == 'interrupted':
                    data = json.loads(prior['data'])
                    identities = [data.get('worker'), data.get('provider'), *data.get('children', [])]
                    if any(alive(i) for i in identities):
                        raise ValueError('Interrupted execution still has live owned processes; cancel first')
                    db.execute('UPDATE runs SET released=1 WHERE id=?', (prior['id'],))
            active = list(db.execute('SELECT * FROM runs WHERE released=0'))
            if len(active) >= 3:
                raise ValueError('Three workers already active or awaiting recovery')
            for row in active:
                other = json.loads(row['request'])
                if row['session_id'] == session_id:
                    raise ValueError('Session is busy or requires recovery_checked')
                if write_scope and other['write_scope'] and (worktree == other.get('worktree') or Path(cwd).is_relative_to(other['cwd']) or Path(other['cwd']).is_relative_to(cwd)):
                    raise ValueError('Another writer owns this working directory')
            fresh = session_id is None
            session_id = session_id or str(uuid.uuid4())
            if fresh:
                db.execute('INSERT INTO sessions VALUES(?,?,?)', (session_id, cwd, adapter))
            run_id = str(uuid.uuid4())
            directory = self.directory(run_id)
            directory.mkdir(parents=True, mode=0o700)
            durable_json(directory / 'request.json', body)
            handoff = ''
            if not fresh:
                previous = db.execute('SELECT * FROM runs WHERE session_id=? ORDER BY created DESC LIMIT 1', (session_id,)).fetchone()
                prior_data = json.loads(previous['data'])
                context = {'previous_run': previous['id'], 'execution_state': previous['state'],
                           'error': prior_data.get('error'),
                           'artifacts_directory': str(self.directory(previous['id']))}
                durable_json(directory / 'handoff.json', context)
                handoff = '\n\nPrevious execution metadata; conversation history is already retained. Read artifacts only if needed:\n' + json.dumps(context)
            (directory / 'prompt.txt').write_text(prompt(task, write_scope) + handoff)
            os.chmod(directory / 'prompt.txt', 0o600)
            data = {'resume': not fresh}
            db.execute('INSERT INTO runs(id,session_id,request_id,request,state,created,data) VALUES(?,?,?,?,?,?,?)',
                       (run_id, session_id, request_id, encoded, 'starting', time.time(), json.dumps(data)))
        self.launch(run_id)
        return {'run_id': run_id, 'session_id': session_id, 'state': self.row(run_id)['state']}

    def launch(self, run_id):
        directory = self.directory(run_id)
        environment = os.environ.copy()
        root = str(Path(__file__).resolve().parent.parent)
        environment['PYTHONPATH'] = root + os.pathsep + environment.get('PYTHONPATH', '')
        with (directory / 'supervisor.log').open('ab') as log:
            try:
                supervisor = subprocess.Popen([sys.executable, '-m', 'orchestrator.grok_bridge', '--home', str(self.home), '--run', run_id],
                                 cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True, env=environment)
                threading.Thread(target=supervisor.wait, daemon=True).start()
            except OSError as error:
                self.settle(run_id, 'failed', {'error': str(error)})

    def inspect(self, run_id=None, session_id=None, after=0, limit=100):
        self.recover()
        if run_id is not None and session_id is not None:
            raise ValueError('Specify run_id or session_id, not both')
        if not isinstance(after, int) or after < 0 or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError('after must be nonnegative; limit must be 1..200')
        if run_id is None:
            with closing(self.connect()) as db:
                rows = db.execute('SELECT id,session_id,state,created,released FROM runs WHERE (? IS NULL OR session_id=?) ORDER BY created DESC LIMIT ?',
                                  (session_id, session_id, limit)).fetchall()
            result = {'runs': [dict(r) for r in rows]}
            if session_id is not None:
                result['session_totals'] = self.session_totals(session_id)
            return result
        row = self.row(run_id)
        data = json.loads(row['data'])
        history = []
        path = self.directory(run_id) / 'history.jsonl'
        next_cursor = after
        if path.exists():
            with path.open() as stream:
                for index, line in enumerate(stream):
                    if index < after:
                        continue
                    if len(history) >= limit:
                        break
                    try:
                        item = json.loads(line)
                        # Keep tool responses small; complete records remain on disk.
                        if len(line) > 8000:
                            item = {'preview': line[:8000], 'truncated': True}
                        if sum(len(json.dumps(i)) for i in history) + len(json.dumps(item)) > 32000:
                            break
                        history.append(item)
                    except ValueError:
                        break
                    next_cursor = index + 1
        return {'run_id': run_id, 'session_id': row['session_id'], 'state': row['state'],
                'cancel_requested': bool(row['cancelled']), 'released': bool(row['released']),
                'report': data.get('report'), 'error': data.get('error'), 'usage': data.get('usage'),
                'metrics': data.get('metrics'), 'report_normalized': data.get('report_normalized', False),
                'observation_error': data.get('observation_error'),
                'session_totals': self.session_totals(row['session_id']),
                'task': json.loads(row['request'])['task'],
                'created': row['created'], 'finished': data.get('finished'),
                'artifacts_directory': str(self.directory(run_id)), 'history': history, 'cursor': next_cursor}

    def session_totals(self, session_id):
        with closing(self.connect()) as db:
            rows = db.execute('SELECT data FROM runs WHERE session_id=?', (session_id,)).fetchall()
        return summarize_runs(json.loads(row['data']) for row in rows)

    def wait(self, run_ids, after=0, timeout=30):
        if not isinstance(run_ids, list) or not run_ids or not all(isinstance(i, str) for i in run_ids):
            raise ValueError('run_ids must be a nonempty list')
        if not isinstance(after, int) or after < 0 or not isinstance(timeout, (int, float)) or not 0 <= timeout <= 30:
            raise ValueError('after must be nonnegative; timeout must be 0..30 seconds')
        for run_id in run_ids:
            self.row(run_id)
        deadline = time.monotonic() + timeout
        while True:
            self.recover()
            with closing(self.connect()) as db:
                placeholders = ','.join('?' for _ in run_ids)
                rows = db.execute(f'SELECT * FROM events WHERE sequence>? AND run_id IN ({placeholders}) ORDER BY sequence',
                                  (after, *run_ids)).fetchall()
            matches = [dict(json.loads(row['body']), sequence=row['sequence']) for row in rows if row['run_id'] in run_ids]
            for match in matches:
                data = json.loads(self.row(match['run_id'])['data'])
                match.update({key: data.get(key) for key in ('usage', 'metrics', 'report_normalized', 'observation_error')})
            states = {i: self.row(i)['state'] for i in run_ids}
            if matches or all(s in TERMINAL for s in states.values()) or time.monotonic() >= deadline:
                return {'results': matches, 'cursor': rows[-1]['sequence'] if rows else after,
                        'pending': [i for i, state in states.items() if state not in TERMINAL], 'states': states,
                        'session_totals': {m['session_id']: self.session_totals(m['session_id']) for m in matches}}
            time.sleep(0.2)

    def cancel(self, run_id):
        self.recover()
        with self.transaction() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            if not row:
                raise ValueError('Unknown run ID')
            if not row['released']:
                db.execute('UPDATE runs SET cancelled=1 WHERE id=?', (run_id,))
        return self.inspect(run_id)

    def cancel_interrupted(self, row):
        # Recovery owns this request too: a supervisor can die during cancel().
        data = json.loads(row['data'])
        for identity in [data.get('provider'), *data.get('children', [])]:
            if alive(identity):
                try:
                    control_tree(identity['pid'], identity['start_identity'], 'cancel')
                except OSError as error:
                    self.update(row['id'], observation_error=str(error))
        identities = [data.get('worker'), data.get('provider'), *data.get('children', [])]
        if not any(alive(i) for i in identities):
            with self.transaction() as db:
                db.execute('UPDATE runs SET released=1 WHERE id=?', (row['id'],))


def execute(bridge, run_id):
    directory = bridge.directory(run_id)
    with (directory / 'owner.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        with bridge.transaction() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            if row['state'] != 'starting':
                return
            data = json.loads(row['data'])
            data['worker'] = ProcessIdentity.read(os.getpid())
            db.execute('UPDATE runs SET state=?,data=? WHERE id=?', ('running', json.dumps(data), run_id))
        body = json.loads(row['request'])
        if row['cancelled']:
            bridge.settle(run_id, 'cancelled', {})
            return
        result = Result(row['session_id'])
        children = {}
        child = None
        cancelled = False
        stopped = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stopped.set())
        signal.signal(signal.SIGINT, lambda *_: stopped.set())
        events = queue.Queue()

        def drain(source, stream):
            try:
                for line in stream:
                    events.put((source, line))
            finally:
                stream.close()
                events.put((source, None))

        def capture():
            provider = json.loads(bridge.row(run_id)['data']).get('provider')
            if provider:
                children[provider['pid']] = provider
            try:
                additions = _snapshot({pid: i for pid, i in children.items() if alive(i)})
            except OSError as error:
                bridge.update(run_id, observation_error=str(error))
                return
            changed = False
            for pid, identity in additions.items():
                if children.get(pid) != identity:
                    children[pid] = identity
                    changed = True
            if changed:
                bridge.update(run_id, children=list(children.values()))

        def stop():
            for identity in list(children.values()):
                if alive(identity):
                    try:
                        observation = control_tree(identity['pid'], identity['start_identity'], 'cancel')
                    except OSError as error:
                        bridge.update(run_id, observation_error=str(error))
                        continue
                    for item in observation.get('observed', []):
                        children[item['pid']] = item
            bridge.update(run_id, children=list(children.values()))

        try:
            bridge.update(run_id, launch_intent=True)
            child = subprocess.Popen([sys.executable, '-m', 'orchestrator.grok_bridge',
                                      '--home', str(bridge.home), '--run', run_id, '--provider'],
                                     cwd=body['cwd'], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                identity = ProcessIdentity.read(child.pid)
            except OSError as error:
                bridge.update(run_id, observation_error=str(error))
                identity = None
            if identity:
                children[child.pid] = identity
                bridge.update(run_id, provider=identity, children=list(children.values()))
            for source, stream in [('stdout', child.stdout), ('stderr', child.stderr)]:
                threading.Thread(target=drain, args=(source, stream), daemon=True).start()
            closed = set()
            tick = 0
            with (directory / 'provider.jsonl').open('a') as rawlog, (directory / 'stderr.log').open('a') as errors, (directory / 'history.jsonl').open('a') as history:
                history.write(json.dumps({'role': 'user', 'text': body['task']}) + '\n')
                history.flush()
                while len(closed) < 2 or child.poll() is None or any(alive(i) for i in children.values()):
                    try:
                        source, line = events.get(timeout=0.1)
                        if line is None:
                            closed.add(source)
                        else:
                            stream = rawlog if source == 'stdout' else errors
                            stream.write(line)
                            stream.flush()
                            if source == 'stdout':
                                result.consume(line)
                                for record in history_records(line):
                                    history.write(json.dumps({'time': time.time(), **record}) + '\n')
                                history.flush()
                    except queue.Empty:
                        pass
                    if time.monotonic() >= tick:
                        capture()
                        cancelled = bool(bridge.row(run_id)['cancelled']) or stopped.is_set()
                        if cancelled:
                            stop()
                        tick = time.monotonic() + 0.5
                for stream in (rawlog, errors, history):
                    stream.flush()
                    os.fsync(stream.fileno())
            output = result.finish(child.wait())
            if result.text is not None:
                (directory / 'final.txt').write_text(result.text)
            state = output.pop('state')
            bridge.settle(run_id, 'cancelled' if cancelled else state, output)
        except BaseException as error:
            stop()
            if child is not None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            live = (child is not None and child.poll() is None) or any(alive(i) for i in children.values())
            bridge.settle(run_id, 'interrupted' if live else 'failed', {'error': str(error)}, released=not live)
            raise


def launch_provider(bridge, run_id):
    """Register before exec: even loss of the supervisor cannot create an orphan Grok."""
    with bridge.transaction() as db:
        row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
        data = json.loads(row['data'])
        if row['state'] != 'running' or row['cancelled'] or not alive(data.get('worker')):
            return
        data['provider'] = ProcessIdentity.read(os.getpid())
        if not data['provider']:
            raise RuntimeError('Cannot establish provider identity')
        db.execute('UPDATE runs SET data=? WHERE id=?', (json.dumps(data), run_id))
    body = json.loads(row['request'])
    cmd = command(body['cwd'], row['session_id'], bridge.directory(run_id) / 'prompt.txt',
                  body['effort'], data['resume'], body['adapter'])
    os.execvp(cmd[0], cmd)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--provider', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    (launch_provider if args.provider else execute)(Bridge(args.home), args.run)


if __name__ == '__main__':
    main()
