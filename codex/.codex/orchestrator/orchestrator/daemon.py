"""One Unix-socket daemon owns storage, delivery scheduling, and reconciliation."""
from __future__ import annotations

import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor
import json
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from .adapters import build_wake_command
from .client import MAX_MESSAGE
from .resources import IntegrationManager, ProcessIdentity, TmuxManager, WorktreeManager, verify_stack_ci
from .store import Store, Invalid, dump, now, require, uid


def write_private(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class Runtime:
    def __init__(self, home):
        self.store = Store(home)
        self.home = self.store.home
        self.children = {}
        self.wakes = {}
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="external-effect")
        self.external_jobs = {}
        self.stopping = False
        self.last_tick = 0

    def actor_for(self, session_id):
        actor = self.store.get('sessions', session_id)
        agent = self.store.get('agents', actor['agent_id'])
        return dict(actor, team_id=agent['team_id'], role=agent['role'])

    def internal_event(self, team_id, kind, body, run_id=None):
        team = self.store.get('teams', team_id)
        actor = self.actor_for(team['coordinator_session'])
        task = self.store.get('runs', run_id)['task_id'] if run_id else None
        event=self.store.event(actor, kind, dict(body, observation_source='runtime'), task_id=task, run_id=run_id, source='runtime')
        if kind in ('runner_missing','operation_uncertain','launch_uncertain'):
            self.store.notify(actor,event)
        return event

    def handle(self, request):
        op = request.get('op')
        store = self.store
        if op == 'ping':
            return {'pid': os.getpid(), 'schema_version': 1, 'tables': 12}
        if op == 'init':
            config = request.get('config') or {}
            result = store.bootstrap(request['objective'], config, request.get('team_id'), request.get('request_id'))
            write_private(self.home / 'credentials' / (result['session_id']+'.json'), result)
            return result
        if op == 'read':
            return store.read(request['token'], request['view'], request.get('filters'))
        if op == 'command':
            if request['kind'] in ('worktree', 'integration', 'reconcile'):
                return self.external_command(request)
            if request['kind']=='review' and request.get('body',{}).get('decision')=='accept' and not store.one('SELECT id FROM command_requests WHERE id=?',(request['request_id'],)):
                self.validate_integration_review(request)
            response = store.command(request['token'], request['request_id'], request.get('epoch'), request['kind'], request.get('body', {}))
            # The daemon retains each worker's transport credential in its private home.
            if request['kind'] in ('register', 'session') and 'token' in response:
                write_private(self.home / 'credentials' / (response['session_id'] + '.json'), response)
            return response
        if op == 'shutdown':
            store.coordinator(store.authenticate(request['token']), request.get('epoch'))
            self.stopping = True
            return {'stopping': True, 'workers_continue': True}
        if op in ('runner_poll', 'runner_observe'):
            actor = store.authenticate(request['token'])
            require(actor['role'] == 'worker', 'Worker credential required')
            run = store.owned(actor, 'runs', request['run_id'])
            if op == 'runner_poll':
                return self.runner_poll(actor, run)
            return self.runner_observe(actor, run, request)
        raise Invalid('Unknown protocol operation')

    def runner_poll(self, actor, run):
        require(not run['released'],'Run already released; old runner cannot consume new work')
        store = self.store
        assignment = store.get('events', run['assignment_event'])
        delivery = store.one('SELECT * FROM deliveries WHERE event_id=? AND recipient=?', (assignment['id'], actor['agent_id']))
        control = store.one("SELECT * FROM events WHERE run_id=? AND type='control_requested' ORDER BY sequence DESC LIMIT 1", (run['id'],))
        messages = store.all("SELECT d.*,e.type,e.body FROM deliveries d JOIN events e ON e.id=d.event_id WHERE d.recipient=? AND (d.target_session IS NULL OR d.target_session=?) AND d.state IN ('pending','delivered') AND e.type='publication' ORDER BY e.sequence", (actor['agent_id'], actor['id']))
        with store.transaction():
            store.update('runs', run['id'], heartbeat=now())
            store.update('sessions', actor['id'], heartbeat=now())
        return {'run': run, 'assignment': assignment, 'assignment_delivery_id': delivery['id'],
                'session': {k:v for k,v in actor.items() if k != 'token_hash'}, 'messages': messages,
                'epoch': store.team(actor)['epoch'],
                'control_epoch': json.loads(control['body'])['epoch'] if control else json.loads(assignment['body'])['epoch']}

    def runner_observe(self, actor, run, request):
        store = self.store
        observation_id = request.get('observation_id')
        require(isinstance(observation_id, str) and observation_id, 'Observation ID required')
        payload = dump({k:v for k,v in request.items() if k != 'token'})
        with store.transaction():
            previous = store.one('SELECT * FROM command_requests WHERE id=?', (observation_id,))
            if previous:
                require(previous['session_id'] == actor['id'] and previous['payload'] == payload, 'Observation ID collision')
                return json.loads(previous['response'])
            body, kind = request.get('body', {}), request['kind']
            result = self.apply_observation(actor, run, kind, body)
            store.insert('command_requests', id=observation_id, session_id=actor['id'], payload=payload, response=dump(result), created=now())
            return result

    def apply_observation(self, actor, run, kind, body):
        store = self.store
        if kind in ('accepted','control','message_ack','uncertain'):
            require(not run['released'],'Released run cannot consume work or change execution')
        if kind == 'ready':
            identity = ProcessIdentity.read(body['pid'])
            require(identity and identity['start_identity'] == body['start_identity'], 'Runner identity mismatch')
            require(not run['released'], 'Released run')
            if run['runner_pid']:
                require(run['runner_pid'] == body['pid'] and run['runner_identity'] == body['start_identity'], 'Another runner owns this attempt')
            store.update('runs', run['id'], runner_pid=body['pid'], runner_identity=body['start_identity'], heartbeat=now())
            operation = store.one("SELECT * FROM operations WHERE run_id=? AND kind='launch' ORDER BY created DESC LIMIT 1", (run['id'],))
            store.update('operations', operation['id'], state='succeeded', outcome=dump(identity), updated=now())
        elif kind == 'accepted':
            delivery = store.get('deliveries', body['delivery_id'])
            require(delivery['event_id'] == run['assignment_event'], 'Not this run assignment')
            assignment = store.get('events', run['assignment_event'])
            require(json.loads(assignment['body'])['epoch'] == store.team(actor)['epoch'], 'Stale assignment awaiting coordinator reconciliation')
            store.cmd_ack(actor, {'delivery_id': delivery['id']})
        elif kind == 'started':
            require(not run['released'], 'Released run')
            identity = ProcessIdentity.read(body['pid'])
            require(identity and identity['start_identity'] == body['start_identity'], 'Child identity mismatch')
            key = f"{body['pid']}:{body['start_identity']}"
            resource = store.one("SELECT * FROM resources WHERE kind='process' AND identity=?", (key,))
            if resource:
                require(resource['team_id']==actor['team_id'] and resource['owner_run']==run['id'], 'Process already owned by another run')
            if not resource:
                store.insert('resources', id=uid('resource'), team_id=actor['team_id'], kind='process', identity=key, detail=dump(identity), owner_run=run['id'], state='held')
            store.update('runs', run['id'], health='running', observed='running', heartbeat=now())
            if body.get('external_id'):
                require(not actor['external_id'] or actor['external_id']==body['external_id'], 'Provider changed session identity')
                store.update('sessions', actor['id'], external_id=body['external_id'])
        elif kind == 'session':
            # Subsequent turns must resume the same conversation.
            require(not actor['external_id'] or actor['external_id'] == body['external_id'], 'Provider changed session identity')
            store.update('sessions', actor['id'], external_id=body['external_id'])
        elif kind == 'progress':
            store.cmd_report(actor, {'run_id': run['id'], 'type': 'progress', 'text': body.get('text', '')})
        elif kind == 'control':
            require(body.get('epoch') == store.team(actor)['epoch'] and body.get('generation') == run['control_generation'], 'Stale control observation')
            requested = store.one("SELECT * FROM events WHERE run_id=? AND type='control_requested' ORDER BY sequence DESC LIMIT 1", (run['id'],))
            require(requested and json.loads(requested['body'])['epoch'] == body['epoch'], 'Control was requested by a stale coordinator')
            observed = body.get('observed', 'unknown')
            require(observed in ('running', 'paused', 'cancelled', 'exited', 'unknown'), 'Invalid observed execution')
            values = {'observed': observed}
            if body.get('outcome') in ('confirmed', 'exited'):
                require(observed == run['desired'] or observed == 'exited', 'Control outcome does not match request')
                values['confirmed_generation'] = body['generation']
            store.update('runs', run['id'], **values)
        elif kind == 'message_ack':
            delivery = store.get('deliveries', body['delivery_id'])
            require(store.get('events', delivery['event_id'])['type'] == 'publication', 'Not a publication')
            store.cmd_ack(actor, body)
        elif kind == 'finished':
            require(not run['released'], 'Run already finished')
            # Runner reports only after reaping the provider and checking its observed tools.
            if body.get('uncertain'):
                store.update('runs', run['id'], health='unresponsive', observed='unknown', outcome='uncertain')
                store.db.execute("UPDATE resources SET state='quarantined' WHERE owner_run=? AND state='held'", (run['id'],))
            else:
                for resource in store.all("SELECT * FROM resources WHERE owner_run=? AND kind='process'", (run['id'],)):
                    detail = json.loads(resource['detail'])
                    require(ProcessIdentity.state(detail['pid'], detail['start_identity']) in ('exited','replaced','Z'), 'Provider still alive; execution cannot be released')
                result_text = body.get('result', '')
                successful = body.get('exit_code') == 0 and isinstance(result_text, str) and bool(result_text.strip()) and not body.get('error')
                outcome = 'cancelled' if run['desired'] == 'cancelled' else ('succeeded' if successful else 'failed')
                if successful and not run['result_event']:
                    path = self.home / 'runs' / run['id'] / 'result.txt'
                    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    path.write_text(result_text)
                    artifact = store.cmd_artifact(actor, {'path': str(path)})
                    store.cmd_report(actor, {'run_id': run['id'], 'type': 'result', 'text': result_text, 'artifact_ids': [artifact['artifact_id']]})
                store.update('runs', run['id'], released=1, health='exited', observed='exited', outcome=outcome, heartbeat=now())
                store.update('sessions', actor['id'], state='idle')
                store.db.execute("UPDATE resources SET state=CASE WHEN kind='worktree' THEN 'idle' ELSE 'released' END,owner_run=NULL WHERE owner_run=?", (run['id'],))
                task = store.get('tasks', run['task_id'])
                if (not successful or outcome=='cancelled') and task['state'] not in ('accepted', 'cancelled'):
                    store.update('tasks', task['id'], state='cancelled' if outcome == 'cancelled' else 'failed')
                if outcome == 'cancelled':
                    store.update('runs', run['id'], confirmed_generation=run['control_generation'])
                holds = [h for h in json.loads(task['holds']) if h != f'control:{run["id"]}']
                store.update('tasks', task['id'], holds=dump(holds))
        elif kind == 'uncertain':
            store.update('runs', run['id'], health='unresponsive', observed='unknown', outcome='uncertain')
            store.db.execute("UPDATE resources SET state='quarantined' WHERE owner_run=? AND state='held'", (run['id'],))
        else:
            raise Invalid(f'Unknown runner observation: {kind}')
        event = store.event(actor, 'runner_' + kind, body, task_id=run['task_id'], run_id=run['id'], revision=run['revision'])
        if kind=='uncertain' or kind=='finished' and (body.get('uncertain') or body.get('error') or body.get('exit_code')!=0):
            store.notify(actor,event)
        return {'ok': True, 'event_id': event}

    def external_command(self, request):
        store = self.store
        actor = store.authenticate(request['token'])
        payload = dump({'kind': request['kind'], 'body': request.get('body', {}), 'epoch': request.get('epoch')})
        with store.transaction():
            previous = store.one('SELECT * FROM command_requests WHERE id=?', (request['request_id'],))
            if previous:
                require(previous['session_id'] == actor['id'] and previous['payload'] == payload, 'Request ID reused with different content')
                return json.loads(previous['response'])
            team=store.coordinator(actor, request.get('epoch'))
            require(team['state']=='active','Team is not active')
            body = request.get('body', {})
            if request['kind'] == 'reconcile':
                result = self.reconcile(actor, body)
            else:
                intent = dict(body, epoch=request['epoch'])
                if request['kind'] == 'worktree':
                    for key in ('repo', 'path', 'branch', 'ref'):
                        require(isinstance(body.get(key), str) and body[key], f'Missing worktree {key}')
                    intent['path'] = str(Path(body['path']).expanduser().resolve())
                    require(not Path(intent['path']).exists(), 'Worktree destination already exists; reconcile it explicitly')
                else:
                    action = body.get('action')
                    require(action in ('cherry_pick', 'create', 'submit', 'ci'), 'Unknown integration action')
                    task = store.owned(actor, 'tasks', body['task_id'])
                    spec = json.loads(task['spec'])
                    require(spec.get('integration') is True, 'A named integration task is required')
                    require(task['state'] not in ('accepted','cancelled'),'Integration task is already terminal')
                    resource = store.one("SELECT * FROM resources WHERE team_id=? AND kind='worktree' AND identity=? AND state='idle'", (actor['team_id'], spec['cwd']))
                    require(resource, 'Integration requires idle isolated worktree')
                    require(not store.one("SELECT id FROM operations WHERE team_id=? AND kind='integration' AND state IN ('pending','running','uncertain') AND json_extract(intent,'$.task_id')=?", (actor['team_id'], task['id'])), 'Integration task has an unresolved operation')
                    intent['repo'] = spec['cwd']
                    if action == 'cherry_pick':
                        source_runs = body.get('source_runs', [])
                        require(source_runs and len(source_runs) == len(body.get('commits', [])), 'Each commit requires an accepted source run')
                        for rid, commit in zip(source_runs, body['commits']):
                            run = store.owned(actor, 'runs', rid)
                            source = store.get('tasks', run['task_id'])
                            require(source['accepted_event'] and json.loads(store.get('events', source['accepted_event'])['body'])['run_id'] == rid, 'Integrate only accepted source runs')
                            review = json.loads(store.get('events', source['accepted_event'])['body'])
                            require(commit in review.get('reviewed_commits',[]), 'Commit was not part of the accepted source review')
                    if action == 'submit':
                        require(body.get('authorized') is True, 'PR publication requires explicit authorization in this command')
                oid = store.operation(actor['team_id'], None, request['kind'], intent)
                if request['kind']=='integration':
                    detail=json.loads(resource['detail'])
                    detail['owner_operation']=oid
                    store.update('resources',resource['id'],state='held',detail=dump(detail))
                eid = store.event(actor, 'operation_requested', {'operation_id': oid, 'kind': request['kind'], 'intent': intent})
                result = {'operation_id': oid, 'event_id': eid}
            store.insert('command_requests', id=request['request_id'], session_id=actor['id'], payload=payload, response=dump(result), created=now())
            return result

    def reconcile(self, actor, body):
        store = self.store
        require(isinstance(body.get('reason'), str) and body['reason'], 'Reconciliation evidence/reason required')
        if body.get('run_id'):
            run = store.owned(actor, 'runs', body['run_id'])
            require(not run['released'], 'Already released')
            require(run['runner_pid'] is None or not ProcessIdentity.matches(run['runner_pid'], run['runner_identity']), 'Runner still alive; control it before releasing')
            for resource in store.all("SELECT * FROM resources WHERE owner_run=? AND kind='process'", (run['id'],)):
                detail = json.loads(resource['detail'])
                require(not ProcessIdentity.matches(detail['pid'], detail['start_identity']) or ProcessIdentity.state(detail['pid'], detail['start_identity']) == 'Z', 'Provider/tool still alive')
            journal_path = self.home / 'runs' / run['id'] / 'journal.json'
            if journal_path.exists():
                journal = json.loads(journal_path.read_text())
                identities = list(journal.get('children', []))
                if journal.get('provider_identity'):
                    identities.append(journal['provider_identity'])
                for detail in identities:
                    require(ProcessIdentity.state(detail['pid'], detail['start_identity']) in ('exited','replaced','Z'), 'Observed tool still alive; cannot release write ownership')
            require(body.get('external_effects_checked') is True, 'Inspect unknown external actions before releasing')
            store.update('runs', run['id'], released=1, health='exited', observed='exited', outcome='cancelled' if run['desired']=='cancelled' else 'failed')
            store.update('sessions', run['session_id'], state='idle')
            task = store.get('tasks', run['task_id'])
            holds = [h for h in json.loads(task['holds']) if h != f'control:{run["id"]}']
            store.update('tasks', task['id'], state='awaiting_review' if run['result_event'] else 'queued', holds=dump(holds))
            store.db.execute("UPDATE resources SET state=CASE WHEN kind='worktree' THEN 'idle' ELSE 'released' END,owner_run=NULL WHERE owner_run=?", (run['id'],))
            store.db.execute("UPDATE operations SET state='failed',outcome=?,updated=? WHERE run_id=? AND state IN ('pending','running','uncertain')", (dump(body), now(), run['id']))
        elif body.get('operation_id'):
            operation = store.owned(actor, 'operations', body['operation_id'])
            require(operation['state'] == 'uncertain', 'Only uncertain operations require explicit reconciliation')
            require(body.get('outcome') in ('succeeded', 'failed') and body.get('external_effects_checked') is True, 'Observed external outcome required')
            if operation['kind']=='worktree' and body['outcome']=='succeeded':
                intent = json.loads(operation['intent'])
                path = Path(intent['path']).resolve(strict=True)
                metadata = subprocess.run(['git','worktree','list','--porcelain'],cwd=intent['repo'],capture_output=True,text=True,check=True,timeout=10).stdout
                require('worktree '+str(path)+'\n' in metadata, 'Worktree is not registered in the expected repository')
                branch = subprocess.run(['git','branch','--show-current'],cwd=path,capture_output=True,text=True,check=True,timeout=10).stdout.strip()
                require(branch==intent['branch'], 'Recovered worktree branch mismatch')
                if not store.one("SELECT id FROM resources WHERE kind='worktree' AND identity=?",(str(path),)):
                    store.insert('resources',id=uid('resource'),team_id=actor['team_id'],kind='worktree',identity=str(path),detail=dump(dict(intent,reconciled=True)),state='idle')
            store.update('operations', operation['id'], state=body['outcome'], outcome=dump(body), updated=now())
            self.release_operation_resource(operation['id'], uncertain=False)
        else:
            raise Invalid('run_id or operation_id required')
        return {'event_id': store.event(actor, 'reconciled', body)}

    def prepare_pane(self, team, worker, run):
        config = json.loads(team['config'])
        if not config.get('tmux_socket') or not config.get('tmux_window'):
            return True
        manager = TmuxManager(config['tmux_socket'], config['tmux_window'], team['id'], max_panes=config.get('max_panes', 4))
        display = str(Path(__file__).with_name('display.py'))
        status = manager.ensure_pane('runtime', [sys.executable, display, '--home', str(self.home), '--team', team['id']], purpose='status')
        if status is None:
            return False
        pane = manager.ensure_pane(worker['id'], [sys.executable, display, '--home', str(self.home), '--team', team['id'], '--agent', worker['id']])
        if pane is None:
            return False
        with self.store.transaction():
            status_key = config['tmux_socket'] + ':' + status['pane']
            if not self.store.one("SELECT id FROM resources WHERE kind='pane' AND identity=?", (status_key,)):
                self.store.insert('resources', id=uid('resource'), team_id=team['id'], kind='pane', identity=status_key, detail=dump(status), state='idle')
            key = config['tmux_socket'] + ':' + pane['pane']
            resource = self.store.one("SELECT * FROM resources WHERE kind='pane' AND identity=?", (key,))
            if resource:
                self.store.update('resources', resource['id'], detail=dump(pane), owner_run=run['id'], state='held')
            else:
                self.store.insert('resources', id=uid('resource'), team_id=team['id'], kind='pane', identity=key, detail=dump(pane), owner_run=run['id'], state='held')
        return True

    def launch(self, operation):
        store = self.store
        run = store.get('runs', operation['run_id'])
        team = store.get('teams', operation['team_id'])
        task = store.get('tasks', run['task_id'])
        control = store.one("SELECT * FROM events WHERE run_id=? AND type='control_requested' ORDER BY sequence DESC LIMIT 1", (run['id'],))
        if control and json.loads(control['body'])['epoch']==team['epoch'] and run['desired'] in ('cancelled','paused'):
            with store.transaction():
                store.update('runs',run['id'],observed=run['desired'],confirmed_generation=run['control_generation'])
                if run['desired']=='cancelled':
                    store.update('runs',run['id'],released=1,health='exited',observed='exited',outcome='cancelled')
                    store.update('sessions',run['session_id'],state='idle')
                    store.update('tasks',task['id'],state='cancelled',holds=dump([h for h in json.loads(task['holds']) if h!=f'control:{run["id"]}']))
                    store.db.execute("UPDATE resources SET state='idle',owner_run=NULL WHERE owner_run=? AND kind='worktree'",(run['id'],))
                    store.update('operations',operation['id'],state='succeeded',outcome=dump({'cancelled_before_launch':True}),updated=now())
                    self.internal_event(team['id'],'cancelled_before_launch',{'generation':run['control_generation']},run['id'])
            return
        if json.loads(task['holds']) or team['state'] != 'active':
            return
        if json.loads(operation['intent'])['epoch'] != team['epoch'] or run['revision'] != team['revision']:
            with store.transaction():
                store.update('operations', operation['id'], state='uncertain', outcome=dump({'reason':'coordinator changed before launch'}), updated=now())
                store.update('runs', run['id'], health='unresponsive', observed='unknown', outcome='uncertain')
            return
        session = store.get('sessions', run['session_id'])
        worker = store.get('agents', session['agent_id'])
        if not self.prepare_pane(team, worker, run):
            return  # Reserved work queues without exceeding the visible pane limit.
        token_path = self.home / 'credentials' / (session['id'] + '.json')
        require(token_path.exists(), 'Worker credential missing; recreate or reconcile worker')
        directory = self.home / 'runs' / run['id']
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with store.transaction():
            store.update('operations', operation['id'], state='running', updated=now())
            self.internal_event(team['id'], 'launch_intent', {'operation_id': operation['id']}, run['id'])
        env = dict(os.environ)
        env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get('PYTHONPATH', '')
        with (directory / 'runner.log').open('ab') as log:
            child = subprocess.Popen([sys.executable, '-m', 'orchestrator.runner', '--home', str(self.home), '--run', run['id'], '--token-file', str(token_path)], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, env=env)
        self.children[run['id']] = child
        identity = ProcessIdentity.read(child.pid)
        if identity:
            with store.transaction():
                store.update('runs', run['id'], runner_pid=child.pid, runner_identity=identity['start_identity'], heartbeat=now())

    def execute_external(self, operation):
        store = self.store
        intent = json.loads(operation['intent'])
        team = store.get('teams', operation['team_id'])
        with store.transaction():
            if team['epoch'] != intent['epoch']:
                store.update('operations', operation['id'], state='uncertain', outcome=dump({'reason':'stale ownership epoch'}), updated=now())
                self.release_operation_resource(operation['id'], uncertain=True)
                return
            store.update('operations', operation['id'], state='running', updated=now())
        self.external_jobs[operation['id']] = self.executor.submit(self.perform_external, operation['kind'], intent)

    @staticmethod
    def perform_external(kind, intent):
        if kind == 'worktree':
            return WorktreeManager.create(intent['repo'], intent['path'], intent['branch'], intent['ref'])
        action, repo = intent['action'], intent['repo']
        if action == 'cherry_pick':
            return {'head': IntegrationManager.cherry_pick(repo, intent['commits'])}
        if action == 'create':
            return {'output': IntegrationManager.create(repo, intent['branch'], intent['message'], trunk=intent.get('trunk'), parent=intent.get('parent'))}
        if action == 'submit':
            return {'output': IntegrationManager.submit(repo)}
        return verify_stack_ci(repo, intent['pr'], intent['expected_head'])

    def complete_external(self):
        store = self.store
        for oid, future in list(self.external_jobs.items()):
            if not future.done():
                continue
            del self.external_jobs[oid]
            operation = store.get('operations', oid)
            intent = json.loads(operation['intent'])
            try:
                result = future.result()
                with store.transaction():
                    if operation['kind'] == 'worktree':
                        store.insert('resources', id=uid('resource'), team_id=operation['team_id'], kind='worktree', identity=intent['path'], detail=dump(result), state='idle')
                    store.update('operations', oid, state='succeeded', outcome=dump(result), updated=now())
                    self.release_operation_resource(oid, uncertain=False)
                    self.internal_event(operation['team_id'], 'operation_observed', {'operation_id': oid, 'outcome': result})
            except Exception as error:
                with store.transaction():
                    store.update('operations', oid, state='uncertain', outcome=dump({'error':str(error)}), updated=now())
                    self.release_operation_resource(oid, uncertain=True)
                    self.internal_event(operation['team_id'], 'operation_uncertain', {'operation_id': oid, 'error':str(error)})

    def release_operation_resource(self, operation_id, uncertain):
        for resource in self.store.all("SELECT * FROM resources WHERE json_extract(detail,'$.owner_operation')=?",(operation_id,)):
            detail=json.loads(resource['detail'])
            if not uncertain:
                detail.pop('owner_operation',None)
            self.store.update('resources',resource['id'],state='quarantined' if uncertain else 'idle',detail=dump(detail))

    def validate_integration_review(self, request):
        store = self.store
        actor = store.authenticate(request['token'])
        store.coordinator(actor, request.get('epoch'))
        run = store.owned(actor,'runs',request['body']['run_id'])
        task = store.get('tasks',run['task_id'])
        spec=json.loads(task['spec'])
        if not spec.get('integration'):
            return
        operations=store.all("SELECT * FROM operations WHERE team_id=? AND kind='integration' AND json_extract(intent,'$.task_id')=? ORDER BY created",(actor['team_id'],task['id']))
        require(not any(o['state'] in ('pending','running','uncertain') for o in operations),'Integration operations remain unresolved')
        submitted=[o for o in operations if json.loads(o['intent'])['action']=='submit']
        if not submitted:
            return  # Local-only integration has no remote publication authorization.
        checks=[o for o in operations if json.loads(o['intent'])['action']=='ci' and o['state']=='succeeded']
        require(checks and checks[-1]['created']>=submitted[-1]['created'],'Verify current PR stack after submission')
        latest=checks[-1]
        require(json.loads(latest['outcome']).get('passed') is True,'Required stack CI has not passed')
        head=subprocess.run(['git','rev-parse','HEAD'],cwd=spec['cwd'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
        require(head==json.loads(latest['intent'])['expected_head'],'Local integration head changed since CI verification')

    def tick(self):
        store = self.store
        self.complete_external()
        for rid, child in list(self.children.items()):
            if child.poll() is not None:
                del self.children[rid]
        for operation in store.all("SELECT * FROM operations WHERE state='pending' ORDER BY created"):
            try:
                if operation['kind'] == 'launch':
                    self.launch(operation)
                elif operation['kind'] in ('worktree', 'integration'):
                    self.execute_external(operation)
            except Exception as error:
                with store.transaction():
                    store.update('operations', operation['id'], state='uncertain', outcome=dump({'error':str(error)}), updated=now())
                    self.internal_event(operation['team_id'],'launch_uncertain',{'operation_id':operation['id'],'error':str(error)},operation['run_id'])
        for run in store.all('SELECT * FROM runs WHERE released=0'):
            if store.one("SELECT id FROM operations WHERE run_id=? AND kind='launch' AND state='pending'", (run['id'],)):
                continue
            if now()-run['heartbeat'] < 5000:
                continue
            identity = ProcessIdentity.read(run['runner_pid']) if run['runner_pid'] else None
            alive = bool(identity and identity['start_identity'] == run['runner_identity'] and identity['state'] != 'Z')
            if not alive or now()-run['heartbeat'] > 30_000:
                if run['outcome'] != 'uncertain':
                    with store.transaction():
                        store.update('runs', run['id'], health='unresponsive', observed='unknown', outcome='uncertain')
                        store.db.execute("UPDATE resources SET state='quarantined' WHERE owner_run=? AND state='held'", (run['id'],))
                        store.db.execute("UPDATE operations SET state='uncertain',updated=? WHERE run_id=? AND state='running'", (now(),run['id']))
                        task = store.get('tasks', run['task_id'])
                        self.internal_event(task['team_id'], 'runner_missing', {'run_id':run['id'], 'runner_alive':alive}, run['id'])
        self.schedule_wakes()

    def schedule_wakes(self):
        store = self.store
        for did, (child, logfile, started) in list(self.wakes.items()):
            status = child.poll()
            if status is None and time.monotonic()-started < 15:
                continue
            if status is None:
                child.kill()
                child.wait()
            logfile.close()
            del self.wakes[did]
            with store.transaction():
                delivery = store.get('deliveries', did)
                if not delivery['acknowledged_at']:
                    store.update('deliveries', did, state='delivered' if status == 0 else 'uncertain', delivered_at=now() if status==0 else delivery['delivered_at'], last_error=None if status==0 else 'Wake submission uncertain; inspect exact coordinator session')
        candidates = store.all("SELECT d.*,s.external_id,e.team_id,e.priority FROM deliveries d JOIN events e ON e.id=d.event_id JOIN agents a ON a.id=d.recipient JOIN teams t ON t.id=e.team_id JOIN sessions s ON s.id=t.coordinator_session WHERE a.role='coordinator' AND d.state='pending' AND d.retry_at<=? AND s.external_id IS NOT NULL ORDER BY CASE e.priority WHEN 'urgent' THEN 0 ELSE 1 END,e.sequence", (now(),))
        for delivery in candidates:
            if delivery['id'] in self.wakes:
                continue
            command = build_wake_command(delivery['external_id'], f"Orchestration {delivery['priority']} event {delivery['event_id']}. Read codex-orch inbox at {self.home}; acknowledge delivery {delivery['id']} after processing. Receipt is not resolution.")
            with store.transaction():
                store.update('deliveries', delivery['id'], state='sending', attempts=delivery['attempts']+1)
                self.internal_event(delivery['team_id'], 'delivery_attempt', {'delivery_id':delivery['id'], 'target_thread':delivery['external_id']})
            log = (self.home / 'wake.log').open('ab')
            try:
                child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
                self.wakes[delivery['id']] = (child, log, time.monotonic())
            except OSError as error:
                log.close()
                with store.transaction():
                    store.update('deliveries', delivery['id'], state='uncertain', last_error=str(error))

    def recover(self):
        # Surviving runners reconnect; started effects are never blindly replayed.
        with self.store.transaction():
            self.store.db.execute("UPDATE deliveries SET state='uncertain',last_error='runtime restarted during send' WHERE state='sending' AND acknowledged_at IS NULL")
            self.store.db.execute("UPDATE operations SET state='uncertain',outcome=?,updated=? WHERE state='running' AND kind<>'launch'", (dump({'reason':'runtime restarted during external effect'}), now()))
            for operation in self.store.all("SELECT id FROM operations WHERE state='uncertain' AND kind='integration'"):
                self.release_operation_resource(operation['id'], uncertain=True)
        self.tick()


def serve(home):
    home = Path(home).expanduser().resolve()
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(home, 0o700)
    lock = (home / 'runtime.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Runtime already running for this home')
    runtime = Runtime(home)
    path = home / 'runtime.sock'
    path.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        os.chmod(path, 0o600)
        server.listen(32)
        server.settimeout(0.2)
        signal.signal(signal.SIGTERM, lambda *_: setattr(runtime, 'stopping', True))
        signal.signal(signal.SIGINT, lambda *_: setattr(runtime, 'stopping', True))
        runtime.recover()
        print(f'Runtime ready: {path}', flush=True)
        try:
            while not runtime.stopping:
                try:
                    connection, _ = server.accept()
                except TimeoutError:
                    connection = None
                if connection:
                    with connection:
                        connection.settimeout(2)
                        try:
                            with connection.makefile('rb') as stream:
                                line = stream.readline(MAX_MESSAGE+1)
                            require(line.endswith(b'\n') and len(line)<=MAX_MESSAGE, 'Incomplete or oversized request')
                            result = runtime.handle(json.loads(line))
                            response = {'ok':True, 'result':result}
                        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
                            response = {'ok':False, 'error':str(error)}
                        try:
                            connection.sendall(dump(response).encode()+b'\n')
                        except OSError:
                            pass  # Receipt can be retrieved with the same request ID.
                if time.monotonic()-runtime.last_tick >= 0.2:
                    try:
                        runtime.tick()
                    except Exception as error:
                        print(f'Scheduler error: {error}', file=sys.stderr, flush=True)
                    runtime.last_tick = time.monotonic()
        finally:
            path.unlink(missing_ok=True)
            runtime.executor.shutdown(wait=False, cancel_futures=True)
            runtime.store.db.close()
            lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', default=str(Path.home()/'.codex'/'orchestration'))
    serve(parser.parse_args().home)


if __name__ == '__main__':
    main()
