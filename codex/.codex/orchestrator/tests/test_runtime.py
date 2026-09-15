"""Independent daemon regression tests; no real provider or external effects."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from orchestrator.daemon import Runtime
from orchestrator.store import Invalid, dump, now


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = Runtime(self.temp.name)
        self.addCleanup(self.close_runtime)
        self.coordinator = self.runtime.store.bootstrap('Runtime contract')
        self.worker = self.command('register', {'name': 'W1', 'adapter': 'fake'})

    @property
    def store(self):
        return self.runtime.store

    def command(self, kind, body, actor=None, request_id=None):
        actor = actor or self.coordinator
        return self.runtime.handle({'op': 'command', 'token': actor['token'],
                                    'request_id': request_id or str(uuid.uuid4()),
                                    'epoch': actor.get('epoch', 1), 'kind': kind, 'body': body})

    def assign(self, worker=None):
        task = self.command('task', {'spec': {'objective': 'Bounded task', 'expected_output': 'Evidence',
                                             'cwd': self.temp.name}})['task_id']
        return self.command('assign', {'task_id': task, 'session_id': (worker or self.worker)['session_id']})

    def observe(self, run, kind, body, actor=None, observation_id=None):
        return self.runtime.handle({'op': 'runner_observe', 'token': (actor or self.worker)['token'],
                                    'run_id': run['run_id'], 'kind': kind, 'body': body,
                                    'observation_id': observation_id or str(uuid.uuid4())})

    def reopen(self):
        self.close_runtime()
        self.runtime = Runtime(self.temp.name)

    def close_runtime(self):
        if hasattr(self.runtime, 'executor'):
            self.runtime.executor.shutdown(wait=True)
        self.runtime.store.db.close()

    def test_cancel_before_launch_releases_without_starting_provider(self):
        run=self.assign()
        self.command('control',{'run_id':run['run_id'],'action':'cancel'})
        with patch('orchestrator.daemon.subprocess.Popen') as popen:
            self.runtime.tick()
            popen.assert_not_called()
        row=self.store.get('runs',run['run_id'])
        self.assertEqual((row['released'],row['outcome'],row['confirmed_generation']),(1,'cancelled',1))

    def test_missing_runner_notifies_without_impersonating_coordinator(self):
        run=self.assign()
        with self.store.transaction():
            self.store.update('operations',run['operation_id'],state='running')
            self.store.update('runs',run['run_id'],heartbeat=now()-10_000)
        self.runtime.tick()
        event=self.store.one("SELECT * FROM events WHERE type='runner_missing'")
        self.assertEqual(event['source'],'runtime')
        self.assertIsNone(event['sender_session'])
        inbox=self.store.read(self.coordinator['token'],'inbox')
        self.assertTrue(any(d['event_id']==event['id'] for d in inbox))

    def test_committed_observation_replay_after_response_loss_is_identical(self):
        run = self.assign()
        body = {'exit_code': 0, 'result': 'Completed evidence', 'error': None}
        first = self.observe(run, 'finished', body, observation_id='finished-once')
        before = len(self.store.all('SELECT * FROM events'))
        self.reopen()
        self.assertEqual(self.observe(run, 'finished', body, observation_id='finished-once'), first)
        self.assertEqual(len(self.store.all('SELECT * FROM events')), before)
        self.assertEqual(len(self.store.all('SELECT * FROM artifacts')), 1)
        with self.assertRaises(Invalid):
            self.observe(run, 'finished', dict(body, result='Different result'), observation_id='finished-once')

    def test_bootstrap_response_loss_does_not_create_duplicate_team(self):
        request = {'op': 'init', 'objective': 'New team once', 'request_id': 'init-once'}
        receipt = self.runtime.handle(request)
        count = len(self.store.all('SELECT * FROM teams'))
        self.reopen()
        self.assertEqual(self.runtime.handle(request), receipt)
        self.assertEqual(len(self.store.all('SELECT * FROM teams')), count)
        with self.assertRaises(Invalid):
            self.runtime.handle(dict(request, objective='Changed objective'))

    def test_runner_cannot_observe_another_workers_run(self):
        run = self.assign()
        other = self.command('register', {'name': 'W2', 'adapter': 'fake'})
        with self.assertRaises(Invalid):
            self.observe(run, 'finished', {'exit_code': 0, 'result': 'spoof'}, other)
        self.assertEqual(self.store.get('runs', run['run_id'])['released'], 0)

    def test_takeover_prevents_pending_launch_and_assignment_acceptance(self):
        run = self.assign()
        self.coordinator = self.command('takeover', {})
        with patch('orchestrator.daemon.subprocess.Popen') as popen:
            self.runtime.tick()
        popen.assert_not_called()
        self.assertEqual(self.store.get('operations', run['operation_id'])['state'], 'uncertain')
        with self.assertRaises(Invalid):
            self.observe(run, 'accepted', {'delivery_id': run['delivery_id']})

    def test_takeover_cannot_relabel_old_control_confirmation_with_new_epoch(self):
        run = self.assign()
        control = self.command('control', {'run_id': run['run_id'], 'action': 'pause'})
        self.coordinator = self.command('takeover', {})
        with self.assertRaises(Invalid):
            self.observe(run, 'control', {'epoch': self.coordinator['epoch'],
                                         'generation': control['generation'],
                                         'outcome': 'confirmed', 'observed': 'paused'})

    def test_new_control_after_takeover_can_be_confirmed(self):
        run = self.assign()
        self.coordinator = self.command('takeover', {})
        control = self.command('control', {'run_id': run['run_id'], 'action': 'pause'})
        self.observe(run, 'control', {'epoch': self.coordinator['epoch'], 'generation': control['generation'],
                                     'outcome': 'confirmed', 'observed': 'paused'})
        row = self.store.get('runs', run['run_id'])
        self.assertEqual(row['confirmed_generation'], control['generation'])

    def test_crash_after_launch_intent_does_not_launch_second_runner(self):
        run = self.assign()
        with self.store.transaction():
            self.store.update('operations', run['operation_id'], state='running')
            self.store.update('runs', run['run_id'], heartbeat=now() - 6000)
        self.reopen()
        with patch('orchestrator.daemon.subprocess.Popen') as popen:
            self.runtime.recover()
        popen.assert_not_called()
        self.assertEqual(self.store.get('operations', run['operation_id'])['state'], 'uncertain')
        self.assertEqual(self.store.get('runs', run['run_id'])['released'], 0)

    def test_restart_preserves_uncertain_send_without_blind_retry(self):
        run = self.assign()
        with self.store.transaction():
            self.store.update('operations', run['operation_id'], state='succeeded')
        report = self.command('report', {'run_id': run['run_id'], 'type': 'question', 'text': 'Need decision'}, self.worker)
        delivery = self.store.one('SELECT * FROM deliveries WHERE event_id=?', (report['event_id'],))
        with self.store.transaction():
            self.store.update('deliveries', delivery['id'], state='sending', attempts=1)
        self.reopen()
        with patch('orchestrator.daemon.subprocess.Popen') as popen:
            self.runtime.recover()
        popen.assert_not_called()
        recovered = self.store.get('deliveries', delivery['id'])
        self.assertEqual((recovered['state'], recovered['attempts']), ('uncertain', 1))

    def test_process_resources_distinguish_pids_with_same_start_tick(self):
        first = self.assign()
        other = self.command('register', {'name': 'W2', 'adapter': 'fake'})
        second = self.assign(other)
        for run, worker, pid in [(first, self.worker, 12001), (second, other, 12002)]:
            identity = {'pid': pid, 'start_identity': 'linux:boot:12345', 'state': 'R'}
            with patch('orchestrator.daemon.ProcessIdentity.read', return_value=identity):
                self.observe(run, 'started', identity, worker)
        resources = self.store.all("SELECT * FROM resources WHERE kind='process'")
        self.assertEqual(len(resources), 2)
        self.assertEqual({row['owner_run'] for row in resources}, {first['run_id'], second['run_id']})

    def test_worker_cannot_claim_process_already_owned_by_another_run(self):
        first = self.assign()
        other = self.command('register', {'name': 'W2', 'adapter': 'fake'})
        second = self.assign(other)
        identity = {'pid': 12001, 'start_identity': 'linux:boot:12345', 'state': 'R'}
        with patch('orchestrator.daemon.ProcessIdentity.read', return_value=identity):
            self.observe(first, 'started', identity)
            with self.assertRaises(Invalid):
                self.observe(second, 'started', identity, other)

    def test_live_provider_prevents_finished_release(self):
        run = self.assign()
        identity = {'pid': 12001, 'start_identity': 'birth', 'state': 'R'}
        with patch('orchestrator.daemon.ProcessIdentity.read', return_value=identity):
            self.observe(run, 'started', identity)
        with patch('orchestrator.daemon.ProcessIdentity.state', return_value='R'):
            with self.assertRaises(Invalid):
                self.observe(run, 'finished', {'exit_code': 0, 'result': 'Not really ended'})
        self.assertEqual(self.store.get('runs', run['run_id'])['released'], 0)

    def test_started_cannot_replace_established_provider_session_identity(self):
        run = self.assign()
        established = str(uuid.uuid4())
        self.observe(run, 'session', {'external_id': established})
        identity = {'pid': 12001, 'start_identity': 'birth', 'state': 'R'}
        with patch('orchestrator.daemon.ProcessIdentity.read', return_value=identity):
            with self.assertRaises(Invalid):
                self.observe(run, 'started', dict(identity, external_id=str(uuid.uuid4())))
        self.assertEqual(self.store.get('sessions', self.worker['session_id'])['external_id'], established)

    def test_reconciliation_requires_effect_check_and_no_live_owned_process(self):
        run = self.assign()
        with self.store.transaction():
            self.store.update('runs', run['run_id'], runner_pid=12000, runner_identity='birth')
        body = {'run_id': run['run_id'], 'reason': 'Inspect original process and side effects'}
        with patch('orchestrator.daemon.ProcessIdentity.matches', return_value=False):
            with self.assertRaises(Invalid):
                self.command('reconcile', body)
        with patch('orchestrator.daemon.ProcessIdentity.matches', return_value=True):
            with self.assertRaises(Invalid):
                self.command('reconcile', dict(body, external_effects_checked=True))
        self.assertEqual(self.store.get('runs', run['run_id'])['released'], 0)

    def test_uncertain_finished_quarantines_worktree_and_does_not_release(self):
        run = self.assign()
        with self.store.transaction():
            self.store.insert('resources', id='tree', team_id=self.coordinator['team_id'], kind='worktree',
                              identity=str(Path(self.temp.name) / 'tree'), detail='{}',
                              owner_run=run['run_id'], state='held')
        self.observe(run, 'finished', {'exit_code': 0, 'result': 'May have live tool', 'uncertain': True})
        self.assertEqual(self.store.get('runs', run['run_id'])['released'], 0)
        self.assertEqual(self.store.get('resources', 'tree')['state'], 'quarantined')

    def test_reconcile_refuses_live_orphan_child_recorded_in_runner_journal(self):
        run = self.assign()
        path = Path(self.temp.name) / 'runs' / run['run_id'] / 'journal.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'phase': 'uncertain', 'children': [
            {'pid': 12345, 'start_identity': 'orphan-birth', 'state': 'R'}]}))
        with patch('orchestrator.daemon.ProcessIdentity.state', return_value='R'):
            with self.assertRaises(Invalid):
                self.command('reconcile', {'run_id': run['run_id'], 'reason': 'Provider root exited',
                                           'external_effects_checked': True})
        self.assertEqual(self.store.get('runs', run['run_id'])['released'], 0)

    def test_reconcile_operation_success_restores_worktree_resource(self):
        path = str((Path(self.temp.name) / 'recovered-tree').resolve())
        Path(path).mkdir()
        intent = {'repo': self.temp.name, 'path': path, 'branch': 'test', 'ref': 'HEAD', 'epoch': 1}
        with self.store.transaction():
            operation = self.store.operation(self.coordinator['team_id'], None, 'worktree', intent)
            self.store.update('operations', operation, state='uncertain')
        def inspect(command, **kwargs):
            if command == ['git', 'worktree', 'list', '--porcelain']:
                self.assertEqual(kwargs['cwd'], self.temp.name)
                return SimpleNamespace(stdout=f'worktree {path}\nHEAD abc123\nbranch refs/heads/test\n')
            self.assertEqual(command, ['git', 'branch', '--show-current'])
            self.assertEqual(str(kwargs['cwd']), path)
            return SimpleNamespace(stdout='test\n')

        with patch('orchestrator.daemon.subprocess.run', side_effect=inspect):
            self.command('reconcile', {'operation_id': operation, 'outcome': 'succeeded',
                                       'external_effects_checked': True, 'reason': 'Checked existing checkout'})
        resource = self.store.one("SELECT * FROM resources WHERE kind='worktree' AND identity=?", (path,))
        self.assertIsNotNone(resource, 'Successful worktree reconciliation must restore its durable resource')

    def test_new_session_does_not_receive_old_publication_on_runner_poll(self):
        original = self.assign()
        proposal = self.command('report', {'run_id': original['run_id'], 'type': 'proposal', 'text': 'Old contract'}, self.worker)
        publication = self.command('publish', {'proposal_event': proposal['event_id'], 'recipients': [self.worker['agent_id']]})
        self.observe(original, 'finished', {'exit_code': 1, 'error': 'ended'})
        fresh = self.command('session', {'agent_id': self.worker['agent_id']})
        current = self.assign(fresh)
        state = self.runtime.handle({'op': 'runner_poll', 'token': fresh['token'], 'run_id': current['run_id']})
        self.assertNotIn(publication['deliveries'][0], [row['id'] for row in state['messages']])

    def test_released_run_cannot_consume_new_publication_in_reused_session(self):
        original = self.assign()
        self.observe(original, 'finished', {'exit_code': 1, 'error': 'Prior task ended'})
        current = self.assign()
        proposal = self.command('report', {'run_id': current['run_id'], 'type': 'proposal', 'text': 'Current contract'}, self.worker)
        publication = self.command('publish', {'proposal_event': proposal['event_id'], 'recipients': [self.worker['agent_id']]})
        with self.assertRaises(Invalid):
            self.runtime.handle({'op': 'runner_poll', 'token': self.worker['token'], 'run_id': original['run_id']})
        with self.assertRaises(Invalid):
            self.observe(original, 'message_ack', {'delivery_id': publication['deliveries'][0]})
        self.assertIsNone(self.store.get('deliveries', publication['deliveries'][0])['acknowledged_at'])

    def integration_task(self):
        path = (Path(self.temp.name) / 'integration-tree').resolve()
        path.mkdir(exist_ok=True)
        task = self.command('task', {'spec': {'objective': 'Integrate accepted work', 'expected_output': 'CI evidence',
                                             'cwd': str(path), 'integration': True, 'write': True}})['task_id']
        with self.store.transaction():
            self.store.insert('resources', id='integration-tree', team_id=self.coordinator['team_id'],
                              kind='worktree', identity=str(path), detail='{}', state='idle')
        return task, str(path)

    def test_integration_rejects_commit_not_in_accepted_review(self):
        source = self.assign()
        self.observe(source, 'finished', {'exit_code': 0, 'result': 'Reviewed implementation evidence'})
        with self.store.transaction():
            self.store.update('operations', source['operation_id'], state='succeeded')
        self.command('review', {'run_id': source['run_id'], 'decision': 'accept', 'reason': 'Inspected changes',
                                'reviewed_commits': ['a' * 40]})
        integration, _ = self.integration_task()
        body = {'task_id': integration, 'action': 'cherry_pick', 'source_runs': [source['run_id']]}
        for commit in ('b' * 40, 'aaaaaaa', 'HEAD'):
            with self.subTest(commit=commit), self.assertRaises(Invalid):
                self.command('integration', dict(body, commits=[commit]))
        accepted = self.command('integration', dict(body, commits=['a' * 40]))
        self.assertTrue(accepted['operation_id'])

    def test_pending_integration_reserves_worktree_against_worker_assignment(self):
        integration, path = self.integration_task()
        operation = self.command('integration', {'task_id': integration, 'action': 'create',
                                                 'branch': 'review-stack', 'message': 'Accepted change'})
        writer = self.command('task', {'spec': {'objective': 'Concurrent writer', 'expected_output': 'Patch',
                                               'cwd': path, 'write': True}})['task_id']
        with self.assertRaises(Invalid):
            self.command('assign', {'task_id': writer, 'session_id': self.worker['session_id']})
        self.assertEqual(self.store.get('operations', operation['operation_id'])['state'], 'pending')

    def test_uncertain_integration_keeps_checkout_reserved_until_reconciliation(self):
        integration, _ = self.integration_task()
        operation = self.command('integration', {'task_id': integration, 'action': 'create',
                                                 'branch': 'review-stack', 'message': 'Accepted change'})
        with self.store.transaction():
            self.store.update('operations', operation['operation_id'], state='running')
        self.reopen()
        with patch('orchestrator.daemon.subprocess.Popen') as popen:
            self.runtime.recover()
        popen.assert_not_called()
        self.assertEqual(self.store.get('resources', 'integration-tree')['state'], 'quarantined')
        self.assertEqual(self.store.get('operations', operation['operation_id'])['state'], 'uncertain')
        self.command('reconcile', {'operation_id': operation['operation_id'], 'outcome': 'failed',
                                   'external_effects_checked': True, 'reason': 'Inspected and restored checkout'})
        self.assertEqual(self.store.get('resources', 'integration-tree')['state'], 'idle')


if __name__ == '__main__':
    unittest.main()
