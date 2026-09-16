import concurrent.futures
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from orchestrator.grok_bridge import Bridge, alive
from orchestrator.runner import durable_json


class GrokBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bridge = Bridge(self.root / 'state')
        self.count = 0

    def tearDown(self):
        for row in self.bridge.inspect()['runs']:
            self.bridge.cancel(row['id'])
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with self.bridge.connect() as db:
                rows = list(db.execute('SELECT state,data FROM runs'))
            live = any(alive(i) for row in rows for i in [json.loads(row['data']).get('worker'), *json.loads(row['data']).get('children', [])])
            settled = all(row['state'] in ('completed', 'failed', 'cancelled', 'interrupted') for row in rows)
            if settled and not live:
                break
            time.sleep(.1)
        self.temp.cleanup()

    def spawn(self, **spec):
        self.count += 1
        return self.bridge.spawn('FAKE_SCRIPT=' + json.dumps(spec), str(self.root), str(self.count), adapter='fake')

    def finish(self, run):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            result = self.bridge.wait([run['run_id']], timeout=2)
            if result['results']:
                return self.bridge.inspect(run['run_id'])
        self.fail('run did not settle: ' + json.dumps(self.bridge.inspect(run['run_id'])))

    def test_parallel_durable_results_history_and_cursor(self):
        a = self.spawn(delay=.2, progress='evidence A')
        b = self.spawn(delay=.3, progress='evidence B')
        first = self.finish(a)
        second = self.finish(b)
        self.assertEqual(first['state'], 'completed')
        self.assertEqual(second['state'], 'completed')
        reconnected = Bridge(self.bridge.home)
        events = reconnected.wait([a['run_id'], b['run_id']], timeout=0)
        self.assertEqual(len(events['results']), 2)
        self.assertEqual(reconnected.wait([a['run_id'], b['run_id']], after=events['cursor'], timeout=0)['results'], [])
        page = reconnected.inspect(a['run_id'], limit=1)
        self.assertEqual(page['history'][0]['role'], 'user')
        self.assertEqual(reconnected.inspect(a['run_id'], after=page['cursor'])['history'][0]['text'], 'evidence A')
        self.assertTrue((Path(first['artifacts_directory']) / 'result.json').exists())

    def test_concurrent_request_replay_starts_once(self):
        def request(_):
            return self.bridge.spawn('FAKE_SCRIPT={"delay":0.5}', str(self.root), 'same', adapter='fake')
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            runs = list(pool.map(request, range(4)))
        self.assertEqual(len({r['run_id'] for r in runs}), 1)
        self.assertEqual(self.finish(runs[0])['state'], 'completed')
        with self.assertRaisesRegex(ValueError, 'different input'):
            self.bridge.spawn('different', str(self.root), 'same', adapter='fake')

    def test_busy_resume_then_continuation(self):
        prior_report = {'outcome': 'completed', 'summary': 'unique prior investigation',
                        'changes': ['x' * 10000], 'validation': [], 'unresolved': [], 'artifacts': []}
        first = self.spawn(delay=.5, report=prior_report)
        with self.assertRaisesRegex(ValueError, 'busy'):
            self.bridge.resume(first['session_id'], 'next', 'next')
        self.finish(first)
        second = self.bridge.resume(first['session_id'], 'next', 'next', effort='xhigh')
        self.assertEqual(second['session_id'], first['session_id'])
        self.assertNotEqual(second['run_id'], first['run_id'])
        self.assertEqual(self.finish(second)['state'], 'completed')
        self.assertTrue(json.loads(self.bridge.row(second['run_id'])['data'])['resume'])
        prompt = (self.bridge.directory(second['run_id']) / 'prompt.txt').read_text()
        self.assertNotIn(prior_report['summary'], prompt)
        self.assertNotIn(prior_report['changes'][0], prompt)
        self.assertIn(first['run_id'], prompt)
        self.assertEqual(self.bridge.inspect(first['run_id'])['report'], prior_report)

    def test_session_totals_cover_all_runs_and_wait_exposes_usage(self):
        first = self.spawn()
        self.finish(first)
        self.bridge.update(first['run_id'], usage={'input_tokens': 100}, metrics={'num_turns': 2})
        second = self.bridge.resume(first['session_id'], 'next', 'next')
        self.finish(second)
        self.bridge.update(second['run_id'], usage={'input_tokens': 20, 'cache_read_input_tokens': 300})
        session = self.bridge.inspect(session_id=first['session_id'], limit=1)
        self.assertEqual(len(session['runs']), 1)
        self.assertEqual(session['session_totals']['totals'],
                         {'input_tokens': 120, 'cache_read_input_tokens': 300, 'num_turns': 2})
        result = self.bridge.wait([first['run_id'], second['run_id']], timeout=0)
        self.assertEqual(result['results'][0]['usage'], {'input_tokens': 100})
        self.assertEqual(result['session_totals'][first['session_id']], session['session_totals'])
        self.assertEqual(self.bridge.wait([first['run_id'], second['run_id']],
                         after=result['cursor'], timeout=0)['results'], [])

    def test_low_disk_rejects_new_launch_but_not_idempotent_replay(self):
        first = self.spawn()
        self.finish(first)
        with patch('orchestrator.grok_bridge.shutil.disk_usage') as disk:
            disk.return_value.free = 0
            with self.assertRaisesRegex(ValueError, 'Insufficient disk'):
                self.spawn()
            same = self.bridge.spawn('FAKE_SCRIPT={}', str(self.root), '1', adapter='fake')
            self.assertEqual(same['run_id'], first['run_id'])
        self.assertEqual(len(self.bridge.inspect()['runs']), 1)

    def test_disk_guard_checks_worktree_volume_and_can_be_disabled(self):
        from types import SimpleNamespace
        with patch('orchestrator.grok_bridge.shutil.disk_usage',
                   side_effect=[SimpleNamespace(free=2**40), SimpleNamespace(free=0)]):
            with self.assertRaisesRegex(ValueError, 'Insufficient disk'):
                self.spawn()
        self.bridge.min_free_bytes = 0
        with patch('orchestrator.grok_bridge.shutil.disk_usage', return_value=SimpleNamespace(free=0)):
            self.assertEqual(self.finish(self.spawn())['state'], 'completed')

    def test_permission_error_during_descendant_scan_does_not_abort_provider(self):
        with patch.object(self.bridge, 'launch'):
            run = self.spawn(delay=.3)
        script = '''from unittest.mock import patch
from orchestrator.grok_bridge import Bridge, execute
import sys
with patch('orchestrator.grok_bridge._snapshot', side_effect=PermissionError(1, 'proc_pidinfo could not establish identity')):
    execute(Bridge(sys.argv[1]), sys.argv[2])
'''
        child = subprocess.run([sys.executable, '-c', script, str(self.bridge.home), run['run_id']],
                               capture_output=True, text=True, timeout=15)
        self.assertEqual(child.returncode, 0, child.stderr)
        result = self.bridge.inspect(run['run_id'])
        self.assertEqual(result['state'], 'completed')
        self.assertIn('proc_pidinfo', result['observation_error'])

    def test_unknown_owned_identity_still_fences_recovery(self):
        with patch('orchestrator.grok_bridge.ProcessIdentity.state', side_effect=PermissionError):
            self.assertTrue(alive({'pid': 42, 'start_identity': 'unreadable'}))

    def test_cancel_cannot_release_an_unobservable_owned_process(self):
        with patch.object(self.bridge, 'launch'):
            run = self.spawn()
        self.bridge.update(run['run_id'], provider={'pid': 42, 'start_identity': 'unreadable'})
        with self.bridge.transaction() as db:
            db.execute("UPDATE runs SET state='interrupted' WHERE id=?", (run['run_id'],))
        with patch('orchestrator.grok_bridge.ProcessIdentity.state', side_effect=PermissionError), \
             patch('orchestrator.grok_bridge.control_tree', side_effect=PermissionError('cannot inspect')):
            self.bridge.cancel_interrupted(self.bridge.row(run['run_id']))
        row = self.bridge.row(run['run_id'])
        self.assertEqual(row['released'], 0)
        self.assertEqual(json.loads(row['data'])['observation_error'], 'cannot inspect')
        self.bridge.update(run['run_id'], provider=None)

    def test_invalid_report_missing_terminal_and_provider_failure(self):
        for spec in ({'report': 'bad'}, {'missing_result': True}, {'exit_code': 1}, {'error': 'provider unavailable'}):
            with self.subTest(spec=spec):
                self.assertEqual(self.finish(self.spawn(**spec))['state'], 'failed')
        report = {'outcome': 'blocked', 'summary': 'Need input', 'changes': [], 'validation': [], 'unresolved': ['missing spec'], 'artifacts': []}
        result = self.finish(self.spawn(report=report))
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(result['report']['outcome'], 'blocked')

    def test_cancel_observes_child_cleanup(self):
        run = self.spawn(delay=30, child_seconds=30)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            data = json.loads(self.bridge.row(run['run_id'])['data'])
            if len(data.get('children', [])) >= 2:
                break
            time.sleep(.1)
        self.assertGreaterEqual(len(data.get('children', [])), 2)
        self.bridge.cancel(run['run_id'])
        result = self.finish(run)
        self.assertEqual(result['state'], 'cancelled')
        self.assertTrue(result['released'])
        self.assertFalse(any(alive(i) for i in data['children']))

    def test_normal_exit_waits_for_observed_child(self):
        start = time.monotonic()
        run = self.spawn(delay=.5, child_seconds=1.5)
        result = self.finish(run)
        self.assertEqual(result['state'], 'completed')
        self.assertGreater(time.monotonic() - start, 1.4)

    def test_capacity_and_writer_exclusion(self):
        args = dict(task='FAKE_SCRIPT={"delay":30}', cwd=str(self.root), adapter='fake')
        first = self.bridge.spawn(**args, request_id='writer', write_scope=['.'])
        with self.assertRaisesRegex(ValueError, 'Another writer'):
            self.bridge.spawn(**args, request_id='conflict', write_scope=['.'])
        self.spawn(delay=30)
        self.spawn(delay=30)
        with self.assertRaisesRegex(ValueError, 'Three workers'):
            self.spawn()
        self.bridge.cancel(first['run_id'])

    def test_unlaunched_crash_is_not_replayed_and_needs_recovery(self):
        with patch.object(self.bridge, 'launch'):
            run = self.spawn()
        with self.bridge.transaction() as db:
            db.execute('UPDATE runs SET created=0 WHERE id=?', (run['run_id'],))
        self.assertEqual(self.bridge.inspect(run['run_id'])['state'], 'interrupted')
        with self.assertRaisesRegex(ValueError, 'recovery_checked'):
            self.bridge.resume(run['session_id'], 'follow-up', 'retry')
        resumed = self.bridge.resume(run['session_id'], 'follow-up', 'retry', recovery_checked=True)
        self.assertEqual(self.finish(resumed)['state'], 'completed')

    def test_result_persisted_before_transaction_crash_is_recovered(self):
        with patch.object(self.bridge, 'launch'):
            run = self.spawn()
        durable_json(self.bridge.directory(run['run_id']) / 'result.json',
                     {'state': 'completed', 'released': True, 'report': {'summary': 'saved'}})
        with self.bridge.transaction() as db:
            db.execute('UPDATE runs SET created=0 WHERE id=?', (run['run_id'],))
        result = self.bridge.inspect(run['run_id'])
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(result['report']['summary'], 'saved')

    def test_supervisor_crash_fences_live_provider(self):
        run = self.spawn(delay=30)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            data = json.loads(self.bridge.row(run['run_id'])['data'])
            raw = self.bridge.directory(run['run_id']) / 'provider.jsonl'
            if data.get('provider') and raw.exists() and raw.stat().st_size:
                break
            time.sleep(.1)
        os.kill(data['worker']['pid'], signal.SIGKILL)
        time.sleep(.2)
        self.assertEqual(self.bridge.inspect(run['run_id'])['state'], 'interrupted')
        with self.assertRaisesRegex(ValueError, 'live owned'):
            self.bridge.resume(run['session_id'], 'next', 'next', recovery_checked=True)
        self.bridge.cancel(run['run_id'])
        self.assertFalse(alive(data['provider']))

    def test_history_excludes_reasoning_and_keeps_tool_evidence(self):
        from orchestrator.grok_bridge import history_records
        records = history_records(json.dumps({'type': 'assistant', 'message': {'content': [
            {'type': 'thinking', 'thinking': 'private', 'signature': 'opaque'},
            {'type': 'text', 'text': 'explanation'},
            {'type': 'tool_use', 'id': 'call-1', 'name': 'read_file', 'input': {'path': 'input.json'}}]}}))
        self.assertEqual([r['role'] for r in records], ['assistant', 'tool_call'])
        self.assertNotIn('private', json.dumps(records))
        self.assertEqual(records[1]['input']['path'], 'input.json')

    def test_history_is_bounded_and_can_advance_past_large_records(self):
        run = self.spawn()
        self.finish(run)
        history = self.bridge.directory(run['run_id']) / 'history.jsonl'
        history.write_text(json.dumps({'text': 'x' * 50000}) + '\n' + json.dumps({'text': 'next'}) + '\n')
        page = self.bridge.inspect(run['run_id'], limit=1)
        self.assertTrue(page['history'][0]['truncated'])
        self.assertLess(len(json.dumps(page['history'])), 10000)
        self.assertEqual(self.bridge.inspect(run['run_id'], after=page['cursor'])['history'][0]['text'], 'next')

    def test_provider_gate_registers_before_exec_and_rejects_recovery(self):
        from orchestrator.grok_bridge import launch_provider
        from orchestrator.resources import ProcessIdentity
        with patch.object(self.bridge, 'launch'):
            run = self.spawn()
        self.bridge.update(run['run_id'], worker=ProcessIdentity.read(os.getpid()))
        with self.bridge.transaction() as db:
            db.execute("UPDATE runs SET state='running' WHERE id=?", (run['run_id'],))
        def exec_checked(*args):
            data = json.loads(self.bridge.row(run['run_id'])['data'])
            self.assertEqual(data['provider']['pid'], os.getpid())
        with patch('orchestrator.grok_bridge.os.execvp', side_effect=exec_checked) as execute:
            launch_provider(self.bridge, run['run_id'])
            execute.assert_called_once()
        # Remove synthetic ownership of this test process before cancellation.
        self.bridge.update(run['run_id'], worker=None, provider=None)
        self.bridge.settle(run['run_id'], 'interrupted', {}, released=False)
        with patch('orchestrator.grok_bridge.os.execvp') as execute:
            launch_provider(self.bridge, run['run_id'])
            execute.assert_not_called()
        self.assertTrue(self.bridge.cancel(run['run_id'])['released'])

    def test_durable_success_survives_failed_commit_and_exception_settlement(self):
        from contextlib import contextmanager
        with patch.object(self.bridge, 'launch'):
            run = self.spawn()
        original = self.bridge.transaction
        @contextmanager
        def failed_commit():
            with original() as db:
                yield db
                raise RuntimeError('injected commit failure')
        with patch.object(self.bridge, 'transaction', failed_commit):
            with self.assertRaisesRegex(RuntimeError, 'commit failure'):
                self.bridge.settle(run['run_id'], 'completed', {'report': {'summary': 'saved'}})
        self.bridge.settle(run['run_id'], 'failed', {'error': 'commit failed'})
        result = self.bridge.inspect(run['run_id'])
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(result['report']['summary'], 'saved')

    def test_interrupted_run_preserves_provider_report_without_claiming_success(self):
        with patch.object(self.bridge, 'launch'):
            run = self.spawn()
        report = {'outcome': 'completed', 'summary': 'provider answer', 'changes': [], 'validation': [], 'unresolved': [], 'artifacts': []}
        raw = self.bridge.directory(run['run_id']) / 'provider.jsonl'
        raw.write_text(json.dumps({'type': 'result', 'subtype': 'success', 'result': json.dumps(report)}) + '\n')
        with self.bridge.transaction() as db:
            db.execute('UPDATE runs SET created=0 WHERE id=?', (run['run_id'],))
        result = self.bridge.inspect(run['run_id'])
        self.assertEqual(result['state'], 'interrupted')
        self.assertEqual(result['report'], report)
        self.assertFalse(result['released'])

    def test_cancel_survives_supervisor_death_during_request(self):
        run = self.spawn(delay=30)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            data = json.loads(self.bridge.row(run['run_id'])['data'])
            raw = self.bridge.directory(run['run_id']) / 'provider.jsonl'
            if data.get('provider') and raw.exists() and raw.stat().st_size:
                break
            time.sleep(.1)
        original = self.bridge.recover
        calls = 0
        def recover_then_crash():
            nonlocal calls
            original()
            calls += 1
            if calls == 1:
                os.kill(data['worker']['pid'], signal.SIGKILL)
                time.sleep(.1)
        with patch.object(self.bridge, 'recover', recover_then_crash):
            result = self.bridge.cancel(run['run_id'])
        self.assertEqual(result['state'], 'interrupted')
        self.assertTrue(result['released'])
        self.assertFalse(alive(data['provider']))

    def test_request_replay_survives_removed_working_directory(self):
        cwd = self.root / 'workspace'
        cwd.mkdir()
        args = {'task': 'FAKE_SCRIPT={}', 'cwd': str(cwd), 'request_id': 'replay-removed', 'adapter': 'fake'}
        run = self.bridge.spawn(**args)
        self.finish(run)
        cwd.rmdir()
        self.assertEqual(self.bridge.spawn(**args)['run_id'], run['run_id'])
