"""One durable, exclusive provider-process owner per run.

The journal closes replay windows by refusing to replay an ambiguous launch. It
does not promise exactly-once model execution. Daemon observations carry stable
IDs so connection loss after a commit can be retried without duplicating events.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import queue
import shlex
import signal
import stat
import subprocess
import threading
import time
import uuid

from .adapters import build_command, parse_line
from .resources import ProcessIdentity, control_tree


def durable_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def protocol_instructions(protocol: dict) -> str:
    command = protocol['command']
    report = {'run_id': protocol['run_id'], 'type': 'conflict', 'priority': 'urgent',
              'coalescing_key': 'stable-short-issue-key', 'text': 'Explain the blocker and decision needed',
              'blocks_acceptance': True}
    return (
        '\nRuntime reporting protocol (coordinator epoch ' + str(protocol['epoch']) + '):\n'
        'You MUST report a conflict or blocking question immediately while executing '
        'and stop your dependent work until the coordinator resolves it. Use your '
        'own run_id below, a stable coalescing_key, and priority urgent. Change type '
        'to question when appropriate. Report only to the coordinator; never contact '
        'other workers. You may also report progress or proposal, but only the '
        'coordinator approves forwarding/publication.\n'
        'Example (replace the descriptive values):\n' +
        shlex.join(command + ['request', 'report', '--body', json.dumps(report)]) + '\n'
        'The CLI prints a request_id before sending. Retry a lost response with '
        'the same --request-id and identical body; do not invent a fresh ID for a retry.\n'
        'Register an existing evidence file using:\n' +
        shlex.join(command + ['request', 'artifact', '--body', json.dumps({'path': '/absolute/path/to/evidence'})]) + '\n'
        'Reference returned artifact_id values in report artifact_ids. Credential '
        'contents must never appear in prompts, output, or reports. The CLI reads '
        'the supplied credential file itself.\n'
        'Your final response is automatically finalized as result evidence by the '
        'runner. Do not submit a result report yourself and never accept your own task.\n'
    )


def assignment_prompt(assignment: dict, run: dict, protocol: dict | None = None) -> str:
    body = decoded(assignment['body'])
    spec = body['spec']
    prompt = (
        'You are a bounded worker reporting only to your coordinator. Do not spawn '
        'subagents or contact other workers. Follow the assigned scope; return '
        'findings, evidence, and unresolved issues. Do not accept your own task.\n'
        f'Run: {run["id"]}; assignment: {assignment["id"]}; '
        f'plan revision: {run["revision"]}; coordinator epoch: {body.get("epoch", 1)}\n'
        'Assignment contract:\n' + json.dumps(spec, indent=2) +
        '\nObjective:\n' + spec['objective']
    )
    if not spec.get('write', False):
        prompt += ('\nThis assignment is read-only. Do not edit project files or '
                   'perform external write actions. Runtime reports and registration '
                   'of existing evidence files are allowed.\n')
    if protocol:
        prompt += protocol_instructions(protocol)
    return prompt


class Runner:
    def __init__(self, home, run_id, token, call_fn=None):
        self.home = Path(home).expanduser().resolve()
        if Path(run_id).name != run_id or run_id in ('.', '..'):
            raise ValueError('Run ID must be a single path component')
        self.run_id, self.token = run_id, token
        if call_fn is None:
            from .client import call
            call_fn = lambda home, message: call(home, message, timeout=2)
        self.call = call_fn
        self.directory = self.home / 'runs' / run_id
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / 'journal.json'
        self.journal = {'phase': 'new', 'outbox': [], 'acked_messages': [], 'turn': 0}
        self.process = None
        self.process_identity = None
        self.stop_requested = False
        self.events = queue.Queue()
        self.children = {}
        self.last_control = None
        self.state = None

    def save(self):
        durable_json(self.path, self.journal)

    def observe(self, kind, **body):
        self.journal['outbox'].append({'op': 'runner_observe', 'run_id': self.run_id,
                                     'observation_id': str(uuid.uuid4()), 'kind': kind, 'body': body})
        self.save()
        self.flush()

    def flush(self):
        while self.journal['outbox']:
            message = self.journal['outbox'][0]
            # A provider may finish while the daemon is offline. Historical
            # birth identity remains in the journal, but cannot be verified as
            # live by the daemon anymore. Final completion still gets delivered.
            if message['kind'] == 'started':
                body = message['body']
                if not body.get('start_identity') or ProcessIdentity.state(body['pid'], body['start_identity']) in ('exited', 'replaced', 'Z'):
                    self.journal['outbox'].pop(0)
                    self.save()
                    continue
            if message['kind'] == 'control' and self.state:
                body = message['body']
                if (body['epoch'], body['generation']) != (self.state['epoch'], self.state['run']['control_generation']):
                    self.journal['outbox'].pop(0)
                    self.save()
                    continue
            try:
                self.call(self.home, dict(message, token=self.token))
            except (OSError, RuntimeError, ValueError):
                return False
            self.journal['outbox'].pop(0)
            self.save()
        return True

    def poll(self):
        try:
            state = self.call(self.home, {'op': 'runner_poll', 'token': self.token,
                                         'run_id': self.run_id})
        except (OSError, RuntimeError, ValueError):
            return None
        self.state = state
        return state

    def request_stop(self, *_):
        self.stop_requested = True

    def pending_messages(self, state):
        return [m for m in state.get('messages', [])
                if m.get('type') == 'publication' and not m.get('acknowledged_at')
                and m['id'] not in self.journal['acked_messages']]

    def protocol(self, state):
        wrapper = Path(__file__).resolve().parents[3] / '.local' / 'bin' / 'codex-orch'
        credentials = self.home / 'credentials' / (state['session']['id'] + '.json')
        return {'command': [str(wrapper), '--home', str(self.home), '--credentials', str(credentials)],
                'run_id': self.run_id, 'epoch': state['epoch']}

    @staticmethod
    def desired(state):
        if state.get('control_epoch', state['epoch']) != state['epoch']:
            return 'running'  # A stale request cannot trigger a new local action.
        return state['run']['desired']

    def signal_provider(self, action):
        if self.process_identity is None:
            return {'outcome': 'uncertain', 'observed_state': 'unknown', 'observed': [],
                    'reason': 'Provider birth identity unavailable'}
        result = control_tree(self.process_identity['pid'],
                              self.process_identity['start_identity'], action)
        for identity in result.get('observed', []):
            self.children[identity['pid']] = identity
        self.journal['children'] = list(self.children.values())
        self.save()
        if result['outcome'] == 'exited':
            for child in self.live_children():
                control_tree(child['pid'], child['start_identity'], action)
        return result

    def apply_control(self, state):
        run = state['run']
        if state.get('control_epoch', state['epoch']) != state['epoch']:
            return
        key = (state['epoch'], run['control_generation'])
        if key == self.last_control or not run['control_generation']:
            return
        desired = run['desired']
        action = {'paused': 'pause', 'running': 'resume', 'cancelled': 'cancel'}[desired]
        if self.process is None:
            result = {'outcome': 'confirmed', 'observed_state': desired,
                      'observed': [], 'reason': 'No provider process is executing'}
        else:
            result = self.signal_provider(action)
        self.last_control = key
        observed = result.get('observed_state', 'unknown')
        if observed == 'resumed':
            observed = 'running'
        self.observe('control', generation=key[1], epoch=key[0],
                     outcome=result['outcome'], observed=observed, detail=result)

    def capture_children(self):
        """Remember observed birth IDs, including reparented process-group members."""
        if self.process_identity is None:
            return
        root = self.process_identity['pid']
        if not ProcessIdentity.matches(root, self.process_identity['start_identity']):
            return
        output = subprocess.run(['ps', '-axo', 'pid=,ppid=,pgid='],
                                capture_output=True, text=True, check=True).stdout
        rows = [tuple(map(int, line.split())) for line in output.splitlines()]
        parents = {root, *(item['pid'] for item in self.live_children())}
        for _ in range(32):
            found = False
            for pid, ppid, pgid in rows:
                if pid <= 1 or pid == os.getpid() or pid in self.children:
                    continue
                if ppid in parents or pgid == root:
                    identity = ProcessIdentity.read(pid)
                    if identity:
                        self.children[pid] = identity
                        parents.add(pid)
                        found = True
            if not found:
                break
        snapshot = list(self.children.values())
        if self.journal.get('children') != snapshot:
            self.journal['children'] = snapshot
            self.save()

    def live_children(self):
        return [item for item in self.children.values()
                if ProcessIdentity.state(item['pid'], item['start_identity'])
                not in ('exited', 'replaced', 'Z')]

    def drain(self, stream, source):
        try:
            for line in iter(stream.readline, b''):
                self.events.put((source, line.decode('utf-8', errors='replace')))
        finally:
            stream.close()
            self.events.put((source, None))

    def launch(self, state, prompt, messages):
        # Successful assignment acceptance is necessary but not sufficient after
        # takeover: recheck ownership immediately before recording launch intent.
        fresh = self.poll()
        if fresh is None or not self.flush():
            return
        state = fresh
        assignment_epoch = decoded(state['assignment']['body']).get('epoch', state['epoch'])
        if assignment_epoch != state['epoch']:
            self.journal['phase'] = 'uncertain'
            self.observe('uncertain', reason='Coordinator changed before provider launch; assignment requires reconciliation')
            return
        if self.desired(state) != 'running' or self.stop_requested:
            return
        config = decoded(state['session']['config'])
        spec = decoded(state['assignment']['body'])['spec']
        adapter = config['adapter']
        command = build_command(adapter, config.get('model', ''), config.get('effort', 'medium'),
                                self.journal.get('external_id') or state['session'].get('external_id'),
                                prompt, spec['cwd'])
        self.journal.update(phase='launch_intent', turn=self.journal['turn'] + 1,
                            provider_command=command, injected_messages=[m['id'] for m in messages])
        self.save()  # Crash after this write requires reconciliation, never automatic replay.
        environment = os.environ.copy()
        if adapter == 'fake':
            package_root = str(Path(__file__).resolve().parent.parent)
            environment['PYTHONPATH'] = package_root + os.pathsep + environment.get('PYTHONPATH', '')
        try:
            self.process = subprocess.Popen(command, cwd=spec['cwd'], env=environment, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            start_new_session=True)
        except OSError as error:
            self.journal.update(phase='between_turns', exit_code=127, result=None,
                                error='Provider process could not start: ' + str(error))
            self.save()
            return
        self.process_identity = ProcessIdentity.read(self.process.pid)
        self.children = {}
        if self.process_identity:
            self.children[self.process.pid] = self.process_identity
        self.journal.update(phase='running', provider_identity=self.process_identity,
                            children=list(self.children.values()))
        self.save()
        self.observe('started', pid=self.process.pid,
                     start_identity=(self.process_identity or {}).get('start_identity'),
                     external_id=self.journal.get('external_id'))
        for source, stream in [('stdout', self.process.stdout), ('stderr', self.process.stderr)]:
            threading.Thread(target=self.drain, args=(stream, source), daemon=True).start()
        # Submission is not model processing. Ack these only after a provider session
        # record proves the submitted process has initialized, below.
        self.run_turn(adapter, state, messages)

    def run_turn(self, adapter, state, messages):
        closed = set()
        result, error = None, None
        turn_completed = False
        messages_acked = False
        last_poll = 0
        log_fd = os.open(self.directory / 'provider.log', os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(log_fd, 'a') as log:
            while len(closed) < 2 or self.process.poll() is None:
                try:
                    source, line = self.events.get(timeout=0.1)
                except queue.Empty:
                    source, line = None, None
                if source:
                    if line is None:
                        closed.add(source)
                    else:
                        log.write(line)
                        log.flush()
                        event = parse_line(adapter, line) if source == 'stdout' else {}
                        if source == 'stdout':
                            try:
                                raw = json.loads(line)
                            except ValueError:
                                raw = None
                            if isinstance(raw, dict):
                                turn_completed |= (raw.get('type') == 'turn.completed' if adapter != 'grok'
                                                   else raw.get('type') == 'result' and 'result' in event)
                        if event.get('external_session_id'):
                            external_id = event['external_session_id']
                            if external_id != self.journal.get('external_id'):
                                self.journal['external_id'] = external_id
                                self.save()
                                self.observe('session', external_id=external_id)
                        if not messages_acked and ('text' in event or 'result' in event):
                            for message in messages:
                                self.journal['acked_messages'].append(message['id'])
                                self.observe('message_ack', delivery_id=message['id'])
                            messages_acked = True
                        if event.get('text'):
                            self.observe('progress', text=event['text'])
                            print(event['text'], flush=True)
                        if 'result' in event:
                            result = event['result']
                        if event.get('error'):
                            error = event['error']
                if time.monotonic() - last_poll >= 0.3:
                    self.flush()
                    fresh = self.poll()
                    if fresh:
                        state = fresh
                        self.apply_control(state)
                    self.capture_children()
                    last_poll = time.monotonic()
                if self.stop_requested:
                    self.signal_provider('cancel')
                if self.process.poll() is not None and len(closed) < 2:
                    # Open pipes may belong to still-running tools. Continue polling
                    # and applying cancel controls until their streams close.
                    continue
            exit_code = self.process.wait()
            while self.live_children():
                fresh = self.poll()
                if fresh:
                    state = fresh
                    self.apply_control(state)
                if self.stop_requested or self.desired(state) == 'cancelled':
                    for child in self.live_children():
                        control_tree(child['pid'], child['start_identity'], 'cancel')
                time.sleep(0.1)
            log.flush()
            os.fsync(log.fileno())
        self.process = None
        self.process_identity = None
        if exit_code == 0 and (not turn_completed or result is None):
            error = error or 'Provider exited without a terminal result'
        self.journal.update(phase='between_turns', exit_code=exit_code, result=result, error=error)
        self.save()

    def execute(self):
        lock = open(self.directory / 'runner.lock', 'a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            return 0
        try:
            return self.execute_locked()
        except BaseException:
            # An unexpected parser/OS failure must not abandon a live provider.
            # The journal stays ambiguous for daemon reconciliation after exit.
            if self.process is not None:
                self.signal_provider('cancel')
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                for child in self.live_children():
                    control_tree(child['pid'], child['start_identity'], 'cancel')
            raise
        finally:
            lock.close()

    def execute_locked(self):
        if self.path.exists():
            self.journal = json.loads(self.path.read_text())
        while not self.flush():
            if self.stop_requested:
                return 1
            time.sleep(0.2)
        if self.journal['phase']=='finished':
            return 0
        while (state := self.poll()) is None:
            if self.stop_requested:
                return 1
            time.sleep(0.2)
        if self.journal['phase'] in ('launch_intent', 'running', 'uncertain'):
            self.journal['phase'] = 'uncertain'
            self.observe('uncertain', reason='Previous provider launch may have executed; explicit reconciliation required',
                         provider_identity=self.journal.get('provider_identity'))
            return 2
        if self.journal['phase'] == 'finished':
            return 0
        identity = ProcessIdentity.read(os.getpid())
        self.observe('ready', pid=os.getpid(), start_identity=identity['start_identity'])
        if self.journal['phase'] == 'new':
            assignment = state['assignment']
            delivery_id = state.get('assignment_delivery_id')
            if not delivery_id:
                delivery_id = next(m['id'] for m in state['messages']
                                   if m['event_id'] == state['run']['assignment_event'])
            self.journal.update(phase='accepted', assignment_event=assignment['id'],
                                assignment_delivery_id=delivery_id)
            self.observe('accepted', delivery_id=delivery_id)
        while True:
            fresh = self.poll()
            if fresh is None or not self.flush():
                if self.stop_requested:
                    return 1
                time.sleep(0.2)
                continue
            state = fresh
            self.apply_control(state)
            if self.stop_requested or self.desired(state) == 'cancelled':
                self.finish(-15, None, 'Runner stopped or assignment cancelled')
                return 0
            if self.desired(state) == 'paused':
                time.sleep(0.2)
                continue
            messages = self.pending_messages(state)
            if self.journal['phase'] == 'accepted':
                prompt = assignment_prompt(state['assignment'], state['run'], self.protocol(state))
            elif self.journal.get('exit_code') != 0 or self.journal.get('error') or not messages:
                self.finish(self.journal.get('exit_code', 1), self.journal.get('result'), self.journal.get('error'))
                return 0
            else:
                if not self.journal.get('external_id'):
                    self.finish(1, self.journal.get('result'), 'Cannot inject publication without exact provider session')
                    return 1
                prompt = ('Coordinator publications follow. Apply them and return an updated result.\n' +
                          protocol_instructions(self.protocol(state)))
            for message in messages:
                prompt += '\nPublication delivery ' + message['id'] + ':\n' + json.dumps(decoded(message['body']))
            self.launch(state, prompt, messages)
            if self.journal['phase'] == 'uncertain':
                return 2

    def finish(self, exit_code, result, error):
        self.journal.update(phase='finished', exit_code=exit_code, result=result, error=error)
        self.observe('finished', exit_code=exit_code, result=result, error=error)
        while not self.flush():
            if self.stop_requested:
                return
            time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--token-file', required=True)
    args = parser.parse_args()
    token_path = Path(args.token_file)
    info = token_path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('Runner token file must be owned by this user with mode 0600')
    credential = token_path.read_text().strip()
    try:
        credential = json.loads(credential)['token']
    except json.JSONDecodeError:
        pass
    runner = Runner(args.home, args.run, credential)
    signal.signal(signal.SIGTERM, runner.request_stop)
    signal.signal(signal.SIGINT, runner.request_stop)
    return runner.execute()


if __name__ == '__main__':
    raise SystemExit(main())
