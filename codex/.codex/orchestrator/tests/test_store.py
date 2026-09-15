"""Store contract tests; simulated observations do not prove live adapter guarantees."""
import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid
from unittest.mock import patch

from orchestrator.store import Invalid, Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.addCleanup(lambda: self.store.db.close())
        self.coordinator = self.store.bootstrap('Exercise orchestration contract')
        self.worker = self.call('register', {'name': 'W1', 'adapter': 'fake'})

    def call(self, kind, body, actor=None, request_id=None, epoch=None):
        actor = actor or self.coordinator
        return self.store.command(actor['token'], request_id or str(uuid.uuid4()),
                                  actor.get('epoch', 1) if epoch is None else epoch, kind, body)

    def spec(self, dependencies=None, criteria=None):
        return {'objective': 'bounded task', 'expected_output': 'evidence',
                'cwd': self.temp.name, 'dependencies': dependencies or [],
                'criteria': criteria or []}

    def task(self, dependencies=None, criteria=None, actor=None):
        return self.call('task', {'spec': self.spec(dependencies, criteria)}, actor)['task_id']

    def assign(self, task=None, worker=None):
        return self.call('assign', {'task_id': task or self.task(),
                                    'session_id': (worker or self.worker)['session_id']})

    def artifact(self, actor=None, content='test evidence'):
        path = Path(self.temp.name) / str(uuid.uuid4())
        path.write_text(content)
        return self.call('artifact', {'path': str(path)}, actor or self.worker)['artifact_id']

    def report(self, run, kind='result', actor=None, **extra):
        return self.call('report', {'run_id': run['run_id'], 'type': kind, 'text': kind,
                                    **extra}, actor or self.worker)

    def release(self, run):
        with self.store.transaction():
            self.store.update('runs', run['run_id'], released=1, health='exited', observed='exited')
            row = self.store.get('runs', run['run_id'])
            self.store.update('sessions', row['session_id'], state='idle')
            self.store.update('operations', run['operation_id'], state='succeeded')

    def review(self, run, decision='accept', **extra):
        return self.call('review', {'run_id': run['run_id'], 'decision': decision,
                                   'reason': 'Reviewed evidence', **extra})

    def completed_run(self, task=None, worker=None):
        run = self.assign(task, worker)
        artifact = self.artifact(worker)
        self.report(run, actor=worker, artifact_ids=[artifact])
        self.release(run)
        return run, artifact

    def counts(self):
        return {name: self.store.one(f'SELECT COUNT(*) AS n FROM {name}')['n']
                for name in ('tasks', 'runs', 'events', 'deliveries', 'command_requests', 'operations')}

    def test_changed_assignment_cannot_resume_stale_inflight_work(self):
        task=self.task()
        run=self.assign(task)
        self.call('control',{'run_id':run['run_id'],'action':'pause'})
        spec=self.spec()
        spec['objective']='Revised contract'
        self.call('replan',{'reason':'Contract changed','tasks':{task:spec}})
        with self.assertRaisesRegex(Invalid,'Assignment changed'):
            self.call('control',{'run_id':run['run_id'],'action':'resume'})
        self.assertEqual(self.store.get('runs',run['run_id'])['desired'],'paused')

    def test_delivery_retry_reuses_message_and_preserves_ack(self):
        run=self.assign()
        report=self.report(run,'question')
        delivery=self.store.one('SELECT * FROM deliveries WHERE event_id=?',(report['event_id'],))
        with self.store.transaction():
            self.store.update('deliveries',delivery['id'],state='uncertain')
        with self.assertRaises(Invalid):
            self.call('retry_delivery',{'delivery_id':delivery['id'],'reason':'timeout'})
        result=self.call('retry_delivery',{'delivery_id':delivery['id'],'reason':'Inspected recipient; no acceptance','not_accepted_confirmed':True})
        self.assertEqual(result['delivery_id'],delivery['id'])
        self.assertEqual(self.store.get('deliveries',delivery['id'])['event_id'],report['event_id'])
        self.call('ack',{'delivery_id':delivery['id']})
        with self.assertRaises(Invalid):
            self.call('retry_delivery',{'delivery_id':delivery['id'],'reason':'Again','not_accepted_confirmed':True})

    def test_authenticated_sender_and_worker_authority(self):
        run = self.assign()
        report = self.report(run, 'progress', sender_session=self.coordinator['session_id'],
                             role='coordinator', team_id='forged')
        event = self.store.get('events', report['event_id'])
        self.assertEqual(event['sender_session'], self.worker['session_id'])
        self.assertEqual(event['team_id'], self.coordinator['team_id'])
        for command, body in [('task', {'spec': self.spec()}), ('register', {'name': 'nested'}),
                              ('control', {'run_id': run['run_id'], 'action': 'pause'}),
                              ('takeover', {}), ('review', {'run_id': run['run_id']}),
                              ('publish', {'proposal_event': report['event_id']})]:
            with self.subTest(command=command), self.assertRaises(Invalid):
                self.call(command, body, self.worker)
        with self.assertRaises(Invalid):
            self.store.command('invalid', 'request', 1, 'heartbeat', {})

    def test_cross_team_and_cross_worker_references_are_rejected(self):
        other = self.store.bootstrap('Other team')
        other_task = self.task(actor=other)
        run = self.assign()
        stranger = self.call('register', {'name': 'W2'})
        for kind, body, actor in [
            ('assign', {'task_id': other_task, 'session_id': self.worker['session_id']}, None),
            ('task', {'spec': self.spec([other_task])}, None),
            ('report', {'run_id': run['run_id'], 'text': 'spoof'}, stranger),
            ('ack', {'delivery_id': run['delivery_id']}, stranger),
            ('heartbeat', {'run_id': run['run_id']}, stranger),
        ]:
            before = self.counts()
            with self.subTest(kind=kind), self.assertRaises(Invalid):
                self.call(kind, body, actor)
            self.assertEqual(self.counts(), before)
        foreign_artifact = self.artifact(other)
        with self.assertRaises(Invalid):
            self.report(run, artifact_ids=[foreign_artifact])

    def test_request_replay_survives_restart_and_rejects_changed_actor_or_payload(self):
        body = {'spec': self.spec()}
        response = self.call('task', body, request_id='fixed')
        counts = self.counts()
        self.store.db.close()
        self.store = Store(self.temp.name)
        self.assertEqual(self.call('task', body, request_id='fixed'), response)
        self.assertEqual(self.counts(), counts)
        for actor, changed in [(self.coordinator, {'spec': self.spec(criteria=['new'])}),
                               (self.worker, body)]:
            with self.assertRaises(Invalid):
                self.call('task', changed, actor, request_id='fixed')
        self.assertEqual(self.counts(), counts)

    def test_assignment_failure_rolls_back_all_records(self):
        task = self.task()
        counts = self.counts()
        with patch.object(self.store, 'operation', side_effect=RuntimeError('crash barrier')):
            with self.assertRaises(RuntimeError):
                self.assign(task)
        self.assertEqual(self.counts(), counts)
        self.assertEqual(self.store.get('tasks', task)['state'], 'queued')
        self.assertEqual(self.store.get('sessions', self.worker['session_id'])['state'], 'idle')

    def test_concurrent_connections_preserve_reports_and_request_deduplication(self):
        run = self.assign()

        def send(index):
            connection = Store(self.temp.name)
            try:
                return connection.command(self.worker['token'], f'concurrent-{index}', 1,
                                          'report', {'run_id': run['run_id'], 'text': str(index),
                                                     'type': 'progress'})
            finally:
                connection.db.close()

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(send, list(range(12)) + list(range(12))))
        self.assertEqual(results[:12], results[12:])
        reports = self.store.read(self.coordinator['token'], 'history', {'type': 'progress'})
        self.assertEqual(len(reports), 12)
        self.assertEqual(len({row['sequence'] for row in reports}), 12)
        self.assertEqual({json.loads(row['body'])['text'] for row in reports}, {str(i) for i in range(12)})

    def test_event_history_and_receipts_are_immutable(self):
        for table, row_id in [('events', self.coordinator['event_id']),
                              ('command_requests', self.store.one('SELECT id FROM command_requests')['id'])]:
            with self.subTest(table=table), self.assertRaises(sqlite3.IntegrityError):
                self.store.db.execute(f'DELETE FROM {table} WHERE id=?', (row_id,))
            with self.subTest(table=table), self.assertRaises(sqlite3.IntegrityError):
                self.store.db.execute(f'UPDATE {table} SET id=id WHERE id=?', (row_id,))

    def test_busy_worker_and_duplicate_assignment_cannot_start_second_run(self):
        task = self.task()
        body = {'task_id': task, 'session_id': self.worker['session_id']}
        first = self.call('assign', body, request_id='assign-once')
        self.assertEqual(self.call('assign', body, request_id='assign-once'), first)
        with self.assertRaises(Invalid):
            self.call('assign', body)
        with self.assertRaises(Invalid):
            self.assign(self.task())
        self.assertEqual(len(self.store.all('SELECT * FROM runs')), 1)

    def test_dependency_requires_acceptance_and_cycle_replan_is_atomic(self):
        a = self.task()
        b = self.task([a])
        with self.assertRaises(Invalid):
            self.assign(b)
        before = self.counts()
        with self.assertRaises(Invalid):
            self.call('replan', {'reason': 'bad cycle', 'tasks': {a: self.spec([b])}})
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.store.get('teams', self.coordinator['team_id'])['revision'], 1)
        run, _ = self.completed_run(a)
        self.review(run)
        self.assertTrue(self.assign(b)['run_id'])

    def test_replan_validates_final_graph_not_transient_edge_order(self):
        a = self.task()
        b = self.task([a])
        changed = self.call('replan', {'reason': 'reverse dependency',
                                     'tasks': {a: self.spec([b]), b: self.spec()}})
        self.assertEqual(changed['revision'], 2)
        self.assertEqual(json.loads(self.store.get('tasks', a)['spec'])['dependencies'], [b])

    def test_pause_desired_is_separate_from_observed_and_resume_is_explicit(self):
        run = self.assign()
        with self.store.transaction():
            self.store.update('runs', run['run_id'], observed='running', health='running')
        control = self.call('control', {'run_id': run['run_id'], 'action': 'pause'})
        state = self.store.get('runs', run['run_id'])
        self.assertEqual((state['desired'], state['observed']), ('paused', 'running'))
        self.assertGreater(control['generation'], state['confirmed_generation'])
        self.call('replan', {'reason': 'new context', 'tasks': {state['task_id']: self.spec()}})
        self.assertEqual(self.store.get('runs', run['run_id'])['desired'], 'paused')
        self.assertTrue(json.loads(self.store.get('tasks', state['task_id'])['holds']))
        self.call('control', {'run_id': run['run_id'], 'action': 'resume'})
        self.assertEqual(self.store.get('runs', run['run_id'])['desired'], 'running')
        self.call('control', {'run_id': run['run_id'], 'action': 'cancel'})
        with self.assertRaises(Invalid):
            self.call('control', {'run_id': run['run_id'], 'action': 'resume'})

    def test_ack_is_not_result_or_acceptance(self):
        run = self.assign()
        self.assertEqual(self.store.get('deliveries', run['delivery_id'])['state'], 'pending')
        self.call('ack', {'delivery_id': run['delivery_id']}, self.worker)
        row = self.store.get('runs', run['run_id'])
        self.assertIsNone(row['result_event'])
        self.assertEqual(self.store.get('tasks', row['task_id'])['state'], 'running')
        with self.assertRaises(Invalid):
            self.review(run)

    def test_old_plan_result_is_preserved_and_requires_explicit_assessment(self):
        run = self.assign()
        self.call('replan', {'reason': 'unrelated context update'})
        artifact = self.artifact()
        result = self.report(run, artifact_ids=[artifact])
        self.assertEqual(self.store.get('events', result['event_id'])['revision'], 1)
        self.release(run)
        with self.assertRaises(Invalid):
            self.review(run)
        accepted = self.review(run, compatible=True, compatibility_reason='Dependencies unchanged')
        self.assertEqual(accepted['state'], 'accepted')

    def test_acceptance_requires_ended_run_finalized_evidence_and_each_check(self):
        task = self.task(criteria=['tests pass'])
        run = self.assign(task)
        artifact = self.artifact()
        self.report(run, artifact_ids=[artifact])
        with self.assertRaises(Invalid):
            self.review(run)
        self.release(run)
        for checks in [[], [{'criterion': 'tests pass', 'passed': False, 'artifact_ids': [artifact]}]]:
            with self.assertRaises(Invalid):
                self.review(run, checks=checks)
        self.assertEqual(self.review(run, checks=[{'criterion': 'tests pass', 'passed': True,
                                                   'artifact_ids': [artifact]}])['state'], 'accepted')

    def test_empty_or_corrupt_evidence_cannot_be_accepted(self):
        run = self.assign()
        self.report(run)
        self.release(run)
        with self.assertRaises(Invalid):
            self.review(run)
        self.review(run, 'revise')
        retry, artifact = self.completed_run(self.store.get('runs', run['run_id'])['task_id'])
        self.assertNotEqual(run['run_id'], retry['run_id'])
        path = Path(self.store.get('artifacts', artifact)['path'])
        path.write_text('tampered data')
        with self.assertRaises(Invalid):
            self.review(retry)
        path.unlink()
        with self.assertRaises(Invalid):
            self.review(retry)

    def test_artifacts_are_copied_hashed_and_versioned(self):
        one = self.artifact(content='version 1')
        again = self.artifact(content='version 1')
        two = self.artifact(content='version 2')
        self.assertEqual(one, again)
        self.assertNotEqual(one, two)
        row = self.store.get('artifacts', one)
        self.assertEqual(Path(row['path']).read_text(), 'version 1')
        self.assertEqual(row['sha256'], hashlib.sha256(b'version 1').hexdigest())

    def test_corrupt_orphan_artifact_cannot_be_committed(self):
        content = b'intended evidence'
        digest = hashlib.sha256(content).hexdigest()
        directory = Path(self.temp.name) / 'artifacts' / self.coordinator['team_id']
        directory.mkdir(parents=True, exist_ok=True)
        (directory / digest).write_bytes(b'corrupt orphan')
        source = Path(self.temp.name) / 'source.txt'
        source.write_bytes(content)
        with self.assertRaises(Invalid):
            self.call('artifact', {'path': str(source)}, self.worker)
        self.assertEqual(self.store.all('SELECT * FROM artifacts'), [])

    def test_issue_coalescing_ack_and_resolution_are_independent(self):
        run = self.assign()
        first = self.report(run, 'question', coalescing_key='contract')
        second = self.report(run, 'question', coalescing_key='contract')
        self.assertEqual(first['issue_id'], second['issue_id'])
        inbox = self.store.read(self.coordinator['token'], 'inbox')
        self.assertEqual(len(inbox), 1)
        self.call('ack', {'delivery_id': inbox[0]['id']})
        self.assertEqual(len(self.store.read(self.coordinator['token'], 'inbox')), 1)
        self.call('resolve', {'issue_id': first['issue_id'], 'resolution': 'Answered'})
        self.assertEqual(self.store.read(self.coordinator['token'], 'inbox'), [])
        reopened = self.report(run, 'question', coalescing_key='contract')
        self.assertNotEqual(reopened['issue_id'], first['issue_id'])

    def test_escalated_issue_appears_in_urgent_filtered_inbox(self):
        run = self.assign()
        initial = self.report(run, 'question', coalescing_key='contract', priority='normal')
        self.report(run, 'conflict', coalescing_key='contract', priority='urgent')
        urgent = self.store.read(self.coordinator['token'], 'inbox', {'priority': 'urgent'})
        self.assertEqual([row['event_id'] for row in urgent], [initial['event_id']])

    def test_equal_coalescing_keys_on_different_tasks_do_not_merge_blockers(self):
        first = self.assign()
        other = self.call('register', {'name': 'W2'})
        second = self.assign(worker=other)
        a = self.report(first, 'conflict', coalescing_key='same-contract')
        b = self.report(second, 'conflict', actor=other, coalescing_key='same-contract')
        self.assertNotEqual(a['issue_id'], b['issue_id'])

    def test_coalesced_issue_can_escalate_to_acceptance_blocker(self):
        run = self.assign()
        first = self.report(run, 'question', coalescing_key='risk', blocks_acceptance=False)
        second = self.report(run, 'conflict', coalescing_key='risk', blocks_acceptance=True)
        self.assertEqual(first['issue_id'], second['issue_id'])
        self.assertEqual(self.store.get('issues', first['issue_id'])['blocks_acceptance'], 1)
        self.report(run, artifact_ids=[self.artifact()])
        self.release(run)
        with self.assertRaises(Invalid):
            self.review(run)

    def test_late_result_preserved_without_overwriting_newer_attempt(self):
        task = self.task()
        original = self.assign(task)
        self.release(original)
        # Simulate runtime reconciliation of an ended attempt with no result.
        with self.store.transaction():
            self.store.update('tasks', task, state='failed')
        current = self.assign(task)
        old_result = self.report(original, artifact_ids=[self.artifact()])
        self.assertEqual(self.store.get('tasks', task)['state'], 'running')
        self.assertEqual(self.store.get('events', old_result['event_id'])['run_id'], original['run_id'])
        self.assertIsNone(self.store.get('runs', current['run_id'])['result_event'])
        with self.assertRaises(Invalid):
            self.review(original)

    def test_dependency_needs_explicit_compatibility_after_replan(self):
        a = self.task()
        b = self.task([a])
        run, _ = self.completed_run(a)
        self.review(run)
        self.call('replan', {'reason': 'new plan'})
        with self.assertRaises(Invalid):
            self.assign(b)
        self.call('compatibility', {'task_id': a, 'compatible': False, 'reason': 'Contract may differ'})
        with self.assertRaises(Invalid):
            self.assign(b)
        self.call('compatibility', {'task_id': a, 'compatible': True, 'reason': 'Verified same contract'})
        self.assertTrue(self.assign(b)['run_id'])

    def test_urgent_ack_does_not_hide_older_normal_and_progress_is_quiet(self):
        run = self.assign()
        self.report(run, 'progress')
        self.assertEqual(self.store.read(self.coordinator['token'], 'inbox'), [])
        normal = self.report(run, 'proposal')
        urgent = self.report(run, 'conflict')
        inbox = self.store.read(self.coordinator['token'], 'inbox')
        self.assertEqual([row['event_id'] for row in inbox], [urgent['event_id'], normal['event_id']])
        self.call('ack', {'delivery_id': inbox[0]['id']})
        self.call('resolve', {'issue_id': urgent['issue_id'], 'resolution': 'Handled'})
        self.assertEqual([row['event_id'] for row in self.store.read(self.coordinator['token'], 'inbox')],
                         [normal['event_id']])

    def test_publication_preserves_source_and_tracks_each_recipient(self):
        run = self.assign()
        other = self.call('register', {'name': 'W2'})
        artifact = self.artifact()
        proposal = self.report(run, 'proposal', suggested_recipients=[other['agent_id']], artifact_ids=[artifact])
        self.assertEqual(self.store.read(other['token'], 'inbox'), [])
        body = {'proposal_event': proposal['event_id'], 'recipients': [self.worker['agent_id'], other['agent_id']]}
        publication = self.call('publish', body, request_id='publish-once')
        self.assertEqual(self.call('publish', body, request_id='publish-once'), publication)
        event = self.store.get('events', publication['event_id'])
        self.assertEqual(event['reply_to'], proposal['event_id'])
        self.assertEqual(json.loads(event['body'])['artifact_ids'], [artifact])
        self.call('ack', {'delivery_id': publication['deliveries'][1]}, other)
        self.assertEqual(self.store.get('deliveries', publication['deliveries'][0])['state'], 'pending')

    def test_takeover_fences_stale_commands_even_with_new_epoch_and_retargets_inbox(self):
        run = self.assign()
        self.report(run, 'question')
        previous = self.coordinator
        takeover = self.call('takeover', {'external_id': str(uuid.uuid4())})
        self.coordinator = takeover
        for epoch in (previous['epoch'], takeover['epoch']):
            with self.assertRaises(Invalid):
                self.call('control', {'run_id': run['run_id'], 'action': 'cancel'}, previous, epoch=epoch)
        with self.assertRaises(Invalid):
            self.store.read(previous['token'], 'inbox')
        inbox = self.store.read(takeover['token'], 'inbox')
        self.assertEqual(inbox[0]['target_session'], takeover['session_id'])
        self.call('control', {'run_id': run['run_id'], 'action': 'pause'})

    def test_team_ids_are_safe_path_components(self):
        for team_id in ('../escape', '/tmp/escape', 'nested/team', '', '.', 'a' * 101, 12):
            with self.subTest(team_id=team_id), self.assertRaises(Invalid):
                self.store.bootstrap('Invalid team', team_id=team_id)
        self.assertEqual(self.store.bootstrap('Valid team', team_id='valid_team-12')['team_id'], 'valid_team-12')

    def test_retry_cancelled_task_requires_released_reconciled_execution(self):
        task = self.task()
        run = self.assign(task)
        with self.store.transaction():
            self.store.update('tasks', task, state='cancelled')
        with self.assertRaises(Invalid):
            self.call('retry', {'task_id': task, 'reason': 'Urgent replacement'})
        self.release(run)
        self.call('retry', {'task_id': task, 'reason': 'Urgent replacement'})
        self.call('replan', {'reason': 'Replace stopped work', 'tasks': {task: self.spec()}})
        replacement = self.assign(task)
        self.assertNotEqual(replacement['run_id'], run['run_id'])
        self.assertEqual(self.store.get('runs', run['run_id'])['released'], 1)

    def test_new_worker_session_is_fresh_and_old_publication_does_not_migrate(self):
        run = self.assign()
        proposal = self.report(run, 'proposal')
        publication = self.call('publish', {'proposal_event': proposal['event_id'],
                                            'recipients': [self.worker['agent_id']]})
        with self.assertRaises(Invalid):
            self.call('session', {'agent_id': self.worker['agent_id']})
        self.release(run)
        same = self.call('session', {'agent_id': self.worker['agent_id'], 'fresh': False,
                                     'session_id': self.worker['session_id']})
        self.assertEqual(same['session_id'], self.worker['session_id'])
        new = self.call('session', {'agent_id': self.worker['agent_id']})
        self.assertNotEqual(new['session_id'], self.worker['session_id'])
        self.assertIsNone(self.store.get('sessions', new['session_id'])['external_id'])
        with self.assertRaises(Invalid):
            self.store.authenticate(self.worker['token'])
        self.assertEqual(self.store.read(new['token'], 'inbox'), [])
        with self.assertRaises(Invalid):
            self.call('ack', {'delivery_id': publication['deliveries'][0]}, new)

    def test_assignment_is_in_run_filtered_history(self):
        run = self.assign()
        history = self.store.read(self.coordinator['token'], 'history', {'run_id': run['run_id']})
        self.assertEqual([row['id'] for row in history], [run['event_id']])

    def test_task_spec_types_are_validated(self):
        for invalid in ({'criteria': [' ']}, {'context': {}}, {'cwd': []}, {'write': 'yes'}):
            with self.subTest(invalid=invalid), self.assertRaises(Invalid):
                self.call('task', {'spec': dict(self.spec(), **invalid)})

    def test_reviewed_commits_require_unique_full_lowercase_oids(self):
        run, _ = self.completed_run()
        for commits in ('a' * 40, ['abc123'], ['A' * 40], ['a' * 40, 'a' * 40], [12]):
            with self.subTest(commits=commits), self.assertRaises(Invalid):
                self.review(run, reviewed_commits=commits)
        response = self.review(run, reviewed_commits=['a' * 40, 'b' * 64])
        self.assertEqual(json.loads(self.store.get('events', response['event_id'])['body'])['reviewed_commits'],
                         ['a' * 40, 'b' * 64])

    def test_register_without_adapter_is_grok_high(self):
        worker = self.call('register', {'name': 'personal'})
        config = json.loads(self.store.get('agents', worker['agent_id'])['config'])
        self.assertEqual((config['adapter'], config['model'], config['effort']), ('grok', 'grok-4.6', 'high'))
        self.assertNotIn('mode', config)
        explicit = self.call('register', {'name': 'codex-worker', 'adapter': 'codex'})
        other = json.loads(self.store.get('agents', explicit['agent_id'])['config'])
        self.assertEqual((other['adapter'], other['model'], other['effort']), ('codex', 'gpt-6-astra', 'medium'))

    def test_budget_validation_and_status_usage_unknown(self):
        task = self.task()
        with self.assertRaises(Invalid):
            self.call('budget', {'scope': 'task', 'id': task, 'budgets': {'model_calls': 0}})
        self.call('budget', {'scope': 'task', 'id': task, 'budgets': {'model_calls': 3}})
        run = self.assign(task)
        status = self.store.read(self.coordinator['token'], 'status')
        row = next(r for r in status['runs'] if r['id'] == run['run_id'])
        self.assertIsNone(row['usage'])
        self.assertEqual(row['budgets']['model_calls'], 3)
        home = self.store.read(self.coordinator['token'], 'home')
        self.assertEqual(home['teams'][0]['id'], self.coordinator['team_id'])
        self.assertNotIn('token', home)
        self.assertIsNone(self.store.read(self.coordinator['token'], 'usage', {'run_id': run['run_id']}))


if __name__ == '__main__':
    unittest.main()
