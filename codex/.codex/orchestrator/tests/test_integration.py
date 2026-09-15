"""Stack CI contract and acceptance tests with deterministic GitHub responses."""
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from orchestrator.daemon import Runtime
from orchestrator.resources import verify_stack_ci
from orchestrator.store import Invalid, dump


class StackCITests(unittest.TestCase):
    def setUp(self):
        self.prs = {
            1: {'number': 1, 'headRefOid': 'a' * 40, 'baseRefName': 'main', 'state': 'OPEN', 'url': 'https://example.test/1'},
            2: {'number': 2, 'headRefOid': 'b' * 40, 'baseRefName': 'branch-1', 'state': 'OPEN', 'url': 'https://example.test/2'},
            3: {'number': 3, 'headRefOid': 'c' * 40, 'baseRefName': 'branch-2', 'state': 'OPEN', 'url': 'https://example.test/3'},
        }
        self.parents = {'branch-1': [1], 'branch-2': [2]}
        self.checks = {number: [{'name': 'required-tests', 'bucket': 'pass', 'state': 'SUCCESS', 'link': 'https://example.test/ci'}]
                       for number in self.prs}
        self.checked = []
        self.after_check = lambda number: None

    def gh(self, command, **kwargs):
        self.assertEqual(command[0], 'gh')
        if command[1:3] == ['repo', 'view']:
            return json.dumps({'defaultBranchRef': {'name': 'main'}})
        if command[1:3] == ['pr', 'list']:
            branch = command[command.index('--head') + 1]
            return json.dumps([{'number': number, 'headRefOid': self.prs[number]['headRefOid']}
                               for number in self.parents.get(branch, [])])
        number = int(command[3])
        if command[1:3] == ['pr', 'checks']:
            self.assertIn('--required', command)
            self.checked.append(number)
            self.after_check(number)
            if self.checks[number] is None:
                raise subprocess.CalledProcessError(1, command, stderr='No required checks available')
            return json.dumps(self.checks[number])
        self.assertEqual(command[1:3], ['pr', 'view'])
        fields = command[command.index('--json') + 1].split(',')
        return json.dumps({field: self.prs[number][field] for field in fields})

    def verify(self):
        with patch('orchestrator.resources.run', side_effect=self.gh):
            return verify_stack_ci('/fixture', 3, 'c' * 40)

    def test_all_downstack_prs_have_required_ci_checked(self):
        result = self.verify()
        self.assertTrue(result['passed'])
        self.assertEqual(self.checked, [3, 2, 1])
        self.assertEqual([row['number'] for row in result['stack']], [3, 2, 1])

    def test_empty_missing_pending_or_failing_required_checks_fail(self):
        for checks in ([], None, [{'bucket': 'pending'}], [{'bucket': 'fail'}]):
            with self.subTest(checks=checks):
                self.checks[2] = checks
                self.assertFalse(self.verify()['passed'])

    def test_head_changes_during_required_check_fetch_fail(self):
        self.after_check = lambda number: self.prs[number].update(headRefOid='d' * 40) if number == 2 else None
        self.assertFalse(self.verify()['passed'])

    def test_previously_checked_head_changes_while_checking_parent_fail(self):
        self.after_check = lambda number: self.prs[3].update(headRefOid='d' * 40) if number == 1 else None
        self.assertFalse(self.verify()['passed'])

    def test_base_changes_during_checks_fail(self):
        self.after_check = lambda number: self.prs[3].update(baseRefName='main') if number == 1 else None
        self.assertFalse(self.verify()['passed'])

    def test_pr_closes_during_checks_fail(self):
        self.after_check = lambda number: self.prs[3].update(state='CLOSED') if number == 1 else None
        self.assertFalse(self.verify()['passed'])

    def test_closed_parent_fails(self):
        self.prs[2]['state'] = 'CLOSED'
        self.assertFalse(self.verify()['passed'])

    def test_missing_or_ambiguous_parent_fails(self):
        for parents in ([], [1, 2]):
            with self.subTest(parents=parents):
                self.parents['branch-2'] = parents
                self.assertFalse(self.verify()['passed'])

    def test_cycle_fails_without_rechecking_same_pr(self):
        self.prs[1]['baseRefName'] = 'branch-3'
        self.parents['branch-3'] = [3]
        self.assertFalse(self.verify()['passed'])
        self.assertEqual(self.checked, [3, 2, 1])


class IntegrationAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = Runtime(self.temp.name)
        self.addCleanup(self.cleanup)
        self.store = self.runtime.store
        self.coordinator = self.store.bootstrap('Review integration')
        self.worker = self.command('register', {'name': 'Integrator', 'adapter': 'fake'})
        self.task = self.command('task', {'spec': {'objective': 'Assemble accepted changes', 'expected_output': 'CI evidence',
                                                 'integration': True, 'cwd': self.temp.name}})['task_id']
        self.run = self.command('assign', {'task_id': self.task, 'session_id': self.worker['session_id']})
        self.runtime.handle({'op': 'runner_observe', 'token': self.worker['token'], 'run_id': self.run['run_id'],
                             'observation_id': 'finished-integration', 'kind': 'finished',
                             'body': {'exit_code': 0, 'result': 'Integrated result'}})
        with self.store.transaction():
            self.store.update('operations', self.run['operation_id'], state='succeeded')
        self.head = 'a' * 40

    def cleanup(self):
        self.runtime.executor.shutdown(wait=True)
        self.store.db.close()

    def command(self, kind, body, request_id=None):
        return self.runtime.handle({'op': 'command', 'token': self.coordinator['token'],
                                    'epoch': self.coordinator['epoch'], 'request_id': request_id or str(uuid.uuid4()),
                                    'kind': kind, 'body': body})

    def operation(self, action, created, state='succeeded', passed=True, head=None):
        with self.store.transaction():
            operation = self.store.operation(self.coordinator['team_id'], None, 'integration',
                                             {'task_id': self.task, 'action': action, 'expected_head': head or self.head})
            self.store.update('operations', operation, state=state, created=created,
                              outcome=dump({'passed': passed, 'head': head or self.head}))
        return operation

    def review(self, request_id=None):
        return self.command('review', {'run_id': self.run['run_id'], 'decision': 'accept',
                                       'reason': 'Reviewed integration evidence'}, request_id)

    def test_submitted_integration_requires_passing_ci_after_submission(self):
        self.operation('submit', 20)
        with self.assertRaises(Invalid):
            self.review()
        self.operation('ci', 10)
        with self.assertRaises(Invalid):
            self.review()
        self.operation('ci', 30, passed=False)
        with self.assertRaises(Invalid):
            self.review()
        self.operation('ci', 40)
        with patch('orchestrator.daemon.subprocess.run', return_value=SimpleNamespace(stdout=self.head + '\n')):
            self.assertEqual(self.review()['state'], 'accepted')

    def test_changed_local_head_after_ci_prevents_acceptance(self):
        self.operation('submit', 10)
        self.operation('ci', 20)
        with patch('orchestrator.daemon.subprocess.run', return_value=SimpleNamespace(stdout='b' * 40 + '\n')):
            with self.assertRaises(Invalid):
                self.review()

    def test_unresolved_integration_operation_prevents_acceptance(self):
        self.operation('submit', 10)
        self.operation('ci', 20)
        self.operation('create', 30, state='uncertain')
        with self.assertRaises(Invalid):
            self.review()

    def test_identical_review_retry_returns_receipt_after_state_changes(self):
        self.operation('submit', 10)
        self.operation('ci', 20)
        with patch('orchestrator.daemon.subprocess.run', return_value=SimpleNamespace(stdout=self.head + '\n')):
            receipt = self.review('accept-once')
        self.operation('create', 30, state='uncertain')
        with patch('orchestrator.daemon.subprocess.run', side_effect=AssertionError('Must return durable receipt')):
            self.assertEqual(self.review('accept-once'), receipt)
        with self.assertRaises(Invalid):
            self.command('review', {'run_id': self.run['run_id'], 'decision': 'reject', 'reason': 'Changed content'}, 'accept-once')

    def test_accepted_integration_cannot_mutate_checkout_without_new_review_task(self):
        with self.store.transaction():
            self.store.insert('resources', id='tree', team_id=self.coordinator['team_id'], kind='worktree',
                              identity=str(Path(self.temp.name).resolve()), detail='{}', state='idle')
        self.review()
        with self.assertRaises(Invalid):
            self.command('integration', {'task_id': self.task, 'action': 'create',
                                         'branch': 'unreviewed-followup', 'message': 'Changes after acceptance'})

    def test_completed_team_cannot_start_new_external_effect(self):
        self.review()
        self.command('finish', {})
        with self.assertRaises(Invalid):
            self.command('worktree', {'repo': self.temp.name, 'path': str(Path(self.temp.name) / 'late-tree'),
                                      'branch': 'late-branch', 'ref': 'HEAD'})


if __name__ == '__main__':
    unittest.main()
