import copy
import fcntl
import json
from pathlib import Path
import tempfile
import sys
import time
import unittest
from unittest.mock import patch

from orchestrator.runner import Runner, assignment_prompt, durable_json


class FakeDaemon:
    def __init__(self, cwd, script=None):
        script = script or {'result': 'completed'}
        self.state = {
            'epoch': 1, 'control_epoch': 1, 'assignment_delivery_id': 'assignment-delivery',
            'run': {'id': 'run-test', 'assignment_event': 'assignment-event', 'revision': 1,
                    'control_generation': 0, 'desired': 'running'},
            'assignment': {'id': 'assignment-event', 'body': json.dumps({'spec': {
                'objective': 'FAKE_SCRIPT=' + json.dumps(script), 'cwd': str(cwd),
                'context': '', 'expected_output': 'result'}})},
            'session': {'id': 'session-test', 'config': json.dumps({'adapter': 'fake', 'model': 'fake', 'effort': 'medium'}),
                        'external_id': None},
            'messages': [],
        }
        self.observations = []
        self.seen = set()
        self.fail_after_commit = False
        self.on_observation = None

    def call(self, home, message):
        if message['op'] == 'runner_poll':
            return copy.deepcopy(self.state)
        oid = message['observation_id']
        if oid not in self.seen:
            self.seen.add(oid)
            self.observations.append(copy.deepcopy(message))
            if self.on_observation:
                self.on_observation(message)
        if self.fail_after_commit:
            self.fail_after_commit = False
            raise OSError('socket closed after daemon commit')
        return {'ok': True}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def runner(self, daemon):
        return Runner(self.home, 'run-test', 'test-token', daemon.call)

    def test_fake_result_and_crash_after_observation_commit(self):
        daemon = FakeDaemon(self.home)
        daemon.fail_after_commit = True
        runner = self.runner(daemon)
        self.assertEqual(runner.execute(), 0)
        kinds = [o['kind'] for o in daemon.observations]
        self.assertEqual(kinds.count('ready'), 1)
        self.assertEqual(kinds.count('accepted'), 1)
        self.assertEqual(kinds.count('finished'), 1)
        self.assertEqual(daemon.observations[-1]['body']['result'], 'completed')
        self.assertEqual(daemon.observations[-1]['body']['exit_code'], 0)
        self.assertEqual(json.loads(runner.path.read_text())['outbox'], [])
        # Finished journal replay must not launch or emit a second finish.
        self.assertEqual(self.runner(daemon).execute(), 0)
        self.assertEqual(len([o for o in daemon.observations if o['kind'] == 'finished']), 1)

    def test_ambiguous_launch_never_reexecutes(self):
        daemon = FakeDaemon(self.home)
        runner = self.runner(daemon)
        runner.journal['phase'] = 'launch_intent'
        runner.save()
        with patch('orchestrator.runner.subprocess.Popen') as launch:
            self.assertEqual(runner.execute(), 2)
            launch.assert_not_called()
        self.assertEqual(daemon.observations[-1]['kind'], 'uncertain')
        self.assertFalse(any(o['kind'] == 'finished' for o in daemon.observations))

    def test_exclusive_lock_prevents_duplicate_runner(self):
        daemon = FakeDaemon(self.home)
        runner = self.runner(daemon)
        with (runner.directory / 'runner.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(runner.execute(), 0)
        self.assertEqual(daemon.observations, [])

    def test_publication_is_injected_by_exact_followup_before_ack(self):
        daemon = FakeDaemon(self.home, {'progress': ['initial progress'], 'delay': 0.15,
                                         'result': 'initial result'})
        def publish(message):
            if message['kind'] == 'progress' and not daemon.state['messages']:
                daemon.state['messages'] = [{'id': 'publication-delivery', 'event_id': 'pub-event',
                                            'type': 'publication', 'body': json.dumps({'text': 'Revise the answer'})}]
        daemon.on_observation = publish
        runner = self.runner(daemon)
        self.assertEqual(runner.execute(), 0)
        kinds = [o['kind'] for o in daemon.observations]
        started = [i for i, kind in enumerate(kinds) if kind == 'started']
        self.assertEqual(len(started), 2)
        self.assertGreater(kinds.index('message_ack'), started[1])
        self.assertEqual(runner.journal['turn'], 2)
        self.assertEqual(runner.journal['acked_messages'], ['publication-delivery'])
        self.assertIn(runner.journal['external_id'], runner.journal['provider_command'])

    def test_cancel_reaps_provider_before_finished(self):
        daemon = FakeDaemon(self.home, {'progress': ['started'], 'delay': 3, 'result': 'too late'})
        def cancel(message):
            if message['kind'] == 'progress':
                daemon.state['run'].update(control_generation=1, desired='cancelled')
        daemon.on_observation = cancel
        runner = self.runner(daemon)
        self.assertEqual(runner.execute(), 0)
        controls = [o['body'] for o in daemon.observations if o['kind'] == 'control']
        self.assertTrue(controls)
        self.assertIn(controls[-1]['outcome'], ('confirmed', 'uncertain'))
        self.assertEqual(daemon.observations[-1]['kind'], 'finished')
        self.assertIsNone(runner.process)

    def test_stale_epoch_never_signals_provider(self):
        daemon = FakeDaemon(self.home)
        daemon.state.update(epoch=2, control_epoch=1)
        daemon.state['run'].update(control_generation=1, desired='paused')
        runner = self.runner(daemon)
        with patch.object(runner, 'signal_provider') as signal_provider:
            runner.apply_control(daemon.state)
            signal_provider.assert_not_called()
        self.assertEqual(daemon.observations, [])

    def test_takeover_after_acceptance_blocks_launch_and_stale_cancel(self):
        daemon = FakeDaemon(self.home)
        assignment = json.loads(daemon.state['assignment']['body'])
        assignment['epoch'] = 1
        daemon.state['assignment']['body'] = json.dumps(assignment)
        def takeover(message):
            if message['kind'] == 'accepted':
                daemon.state['epoch'] = 2
                daemon.state['run'].update(control_generation=1, desired='cancelled')
        daemon.on_observation = takeover
        with patch('orchestrator.runner.build_command') as launch:
            self.assertEqual(self.runner(daemon).execute(), 2)
            launch.assert_not_called()
        self.assertEqual(daemon.observations[-1]['kind'], 'uncertain')
        self.assertFalse(any(o['kind'] in ('finished', 'control') for o in daemon.observations))

    def test_pause_and_resume_keep_observed_and_confirmed_distinct(self):
        daemon = FakeDaemon(self.home, {'progress': ['started'], 'delay': 0.5, 'result': 'resumed'})
        def controls(message):
            if message['kind'] == 'progress' and daemon.state['run']['control_generation'] == 0:
                daemon.state['run'].update(control_generation=1, desired='paused')
            if message['kind'] == 'control' and message['body']['observed'] == 'paused':
                daemon.state['run'].update(control_generation=2, desired='running')
        daemon.on_observation = controls
        self.assertEqual(self.runner(daemon).execute(), 0)
        observed = [o['body'] for o in daemon.observations if o['kind'] == 'control']
        self.assertEqual([o['observed'] for o in observed], ['paused', 'running'])
        for item in observed:
            self.assertEqual(item['outcome'], item['detail']['outcome'])

    def test_finished_waits_for_observed_orphan_child(self):
        daemon = FakeDaemon(self.home)
        program = '''import subprocess, sys, time, json, uuid
subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(0.6)'],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(json.dumps({'type':'thread.started','thread_id':str(uuid.uuid4())}), flush=True)
time.sleep(0.15)
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ready'}}), flush=True)
print(json.dumps({'type':'turn.completed'}), flush=True)
'''
        started = time.monotonic()
        with patch('orchestrator.runner.build_command', return_value=[sys.executable, '-c', program]):
            self.assertEqual(self.runner(daemon).execute(), 0)
        self.assertGreaterEqual(time.monotonic() - started, 0.5)
        self.assertEqual(daemon.observations[-1]['body']['result'], 'ready')

    def test_zero_exit_without_terminal_result_is_failure(self):
        daemon = FakeDaemon(self.home)
        program = 'print(\'{"type":"item.completed","item":{"type":"agent_message","text":"progress only"}}\')'
        with patch('orchestrator.runner.build_command', return_value=[sys.executable, '-c', program]):
            self.assertEqual(self.runner(daemon).execute(), 0)
        self.assertIn('without a terminal result', daemon.observations[-1]['body']['error'])

    def test_durable_journal_mode(self):
        path = self.home / 'journal.json'
        durable_json(path, {'phase': 'accepted'})
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(path.read_text()), {'phase': 'accepted'})

    def test_worker_reporting_prompt_has_exact_route_without_token(self):
        daemon = FakeDaemon(self.home)
        runner = self.runner(daemon)
        prompt = assignment_prompt(daemon.state['assignment'], daemon.state['run'], runner.protocol(daemon.state))
        self.assertIn(str(self.home / 'credentials' / 'session-test.json'), prompt)
        self.assertIn('request report --body', prompt)
        self.assertIn('request artifact --body', prompt)
        self.assertIn('"run_id": "run-test"', prompt)
        self.assertIn('"priority": "urgent"', prompt)
        self.assertIn('coalescing_key', prompt)
        self.assertIn('This assignment is read-only', prompt)
        self.assertNotIn('test-token', prompt)

    def test_interactive_grok_without_pane_does_not_exec(self):
        daemon = FakeDaemon(self.home)
        daemon.state['session']['config'] = json.dumps({'adapter': 'grok', 'model': 'grok-4.6', 'effort': 'high'})
        with patch('orchestrator.runner.build_command') as exec_cmd:
            self.assertEqual(self.runner(daemon).execute(), 0)
            exec_cmd.assert_not_called()
        finished = next(o for o in reversed(daemon.observations) if o['kind'] == 'finished')
        self.assertIn('tmux pane', finished['body']['error'])
        self.assertNotEqual(finished['body']['exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
