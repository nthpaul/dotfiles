"""Transactional command handling; called only by the single local daemon.

Events carry versioned snapshots. Mutable rows are projections, not evidence.
Local session tokens bind callers; this is not isolation from other same-user code.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class Invalid(ValueError):
    pass


def uid(prefix):
    return f'{prefix}-{uuid.uuid4().hex}'


def now():
    return time.time_ns() // 1_000_000


def dump(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def hashed(value):
    return hashlib.sha256(value.encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise Invalid(message)


class Store:
    def __init__(self, home):
        self.home = Path(home).expanduser().resolve()
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.home, 0o700)
        self.db = sqlite3.connect(self.home / 'state.sqlite3', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=5000')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        require(version in (0, 1), f'Unsupported database version {version}')
        self.db.executescript(Path(__file__).with_name('schema.sql').read_text())
        self.db.execute('PRAGMA recursive_triggers=ON')

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def one(self, sql, params=()):
        row = self.db.execute(sql, params).fetchone()
        return dict(row) if row else None

    def all(self, sql, params=()):
        return [dict(r) for r in self.db.execute(sql, params)]

    def insert(self, table, **values):
        keys = ','.join(values)
        self.db.execute(f'INSERT INTO {table} ({keys}) VALUES ({",".join("?" for _ in values)})', tuple(values.values()))

    def update(self, table, row_id, **values):
        self.db.execute(f'UPDATE {table} SET {",".join(k+"=?" for k in values)} WHERE id=?', (*values.values(), row_id))

    def get(self, table, row_id):
        row = self.one(f'SELECT * FROM {table} WHERE id=?', (row_id,))
        require(row is not None, f'Unknown {table}: {row_id}')
        return row

    def team(self, actor):
        return self.get('teams', actor['team_id'])

    def authenticate(self, token):
        require(isinstance(token, str) and bool(token), 'Session token required')
        actor = self.one('SELECT s.*, a.team_id,a.role,a.retired FROM sessions s JOIN agents a ON a.id=s.agent_id WHERE token_hash=?', (hashed(token),))
        require(actor and not actor['retired'] and actor['state'] != 'superseded', 'Invalid or retired session')
        return actor

    def owned(self, actor, table, row_id):
        row = self.get(table, row_id)
        if table == 'runs':
            task = self.get('tasks', row['task_id'])
            require(task['team_id'] == actor['team_id'], 'Cross-team run')
            if actor['role'] == 'worker':
                require(row['session_id'] == actor['id'], 'Run belongs to another session')
        else:
            require(row['team_id'] == actor['team_id'], 'Cross-team reference')
        return row

    def coordinator(self, actor, epoch):
        team = self.team(actor)
        require(actor['role'] == 'coordinator', 'Coordinator command required')
        require(team['coordinator_session'] == actor['id'] and team['epoch'] == epoch, 'Stale coordinator ownership epoch')
        return team

    def event(self, actor, kind, body, task_id=None, run_id=None, revision=None, priority='normal', reply_to=None, event_id=None, source='session'):
        require(priority in ('normal', 'urgent'), 'Invalid priority')
        if task_id:
            self.owned(actor, 'tasks', task_id)
        if run_id:
            self.owned(actor, 'runs', run_id)
        if reply_to:
            self.owned(actor, 'events', reply_to)
        team = self.team(actor)
        sequence = self.db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE team_id=?', (team['id'],)).fetchone()[0]
        eid = event_id or uid('evt')
        self.insert('events', id=eid, team_id=team['id'], sequence=sequence, type=kind, sender_session=actor['id'] if source=='session' else None, source=source, task_id=task_id,
                    run_id=run_id, revision=revision if revision is not None else team['revision'], priority=priority, body=dump(body), reply_to=reply_to, created=now())
        return eid

    def deliver(self, event_id, agent_id, target_session=None):
        event = self.get('events', event_id)
        agent = self.get('agents', agent_id)
        require(agent['team_id'] == event['team_id'] and not agent['retired'], 'Invalid delivery recipient')
        if event['source']=='runtime':
            require(agent['role']=='coordinator','Runtime observations go to the coordinator')
        else:
            sender = self.get('sessions', event['sender_session'])
            sender_agent = self.get('agents', sender['agent_id'])
            require(agent['role'] == 'coordinator' or sender_agent['role'] == 'coordinator', 'Workers may report only to coordinator')
        did = uid('delivery')
        self.insert('deliveries', id=did, event_id=event_id, recipient=agent_id, target_session=target_session)
        return did

    def notify(self, actor, event_id):
        owner = self.get('sessions', self.team(actor)['coordinator_session'])
        return self.deliver(event_id, owner['agent_id'], owner['id'])

    def bootstrap(self, objective, config=None, team_id=None, request_id=None):
        require(isinstance(objective, str) and objective.strip(), 'Objective required')
        initial_payload = dump({'kind':'init','objective':objective,'config':config or {},'team_id':team_id})
        team_id = uid('team') if team_id is None else team_id
        require(isinstance(team_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', team_id), 'Invalid team ID')
        sid, aid, token = uid('session'), uid('agent'), secrets.token_urlsafe(32)
        config = {} if config is None else config
        require(isinstance(config, dict), 'Team config must be an object')
        with self.transaction():
            if request_id:
                previous = self.one('SELECT * FROM command_requests WHERE id=?', (request_id,))
                if previous:
                    require(previous['payload'] == initial_payload, 'Init request ID reused with different content')
                    return json.loads(previous['response'])
            self.insert('teams', id=team_id, objective=objective, coordinator_session=sid, config=dump(config))
            self.insert('agents', id=aid, team_id=team_id, role='coordinator', name='Coordinator', config=dump({'adapter': 'codex', 'model': 'gpt-6-astra', 'effort': 'medium'}))
            self.insert('sessions', id=sid, agent_id=aid, token_hash=hashed(token), external_id=config.get('coordinator_thread'), config='{}', heartbeat=now())
            actor = self.authenticate(token)
            event = self.event(actor, 'team_created', {'objective': objective, 'config': config, 'epoch': 1})
            response = {'team_id': team_id, 'session_id': sid, 'token': token, 'epoch': 1, 'event_id': event}
            if request_id:
                self.insert('command_requests', id=request_id, session_id=sid, payload=initial_payload, response=dump(response), created=now())
        return response

    def command(self, token, request_id, epoch, kind, body):
        require(isinstance(request_id, str) and 0 < len(request_id) <= 200, 'Request ID required (max 200 characters)')
        require(isinstance(body, dict), 'Command body must be an object')
        payload = dump({'kind': kind, 'body': body, 'epoch': epoch})
        with self.transaction():
            actor = self.authenticate(token)
            previous = self.one('SELECT * FROM command_requests WHERE id=?', (request_id,))
            if previous:
                require(previous['session_id'] == actor['id'] and previous['payload'] == payload, 'Request ID reused with different actor or content')
                return json.loads(previous['response'])
            worker_commands = {'report', 'ack', 'heartbeat', 'artifact'}
            if kind not in worker_commands:
                self.coordinator(actor, epoch)
            elif actor['role'] == 'coordinator':
                self.coordinator(actor, epoch)
            if kind not in ('artifact','heartbeat','ack','report','takeover'):
                require(self.team(actor)['state']=='active','Team is not active')
            handler = getattr(self, f'cmd_{kind}', None)
            require(handler is not None, f'Unknown command: {kind}')
            response = handler(actor, body)
            self.insert('command_requests', id=request_id, session_id=actor['id'], payload=payload, response=dump(response), created=now())
            return response

    def cmd_register(self, actor, body):
        adapter = body.get('adapter', 'codex')
        require(adapter in ('codex', 'grok', 'fake'), 'Unknown adapter')
        name = body.get('name')
        require(isinstance(name, str) and name.strip(), 'Worker name required')
        config = {'adapter': adapter, 'model': body.get('model', 'gpt-6-astra' if adapter == 'codex' else ('grok-4.6' if adapter == 'grok' else '')), 'effort': body.get('effort', 'medium')}
        require(isinstance(config['model'], str) and isinstance(config['effort'], str), 'Model and effort must be strings')
        aid, sid, token = uid('agent'), uid('session'), secrets.token_urlsafe(32)
        self.insert('agents', id=aid, team_id=actor['team_id'], role='worker', name=name, config=dump(config))
        self.insert('sessions', id=sid, agent_id=aid, token_hash=hashed(token), config=dump(config), heartbeat=now())
        eid = self.event(actor, 'worker_registered', {'agent_id': aid, 'session_id': sid, 'config': config})
        return {'agent_id': aid, 'session_id': sid, 'token': token, 'event_id': eid}

    def cmd_session(self, actor, body):
        worker = self.owned(actor, 'agents', body['agent_id'])
        require(worker['role'] == 'worker' and not worker['retired'], 'Active worker required')
        require(not self.one('SELECT r.id FROM runs r JOIN sessions s ON s.id=r.session_id WHERE s.agent_id=? AND r.released=0', (worker['id'],)), 'Worker already allocated')
        fresh = body.get('fresh', True)
        require(isinstance(fresh, bool), 'fresh must be boolean')
        if not fresh:
            session = self.get('sessions', body['session_id'])
            require(session['agent_id'] == worker['id'] and session['state'] != 'superseded', 'Invalid related-work session')
            return {'agent_id': worker['id'], 'session_id': session['id'], 'reused': True}
        sid, token = uid('session'), secrets.token_urlsafe(32)
        self.db.execute("UPDATE sessions SET state='superseded' WHERE agent_id=?", (worker['id'],))
        self.insert('sessions', id=sid, agent_id=worker['id'], token_hash=hashed(token), config=worker['config'], heartbeat=now())
        eid = self.event(actor, 'worker_session_created', {'agent_id': worker['id'], 'session_id': sid, 'config': json.loads(worker['config'])})
        return {'agent_id': worker['id'], 'session_id': sid, 'token': token, 'event_id': eid}

    def cmd_retry(self, actor, body):
        task = self.owned(actor, 'tasks', body['task_id'])
        require(task['state'] in ('failed', 'cancelled', 'blocked'), 'Only failed, cancelled or blocked tasks may retry')
        require(isinstance(body.get('reason'), str) and body['reason'].strip(), 'Retry reason required')
        require(not self.one('SELECT id FROM runs WHERE task_id=? AND released=0', (task['id'],)), 'Reconcile execution before retry')
        require(self.one('SELECT id FROM runs WHERE task_id=? AND released=1', (task['id'],)), 'Retry requires a released prior attempt')
        require(not self.one("SELECT id FROM operations WHERE run_id IN (SELECT id FROM runs WHERE task_id=?) AND state IN ('pending','running','uncertain')", (task['id'],)), 'Reconcile previous effects before retry')
        self.update('tasks', task['id'], state='queued', accepted_event=None)
        return {'event_id': self.event(actor, 'task_retry_requested', body, task_id=task['id']), 'state': 'queued'}

    def validate_spec(self, actor, spec, task_id=None, graph_override=None):
        require(isinstance(spec, dict), 'Task spec must be an object')
        for name in ('objective', 'expected_output'):
            require(isinstance(spec.get(name), str) and spec[name].strip(), f'Spec requires {name}')
        spec = dict(spec)
        spec.setdefault('context', '')
        spec.setdefault('dependencies', [])
        spec.setdefault('criteria', [])
        spec.setdefault('write', False)
        require(isinstance(spec['write'], bool), 'write must be boolean')
        require(isinstance(spec['criteria'], list) and all(isinstance(c, str) and c.strip() for c in spec['criteria']), 'criteria must contain nonempty strings')
        require(isinstance(spec['context'], str), 'context must be a string')
        require(len(spec['criteria']) == len(set(spec['criteria'])), 'Duplicate criterion')
        require(isinstance(spec['dependencies'], list) and all(isinstance(d, str) for d in spec['dependencies']), 'dependencies must be task IDs')
        require(len(set(spec['dependencies'])) == len(spec['dependencies']), 'Duplicate dependency')
        require(isinstance(spec.get('cwd', '.'), str) and bool(spec.get('cwd', '.')), 'cwd must be a nonempty string')
        spec['cwd'] = str(Path(spec.get('cwd', '.')).expanduser().resolve())
        require(Path(spec['cwd']).is_dir(), 'Task cwd must exist')
        graph = dict(graph_override) if graph_override is not None else {t['id']: json.loads(t['spec'])['dependencies'] for t in self.all('SELECT * FROM tasks WHERE team_id=?', (actor['team_id'],))}
        for dependency in spec['dependencies']:
            self.owned(actor, 'tasks', dependency)
        if task_id:
            graph[task_id] = spec['dependencies']
        def visit(node, path):
            require(node not in path, 'Dependency cycle')
            for child in graph.get(node, []):
                visit(child, path | {node})
        for node in graph:
            visit(node, set())
        return spec

    def cmd_task(self, actor, body):
        tid = body.get('task_id', uid('task'))
        require(isinstance(tid, str) and tid, 'Invalid task ID')
        spec = self.validate_spec(actor, body.get('spec'), tid)
        self.insert('tasks', id=tid, team_id=actor['team_id'], revision=self.team(actor)['revision'], spec=dump(spec))
        eid = self.event(actor, 'task_created', {'spec': spec}, task_id=tid)
        return {'task_id': tid, 'event_id': eid}

    def cmd_replan(self, actor, body):
        team = self.team(actor)
        require(isinstance(body.get('reason'), str) and body['reason'].strip(), 'Replan reason required')
        require(isinstance(body.get('tasks', {}), dict), 'tasks must map task IDs to complete specs')
        revision = team['revision'] + 1
        # Validate against the whole proposed graph, including simultaneous edge changes.
        changes = body.get('tasks', {})
        graph = {t['id']: json.loads(t['spec'])['dependencies'] for t in self.all('SELECT * FROM tasks WHERE team_id=?', (team['id'],))}
        for tid, spec in changes.items():
            require(isinstance(spec, dict), 'Task spec must be an object')
            graph[tid] = spec.get('dependencies', [])
        for tid, spec in changes.items():
            task = self.owned(actor, 'tasks', tid)
            require(task['state'] not in ('accepted', 'cancelled'), 'Create a follow-up task for accepted/cancelled work')
            self.validate_spec(actor, spec, tid, graph)
            self.update('tasks', tid, spec=dump(self.validate_spec(actor, spec, tid, graph)), revision=revision, version=task['version']+1)
        self.update('teams', team['id'], revision=revision)
        snapshot = {t['id']: json.loads(t['spec']) for t in self.all('SELECT * FROM tasks WHERE team_id=?', (team['id'],))}
        eid = self.event(actor, 'plan_revised', {'reason': body['reason'], 'tasks': snapshot, 'previous_revision': team['revision']})
        return {'revision': revision, 'event_id': eid}

    def cmd_hold(self, actor, body):
        task = self.owned(actor, 'tasks', body['task_id'])
        require(isinstance(body.get('reason'), str) and body['reason'], 'Hold reason required')
        holds = json.loads(task['holds'])
        if body.get('clear', False):
            require(body['reason'] in holds, 'Unknown hold')
            holds.remove(body['reason'])
        elif body['reason'] not in holds:
            holds.append(body['reason'])
        self.update('tasks', task['id'], holds=dump(holds))
        return {'event_id': self.event(actor, 'dispatch_hold', body, task_id=task['id']), 'holds': holds}

    def cmd_assign(self, actor, body):
        team = self.team(actor)
        require(team['state'] == 'active', 'Team is not active')
        task = self.owned(actor, 'tasks', body['task_id'])
        require(task['state'] in ('queued', 'blocked', 'failed'), 'Task not assignable; request revision after a result')
        require(not json.loads(task['holds']), 'Task dispatch held')
        require(not self.one("SELECT id FROM issues WHERE team_id=? AND state='open' AND blocks_acceptance=1 AND (task_id=? OR task_id IS NULL)", (team['id'], task['id'])), 'Resolve blocking issues before dispatch')
        session = self.get('sessions', body['session_id'])
        require(session['state'] != 'superseded', 'Session has been superseded')
        worker = self.get('agents', session['agent_id'])
        require(worker['team_id'] == team['id'] and worker['role'] == 'worker' and not worker['retired'], 'Invalid worker')
        require(not self.one('SELECT r.id FROM runs r JOIN sessions s ON s.id=r.session_id WHERE s.agent_id=? AND r.released=0', (worker['id'],)), 'Worker already allocated')
        require(self.db.execute('SELECT count(*) FROM runs r JOIN tasks t ON t.id=r.task_id WHERE t.team_id=? AND r.released=0', (team['id'],)).fetchone()[0] < team['max_workers'], 'All worker slots occupied')
        spec = json.loads(task['spec'])
        for dependency in spec['dependencies']:
            dep = self.owned(actor, 'tasks', dependency)
            require(dep['state'] == 'accepted', 'Dependency not accepted')
            review = self.get('events', dep['accepted_event'])
            if review['revision'] != team['revision']:
                assessment = self.one("SELECT * FROM events WHERE task_id=? AND type='compatibility' AND revision=? ORDER BY sequence DESC LIMIT 1", (dependency, team['revision']))
                require(assessment and json.loads(assessment['body']).get('compatible') is True, 'Dependency requires current-plan compatibility assessment')
        rid = uid('run')
        eid = uid('evt')
        self.insert('runs', id=rid, task_id=task['id'], session_id=session['id'], assignment_event=eid, revision=team['revision'], heartbeat=now())
        self.event(actor, 'assignment', {'spec': spec, 'session_id': session['id'], 'epoch': team['epoch'], 'run_id': rid}, task_id=task['id'], run_id=rid, event_id=eid)
        if spec['write']:
            resource = self.one("SELECT * FROM resources WHERE kind='worktree' AND identity=? AND team_id=?", (spec['cwd'], team['id']))
            require(resource and resource['state'] == 'idle', 'Writing requires an idle registered isolated worktree')
            self.update('resources', resource['id'], owner_run=rid, state='held')
        self.update('tasks', task['id'], state='running')
        self.update('sessions', session['id'], state='busy')
        did = self.deliver(eid, worker['id'], session['id'])
        operation = self.operation(team['id'], rid, 'launch', {'epoch': team['epoch'], 'session_id': session['id'], 'delivery_id': did})
        return {'run_id': rid, 'event_id': eid, 'delivery_id': did, 'operation_id': operation}

    def operation(self, team_id, run_id, kind, intent):
        oid = uid('op')
        self.insert('operations', id=oid, team_id=team_id, run_id=run_id, kind=kind, intent=dump(intent), created=now(), updated=now())
        return oid

    def cmd_control(self, actor, body):
        run = self.owned(actor, 'runs', body['run_id'])
        require(not run['released'], 'Run already released')
        action = body.get('action')
        require(action in ('pause', 'resume', 'cancel'), 'Unknown control')
        desired = {'pause': 'paused', 'resume': 'running', 'cancel': 'cancelled'}[action]
        require(run['desired'] != 'cancelled' or action == 'cancel', 'Cancellation cannot be reversed')
        generation = run['control_generation']+1
        task = self.get('tasks', run['task_id'])
        holds = json.loads(task['holds'])
        hold = f'control:{run["id"]}'
        if action in ('pause', 'cancel') and hold not in holds:
            holds.append(hold)
        if action == 'resume':
            assigned=json.loads(self.get('events',run['assignment_event'])['body'])['spec']
            require(json.loads(task['spec'])==assigned, 'Assignment changed while executing: cancel, wait for release, retry, then assign revised work in the same session')
            holds = [h for h in holds if h != hold]
        self.update('tasks', task['id'], holds=dump(holds))
        self.update('runs', run['id'], desired=desired, control_generation=generation)
        eid = self.event(actor, 'control_requested', {'action': action, 'generation': generation, 'epoch': self.team(actor)['epoch']}, task_id=task['id'], run_id=run['id'])
        return {'event_id': eid, 'generation': generation, 'desired': desired}

    def cmd_ack(self, actor, body):
        delivery = self.get('deliveries', body['delivery_id'])
        require(delivery['recipient'] == actor['agent_id'] and delivery['target_session'] in (None, actor['id']), 'Delivery belongs to another recipient/session')
        require(delivery['state'] != 'cancelled', 'Delivery cancelled')
        if delivery['acknowledged_at']:
            return {'acknowledged': True, 'event_id': delivery['event_id']}
        self.update('deliveries', delivery['id'], state='acknowledged', acknowledged_at=now(), delivered_at=delivery['delivered_at'] or now())
        eid = self.event(actor, 'acknowledged', {'delivery_id': delivery['id']}, reply_to=delivery['event_id'])
        return {'event_id': eid, 'acknowledged': True}

    def cmd_retry_delivery(self, actor, body):
        delivery=self.get('deliveries',body['delivery_id'])
        event=self.owned(actor,'events',delivery['event_id'])
        require(delivery['state'] in ('pending','delivered','uncertain'),'Delivery cannot be retried')
        require(not delivery['acknowledged_at'],'Acknowledged delivery cannot be retried')
        require(body.get('reason') and body.get('not_accepted_confirmed') is True,'Inspect recipient acceptance before retrying an uncertain send')
        self.update('deliveries',delivery['id'],state='pending',retry_at=0,last_error=None)
        return {'event_id':self.event(actor,'delivery_retry_authorized',body,reply_to=event['id']),'delivery_id':delivery['id']}

    def cmd_heartbeat(self, actor, body):
        self.update('sessions', actor['id'], heartbeat=now())
        if body.get('run_id'):
            run = self.owned(actor, 'runs', body['run_id'])
            require(not run['released'], 'Released run')
            self.update('runs', run['id'], heartbeat=now())
        return {'ok': True}

    def cmd_artifact(self, actor, body):
        # Finalize a content-addressed copy before committing any reference.
        source = Path(body['path']).expanduser().resolve(strict=True)
        require(source.is_file(), 'Artifact must be a file')
        content = source.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        directory = self.home / 'artifacts' / actor['team_id']
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = directory / digest
        if not target.exists():
            temporary = directory / uid('.tmp')
            with temporary.open('xb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        require(target.is_file() and target.stat().st_size == len(content) and hashlib.sha256(target.read_bytes()).hexdigest() == digest, 'Artifact corrupt')
        existing = self.one('SELECT * FROM artifacts WHERE path=?', (str(target),))
        if existing:
            return {'artifact_id': existing['id'], 'sha256': digest}
        aid = uid('artifact')
        self.insert('artifacts', id=aid, team_id=actor['team_id'], path=str(target), sha256=digest, size=len(content), created=now())
        eid = self.event(actor, 'artifact_finalized', {'artifact_id': aid, 'sha256': digest, 'size': len(content)})
        return {'artifact_id': aid, 'sha256': digest, 'event_id': eid}

    def verify_artifacts(self, actor, ids):
        require(isinstance(ids, list) and all(isinstance(a, str) for a in ids), 'artifact_ids must be a list')
        for aid in ids:
            artifact = self.owned(actor, 'artifacts', aid)
            path = Path(artifact['path'])
            require(path.is_file() and path.stat().st_size == artifact['size'] and hashlib.sha256(path.read_bytes()).hexdigest() == artifact['sha256'], 'Missing or corrupt artifact')

    def cmd_report(self, actor, body):
        require(actor['role'] == 'worker', 'Reports come from workers')
        run = self.owned(actor, 'runs', body['run_id'])
        kind = body.get('type', 'progress')
        require(kind in ('progress', 'result', 'question', 'conflict', 'proposal'), 'Invalid report type')
        require(isinstance(body.get('text'), str), 'Report text required')
        self.verify_artifacts(actor, body.get('artifact_ids', []))
        if kind == 'result':
            require(run['result_event'] is None, 'Run already has a result')
        priority = body.get('priority', 'urgent' if kind == 'conflict' else 'normal')
        if kind in ('question', 'conflict'):
            require(isinstance(body.get('blocks_acceptance', True), bool), 'blocks_acceptance must be boolean')
            key = body.get('coalescing_key', run['task_id'] + ':' + body['text'])
            require(isinstance(key, str) and bool(key), 'Issue coalescing key required')
            previous = self.one("SELECT * FROM issues WHERE team_id=? AND task_id=? AND coalescing_key=? AND state='open'", (actor['team_id'], run['task_id'], key))
        else:
            previous = None
        eid = self.event(actor, kind, body, task_id=run['task_id'], run_id=run['id'], revision=run['revision'], priority=priority, reply_to=previous['event_id'] if previous else None)
        if kind == 'result':
            self.update('runs', run['id'], result_event=eid)
            task = self.get('tasks', run['task_id'])
            if task['state'] not in ('accepted', 'cancelled') and not self.one('SELECT id FROM runs WHERE task_id=? AND released=0 AND id<>?', (task['id'], run['id'])):
                self.update('tasks', task['id'], state='awaiting_review')
        if kind in ('question', 'conflict'):
            if not previous:
                iid = uid('issue')
                self.insert('issues', id=iid, team_id=actor['team_id'], task_id=run['task_id'], coalescing_key=key, event_id=eid, priority=priority, blocks_acceptance=int(body.get('blocks_acceptance', True)))
            else:
                iid = previous['id']
                if priority == 'urgent':
                    self.update('issues', iid, priority='urgent')
                if body.get('blocks_acceptance', True):
                    self.update('issues', iid, blocks_acceptance=1)
            task = self.get('tasks', run['task_id'])
            if task['state'] not in ('accepted', 'cancelled'):
                self.update('tasks', task['id'], state='blocked')
            if not previous:
                self.notify(actor, eid)
            return {'event_id': eid, 'issue_id': iid}
        if kind != 'progress':
            self.notify(actor, eid)
        return {'event_id': eid}

    def cmd_resolve(self, actor, body):
        issue = self.owned(actor, 'issues', body['issue_id'])
        require(issue['state'] == 'open', 'Issue already resolved')
        require(isinstance(body.get('resolution'), str) and body['resolution'].strip(), 'Resolution required')
        eid = self.event(actor, 'issue_resolved', body, task_id=issue['task_id'], reply_to=issue['event_id'])
        self.update('issues', issue['id'], state='resolved', resolution_event=eid)
        return {'event_id': eid}

    def cmd_publish(self, actor, body):
        source = self.owned(actor, 'events', body['proposal_event'])
        require(source['type'] in ('proposal', 'conflict', 'question'), 'Publication must reference a source report')
        original = json.loads(source['body'])
        self.verify_artifacts(actor, original.get('artifact_ids', []))
        recipients = body.get('recipients', [])
        require(isinstance(recipients, list) and all(isinstance(r, str) for r in recipients) and len(set(recipients)) == len(recipients), 'Recipients must be unique agent IDs')
        eid = self.event(actor, 'publication', {'source_event': source['id'], 'text': body.get('text', original['text']), 'artifact_ids': original.get('artifact_ids', []), 'recipients': recipients}, reply_to=source['id'])
        deliveries = []
        for recipient in recipients:
            agent = self.owned(actor, 'agents', recipient)
            if agent['role'] == 'coordinator':
                target = self.team(actor)['coordinator_session']
            else:
                session = self.one("SELECT id FROM sessions WHERE agent_id=? AND state<>'superseded' ORDER BY rowid DESC LIMIT 1", (recipient,))
                require(session, 'Recipient has no active session')
                target = session['id']
            deliveries.append(self.deliver(eid, recipient, target))
        return {'event_id': eid, 'deliveries': deliveries}

    def cmd_compatibility(self, actor, body):
        task = self.owned(actor, 'tasks', body['task_id'])
        require(task['accepted_event'], 'Compatibility assessment requires accepted task')
        require(isinstance(body.get('compatible'), bool) and body.get('reason'), 'Compatibility and reason required')
        return {'event_id': self.event(actor, 'compatibility', body, task_id=task['id'], reply_to=task['accepted_event'])}

    def cmd_review(self, actor, body):
        run = self.owned(actor, 'runs', body['run_id'])
        task = self.get('tasks', run['task_id'])
        require(run['result_event'], 'No worker result')
        require(run['released'], 'Confirm execution has ended before review')
        require(task['state'] not in ('accepted', 'cancelled'), 'Task already terminal')
        require(not self.one('SELECT id FROM runs WHERE task_id=? AND released=0', (task['id'],)), 'Task still executing')
        decision = body.get('decision')
        require(decision in ('accept', 'revise', 'reject'), 'Unknown review decision')
        require(isinstance(body.get('reason'), str) and body['reason'].strip(), 'Review reason required')
        if decision == 'accept':
            reviewed_commits = body.get('reviewed_commits', [])
            require(isinstance(reviewed_commits, list) and all(isinstance(commit, str) and re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', commit) for commit in reviewed_commits), 'reviewed_commits must contain full lowercase commit OIDs')
            require(len(reviewed_commits) == len(set(reviewed_commits)), 'Duplicate reviewed commit OID')
            require(not self.one("SELECT id FROM issues WHERE team_id=? AND state='open' AND blocks_acceptance=1 AND (task_id=? OR task_id IS NULL)", (actor['team_id'], task['id'])), 'Unresolved acceptance blocker')
            result = self.get('events', run['result_event'])
            artifacts = json.loads(result['body']).get('artifact_ids', [])
            require(artifacts, 'Acceptance requires finalized result evidence')
            self.verify_artifacts(actor, artifacts)
            if run['revision'] != self.team(actor)['revision']:
                require(body.get('compatible') is True and body.get('compatibility_reason'), 'Old-plan result requires explicit dependency/compatibility assessment')
            checks = body.get('checks', [])
            require(isinstance(checks, list), 'Checks must be a list')
            for criterion in json.loads(task['spec'])['criteria']:
                matching = [c for c in checks if isinstance(c, dict) and c.get('criterion') == criterion]
                require(len(matching) == 1 and matching[0].get('passed') is True and matching[0].get('artifact_ids'), f'Missing passing evidence for: {criterion}')
                self.verify_artifacts(actor, matching[0]['artifact_ids'])
        eid = self.event(actor, 'review', body, task_id=task['id'], run_id=run['id'], reply_to=run['result_event'])
        self.update('tasks', task['id'], state={'accept': 'accepted', 'revise': 'queued', 'reject': 'failed'}[decision], accepted_event=eid if decision == 'accept' else None)
        return {'event_id': eid, 'state': self.get('tasks', task['id'])['state']}

    def cmd_takeover(self, actor, body):
        # Current credential authorizes handoff, but gets a new session/token/epoch.
        team = self.team(actor)
        sid, token = uid('session'), secrets.token_urlsafe(32)
        self.insert('sessions', id=sid, agent_id=actor['agent_id'], token_hash=hashed(token), external_id=body.get('external_id'), config=actor['config'], heartbeat=now())
        self.update('teams', team['id'], coordinator_session=sid, epoch=team['epoch']+1)
        eid = self.event(actor, 'ownership_acquired', {'session_id': sid, 'epoch': team['epoch']+1})
        self.db.execute("UPDATE deliveries SET target_session=?, state=CASE WHEN acknowledged_at IS NOT NULL THEN 'acknowledged' ELSE 'pending' END WHERE recipient=? AND state<>'cancelled'", (sid, actor['agent_id']))
        return {'event_id': eid, 'session_id': sid, 'token': token, 'epoch': team['epoch']+1, 'team_id': team['id']}

    def cmd_finish(self, actor, body):
        require(not self.one('SELECT r.id FROM runs r JOIN tasks t ON t.id=r.task_id WHERE t.team_id=? AND r.released=0', (actor['team_id'],)), 'Active runs remain')
        require(not self.one("SELECT id FROM tasks WHERE team_id=? AND state<>'accepted'", (actor['team_id'],)), 'All tasks must be accepted')
        require(not self.one("SELECT id FROM issues WHERE team_id=? AND state='open'", (actor['team_id'],)), 'Open issues remain')
        require(not self.one("SELECT id FROM operations WHERE team_id=? AND state IN ('pending','running','uncertain')", (actor['team_id'],)), 'Unreconciled operations remain')
        self.update('teams', actor['team_id'], state='completed')
        return {'event_id': self.event(actor, 'team_completed', body)}

    def read(self, token, view, filters=None):
        actor = self.authenticate(token)
        filters = filters or {}
        if view == 'status':
            team = self.team(actor)
            return {'team': team, 'agents': self.all('SELECT id,role,name,retired FROM agents WHERE team_id=?', (team['id'],)),
                    'sessions': self.all('SELECT s.id,s.agent_id,s.external_id,s.state,s.heartbeat,s.config FROM sessions s JOIN agents a ON a.id=s.agent_id WHERE a.team_id=?', (team['id'],)),
                    'tasks': self.all('SELECT * FROM tasks WHERE team_id=?', (team['id'],)),
                    'runs': self.all('SELECT r.* FROM runs r JOIN tasks t ON t.id=r.task_id WHERE t.team_id=?', (team['id'],)),
                    'issues': self.all('SELECT * FROM issues WHERE team_id=?', (team['id'],)),
                    'operations': self.all('SELECT * FROM operations WHERE team_id=?', (team['id'],)),
                    'resources': self.all('SELECT * FROM resources WHERE team_id=?', (team['id'],))}
        if view in ('history', 'bulletin'):
            clauses, values = ['team_id=?'], [actor['team_id']]
            if view == 'bulletin':
                clauses.append("type='publication'")
            for key in ('task_id', 'run_id', 'type'):
                if key in filters:
                    clauses.append(f'{key}=?')
                    values.append(filters[key])
            clauses.append('sequence>?')
            values.append(int(filters.get('after', 0)))
            values.append(min(max(int(filters.get('limit', 100)), 1), 1000))
            return self.all('SELECT * FROM events WHERE '+ ' AND '.join(clauses)+' ORDER BY sequence LIMIT ?', values)
        if view == 'inbox':
            if actor['role'] == 'coordinator':
                require(self.team(actor)['coordinator_session'] == actor['id'], 'Stale coordinator inbox')
            rows = self.all("SELECT d.*,e.type,e.body,e.sequence,CASE WHEN EXISTS(SELECT 1 FROM issues i WHERE i.event_id=e.id AND i.state='open' AND i.priority='urgent') THEN 'urgent' ELSE e.priority END AS priority,e.run_id,e.task_id FROM deliveries d JOIN events e ON e.id=d.event_id WHERE d.recipient=? AND (d.target_session IS NULL OR d.target_session=?) AND d.state<>'cancelled' AND (d.acknowledged_at IS NULL OR EXISTS(SELECT 1 FROM issues i WHERE i.event_id=e.id AND i.state='open')) ORDER BY CASE WHEN e.priority='urgent' OR EXISTS(SELECT 1 FROM issues i WHERE i.event_id=e.id AND i.state='open' AND i.priority='urgent') THEN 0 ELSE 1 END,e.sequence", (actor['agent_id'], actor['id']))
            if filters.get('priority'):
                rows = [r for r in rows if r['priority'] == filters['priority']]
            return rows
        raise Invalid(f'Unknown view: {view}')
