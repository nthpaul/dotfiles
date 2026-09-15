"""Board snapshot, navigation, pane honesty, and control gating. Dedicated temp homes only."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.board import Board
from orchestrator.cli import main, parser, register_body

SCHEMA = Path(__file__).resolve().parents[1] / 'orchestrator' / 'schema.sql'


def _insert(db, table, **values):
    keys = ','.join(values)
    db.execute(f'INSERT INTO {table} ({keys}) VALUES ({",".join("?" for _ in values)})', tuple(values.values()))


def seed_home(home, *, team='team-alpha', epoch=2, revision=3, suffix='a'):
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(home / 'state.sqlite3')
    db.executescript(SCHEMA.read_text())
    coordinator = f'session-coord-{suffix}'
    worker = f'agent-w-{suffix}'
    session = f'session-w-{suffix}'
    task = f'task-{suffix}'
    prior = f'run-{suffix}-1'
    current = f'run-{suffix}-2'
    assign = f'evt-assign-{suffix}'
    _insert(db, 'teams', id=team, objective=f'Objective {suffix}', revision=revision, epoch=epoch,
            coordinator_session=coordinator, state='active', max_workers=2,
            config=json.dumps({'budgets': {'model_calls': 9}}))
    _insert(db, 'agents', id=f'agent-c-{suffix}', team_id=team, role='coordinator', name='Coordinator',
            config=json.dumps({'adapter': 'codex', 'model': 'gpt-6-astra', 'effort': 'medium'}), retired=0)
    _insert(db, 'agents', id=worker, team_id=team, role='worker', name=f'worker-{suffix}',
            config=json.dumps({'adapter': 'grok', 'model': 'grok-4.6', 'effort': 'high'}), retired=0)
    _insert(db, 'sessions', id=coordinator, agent_id=f'agent-c-{suffix}', token_hash=f'c{suffix}'.ljust(64, '0'),
            external_id=None, config='{}', state='idle', heartbeat=1)
    _insert(db, 'sessions', id=session, agent_id=worker, token_hash=f'w{suffix}'.ljust(64, '0'),
            external_id='11111111-1111-4111-8111-111111111111',
            config=json.dumps({'adapter': 'grok', 'model': 'grok-4.6', 'effort': 'high'}),
            state='busy', heartbeat=1)
    spec = {'objective': f'Do {suffix}', 'dependencies': [], 'criteria': [], 'budgets': {'model_calls': 3}}
    if suffix == 'a':
        spec['dependencies'] = ['task-dep']
        _insert(db, 'tasks', id='task-dep', team_id=team, revision=revision,
                spec=json.dumps({'objective': 'dep', 'dependencies': [], 'criteria': []}),
                state='accepted', holds='[]', accepted_event=None, version=1)
    _insert(db, 'tasks', id=task, team_id=team, revision=revision, spec=json.dumps(spec),
            state='running', holds=json.dumps([f'control:{current}']), accepted_event=None, version=1)
    _insert(db, 'runs', id=prior, task_id=task, session_id=session, assignment_event=assign,
            revision=revision - 1 if revision > 1 else 1, health='exited', desired='running',
            observed='running', control_generation=0, confirmed_generation=0, outcome='succeeded',
            released=1, runner_pid=None, runner_identity=None, heartbeat=1, result_event=None)
    _insert(db, 'runs', id=current, task_id=task, session_id=session, assignment_event=assign,
            revision=revision, health='running', desired='paused', observed='running',
            control_generation=1, confirmed_generation=0, outcome=None, released=0,
            runner_pid=4242, runner_identity='birth', heartbeat=1, result_event=None)
    _insert(db, 'events', id=assign, team_id=team, sequence=1, type='assignment', sender_session=coordinator,
            source='session', task_id=task, run_id=current, revision=revision, priority='normal',
            body=json.dumps({'spec': spec, 'epoch': epoch}), reply_to=None, created=1)
    _insert(db, 'events', id=f'evt-own-{suffix}', team_id=team, sequence=2, type='ownership_acquired',
            sender_session=coordinator, source='session', task_id=None, run_id=None, revision=revision,
            priority='normal', body=json.dumps({'epoch': epoch, 'session_id': coordinator}), reply_to=None, created=2)
    _insert(db, 'events', id=f'evt-replan-{suffix}', team_id=team, sequence=3, type='replan',
            sender_session=coordinator, source='session', task_id=None, run_id=None, revision=revision,
            priority='normal', body=json.dumps({'reason': 'scope change'}), reply_to=None, created=3)
    _insert(db, 'events', id=f'evt-usage-{suffix}', team_id=team, sequence=4, type='runner_usage',
            sender_session=session, source='runtime', task_id=task, run_id=current, revision=revision,
            priority='normal', body=json.dumps({
                'as_of': 10, 'session_id': session,
                'baseline': {'input_tokens': 4, 'model_calls': 1},
                'current': {'input_tokens': 10, 'model_calls': 2, 'cached_read_tokens': 3},
                'delta': {'input_tokens': 6, 'model_calls': 1, 'cached_read_tokens': 3},
            }), reply_to=None, created=4)
    _insert(db, 'events', id=f'evt-secret-{suffix}', team_id=team, sequence=5, type='report',
            sender_session=session, source='session', task_id=task, run_id=current, revision=revision,
            priority='normal', body=json.dumps({
                'text': 'progress', 'reasoning': 'SECRET_REASONING', 'token': 'SECRET_TOKEN',
            }), reply_to=None, created=5)
    _insert(db, 'deliveries', id=f'del-{suffix}', event_id=f'evt-secret-{suffix}', recipient=f'agent-c-{suffix}',
            target_session=coordinator, state='delivered', attempts=1, delivered_at=1,
            acknowledged_at=None, retry_at=0, last_error=None)
    _insert(db, 'issues', id=f'issue-{suffix}', team_id=team, task_id=task, coalescing_key=f'budget:model_calls',
            event_id=f'evt-secret-{suffix}', priority='urgent', blocks_acceptance=1, state='open',
            resolution_event=None)
    _insert(db, 'operations', id=f'op-ci-{suffix}', team_id=team, run_id=current, kind='ci_watch',
            state='failed', intent=json.dumps({'pr': 7, 'expected_head': 'abc123'}),
            outcome=json.dumps({'passed': False, 'head': 'def456', 'expected_head': 'abc123',
                                'stack': [{'pr': 7, 'head': 'def456'}], 'reason': 'head changed'}),
            created=1, updated=2)
    _insert(db, 'resources', id=f'res-live-{suffix}', team_id=team, kind='pane',
            identity=f'/tmp/tmux.sock:%live-{suffix}',
            detail=json.dumps({'socket': '/tmp/tmux.sock', 'window': '@1', 'pane': f'%live-{suffix}',
                               'team': team, 'agent': worker, 'purpose': 'worker'}),
            owner_run=current, state='held')
    _insert(db, 'resources', id=f'res-miss-{suffix}', team_id=team, kind='pane',
            identity=f'/tmp/tmux.sock:%missing-{suffix}',
            detail=json.dumps({'socket': '/tmp/tmux.sock', 'window': '@1', 'pane': f'%missing-{suffix}',
                               'team': team, 'agent': worker, 'purpose': 'worker'}),
            owner_run=current, state='held')
    _insert(db, 'resources', id=f'res-stale-{suffix}', team_id=team, kind='pane',
            identity=f'/tmp/tmux.sock:%stale-{suffix}',
            detail=json.dumps({'socket': '/tmp/tmux.sock', 'window': '@1', 'pane': f'%stale-{suffix}',
                               'team': team, 'agent': worker, 'purpose': 'worker'}),
            owner_run=prior, state='released')
    _insert(db, 'resources', id=f'res-dead-{suffix}', team_id=team, kind='pane',
            identity=f'/tmp/tmux.sock:%dead-{suffix}',
            detail=json.dumps({'socket': '/tmp/tmux.sock', 'window': '@1', 'pane': f'%dead-{suffix}',
                               'team': team, 'agent': worker, 'purpose': 'worker'}),
            owner_run=None, state='idle')
    db.commit()
    db.close()
    (home / 'coordinator.json').write_text(json.dumps({
        'token': 'SECRET_COORD_TOKEN', 'epoch': epoch, 'session_id': coordinator, 'team_id': team,
    }))
    return {'team': team, 'task': task, 'run': current, 'worker': worker, 'epoch': epoch}


def probe(socket, window, pane, team=None, agent=None, purpose=None):
    pane = pane or ''
    if pane.startswith('%live'):
        return {'state': 'live', 'socket': socket, 'window': window, 'pane': pane}
    if pane.startswith('%missing'):
        return {'state': 'missing'}
    if pane.startswith('%stale'):
        return {'state': 'stale', 'reason': 'team tag mismatch'}
    if pane.startswith('%dead'):
        return {'state': 'dead', 'pane': pane}
    return {'state': 'unknown', 'reason': 'unprobed'}


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='orch-board-', dir='/tmp')
        self.home_a = Path(self.temporary.name) / 'a'
        self.home_b = Path(self.temporary.name) / 'b'
        self.meta_a = seed_home(self.home_a, team='team-alpha', epoch=2, revision=3, suffix='a')
        seed_home(self.home_a, team='team-beta', epoch=1, revision=1, suffix='b')
        self.meta_b = seed_home(self.home_b, team='team-gamma', epoch=1, revision=1, suffix='c')
        self.calls = []
        self.focused = []

        def control(home, credentials, kind, body):
            self.calls.append({'home': str(home), 'epoch': credentials.get('epoch'),
                               'token': credentials.get('token'), 'kind': kind, 'body': body})
            if credentials.get('epoch') != 2:
                raise RuntimeError('Stale coordinator ownership epoch')
            if kind == 'control':
                return {'desired': {'pause': 'paused', 'resume': 'running', 'cancel': 'cancelled'}[body['action']]}
            return {'holds': [body.get('reason', 'board')]}

        def tmux(socket, window, pane):
            self.focused.append((socket, window, pane))
            return True

        def credentials(home):
            from orchestrator.board_model import load_coordinator_credentials
            return load_coordinator_credentials(home)

        self.board = Board([self.home_a, self.home_b], section='tasks', control=control,
                           probe=probe, tmux=tmux, credentials_loader=credentials)

    def tearDown(self):
        self.temporary.cleanup()

    def test_navigation_filter_and_resize(self):
        wide = self.board.render(100, 30)
        self.assertIn('[tasks]', wide)
        self.assertIn('task-a', wide)
        self.assertIn('holds=', wide)
        self.board.handle('j')
        self.board.handle('tab')
        self.assertEqual(self.board.section, 'epochs')
        epochs = self.board.render(100, 30)
        self.assertIn('[epochs]', epochs)
        self.assertIn('epoch=2', epochs)
        self.board.handle('attempts')
        labels = [row['label'] for row in self.board.rows()]
        self.assertTrue(any('run-a-1' in label for label in labels))
        self.assertTrue(any('run-a-2' in label and 'REQUESTED!=OBSERVED' in label for label in labels))
        self.board.cursor = next(i for i, row in enumerate(self.board.rows()) if row['id'] == 'run-a-2')
        detail = '\n'.join(self.board.detail_lines())
        self.assertIn('input_tokens=6', detail)
        self.assertIn('REQUESTED!=OBSERVED', detail)
        self.assertNotIn('cached_read_tokens=0', detail.replace('cached_read_tokens=3', ''))
        attempts = self.board.render(100, 30)
        self.assertIn('REQUESTED!=OBSERVED', attempts)
        self.board.handle('/')
        for char in 'run-a-2':
            self.board.handle(char)
        self.board.handle('enter')
        filtered = self.board.render(40, 12)
        self.assertIn('run-a-2', filtered)
        self.assertNotIn('run-a-1', filtered)
        self.assertEqual(len(filtered.splitlines()), 12)
        for line in filtered.splitlines():
            self.assertLessEqual(len(line), 40)

    def test_multiteam_and_extra_home(self):
        self.board.handle('teams')
        text = self.board.render(120, 24)
        self.assertIn('team-alpha', text)
        self.assertIn('team-beta', text)
        self.board.handle('n')
        other = self.board.render(120, 24)
        self.assertIn('team-gamma', other)
        self.board.handle('t')
        self.board.handle('t')
        self.assertIn(self.board.team_id, ('team-alpha', 'team-beta', 'team-gamma'))

    def test_missing_stale_dead_panes_and_attach(self):
        self.board.handle('resources')
        text = self.board.render(120, 30)
        self.assertIn('pane=live', text)
        self.assertIn('pane=missing', text)
        self.assertIn('pane=stale', text)
        self.assertIn('pane=dead', text)
        rows = self.board.rows()
        live = next(i for i, row in enumerate(rows) if 'pane=live' in row['label'])
        missing = next(i for i, row in enumerate(rows) if 'pane=missing' in row['label'])
        self.board.cursor = missing
        self.board.handle('a')
        self.assertIn('not attached', self.board.message)
        self.assertEqual(self.focused, [])
        self.board.cursor = live
        self.board.handle('a')
        self.assertEqual(self.focused, [('/tmp/tmux.sock', '@1', '%live-a')])

    def test_stale_epoch_and_missing_credentials_do_not_send(self):
        self.board.handle('attempts')
        rows = self.board.rows()
        self.board.cursor = next(i for i, row in enumerate(rows) if row['id'] == 'run-a-2')
        self.board.credentials_loader = lambda home: {'token': 'SECRET_COORD_TOKEN', 'epoch': 1}
        self.board.handle('p')
        self.assertEqual(self.calls, [])
        self.assertIn('stale coordinator epoch', self.board.message)
        self.board.credentials_loader = lambda home: None
        self.board.handle('p')
        self.assertEqual(self.calls, [])
        self.assertIn('no coordinator credentials', self.board.message)
        self.board.credentials_loader = lambda home: {'token': 'SECRET_COORD_TOKEN', 'epoch': 2}
        self.board.handle('p')
        self.assertEqual(self.calls[-1]['kind'], 'control')
        self.assertEqual(self.calls[-1]['body'], {'run_id': 'run-a-2', 'action': 'pause'})
        self.assertIn('requested', self.board.message)
        self.assertIn('observed=running', self.board.message)

    def test_redacts_credentials_reasoning_and_missing_usage_keys(self):
        text = self.board.render(120, 40)
        self.assertNotIn('SECRET_COORD_TOKEN', text)
        self.assertNotIn('SECRET_REASONING', text)
        self.assertNotIn('SECRET_TOKEN', text)
        self.board.handle('inbox')
        inbox = self.board.render(120, 30)
        self.assertNotIn('SECRET_REASONING', inbox)
        self.board.handle('operations')
        ops = self.board.render(120, 30)
        self.assertIn('expected=abc123', ops)
        self.assertIn('head=def456', ops)
        self.assertIn('ci=failed', ops)
        self.board.handle('workers')
        workers = self.board.render(140, 24)
        self.assertIn('grok-4.6', workers)
        self.assertIn('effort=high', workers)
        self.assertIn('mode=omitted', workers)

    def test_cli_snapshot_and_register_defaults(self):
        args = parser().parse_args(['register', 'worker'])
        self.assertEqual(register_body(args), {
            'name': 'worker', 'adapter': 'grok', 'model': 'grok-4.6', 'effort': 'high'})
        self.assertEqual(register_body(parser().parse_args(['register', 'w', '--adapter', 'codex'])),
                         {'name': 'w', 'adapter': 'codex'})
        self.assertEqual(register_body(parser().parse_args(['register', 'w', '--adapter', 'fake'])),
                         {'name': 'w', 'adapter': 'fake'})
        exec_body = register_body(parser().parse_args(
            ['register', 'w', '--adapter', 'grok', '--mode', 'exec']))
        self.assertEqual(exec_body['mode'], 'exec')
        self.assertEqual(exec_body['effort'], 'high')
        from io import StringIO
        from unittest.mock import patch
        with patch('sys.stdout', new=StringIO()) as stdout:
            code = main(['--home', str(self.home_a), 'board', '--snapshot', '--width', '80', '--height', '20',
                         '--section', 'tasks'])
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertIn('task-a', text)
        self.assertNotIn('SECRET_COORD_TOKEN', text)


if __name__ == '__main__':
    unittest.main()
