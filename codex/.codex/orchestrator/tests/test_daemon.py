"""Socket-level exercises with a real daemon, fake providers, and private tmux."""
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.client import call
from orchestrator.resources import ProcessIdentity
from orchestrator.store import Store, dump, now

PACKAGE = Path(__file__).resolve().parents[1]


class CLITmuxTests(unittest.TestCase):
    def test_current_pane_resolves_exact_socket_and_window(self):
        from orchestrator.cli import parser, tmux_config
        args = parser().parse_args(['init', 'objective'])
        response = subprocess.CompletedProcess([], 0, stdout='/tmp/exact.sock\t@12\n')
        with patch.dict(os.environ, {'TMUX':'/tmp/current.sock,123,0', 'TMUX_PANE':'%9'}, clear=True), patch('orchestrator.cli.subprocess.run', return_value=response) as command:
            self.assertEqual(tmux_config(args), {'tmux_socket':'/tmp/exact.sock', 'tmux_window':'@12'})
        self.assertEqual(command.call_args.args[0], ['tmux','-S','/tmp/current.sock','display-message','-p','-t','%9','#{socket_path}\t#{window_id}'])

    def test_headless_never_queries_tmux(self):
        from orchestrator.cli import parser, tmux_config
        args = parser().parse_args(['init','objective','--headless'])
        with patch.dict(os.environ, {'TMUX':'/tmp/current.sock,123,0', 'TMUX_PANE':'%9'}), patch('orchestrator.cli.subprocess.run') as command:
            self.assertEqual(tmux_config(args), {})
            command.assert_not_called()

    def test_explicit_targets_override_current_window(self):
        from orchestrator.cli import parser, tmux_config
        args = parser().parse_args(['init','objective','--tmux-socket','/tmp/other.sock','--tmux-window','@42'])
        with patch('orchestrator.cli.subprocess.run') as command:
            self.assertEqual(tmux_config(args), {'tmux_socket':'/tmp/other.sock','tmux_window':'@42'})
            command.assert_not_called()


class DaemonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='orch-test-', dir='/tmp')
        self.home = Path(self.temporary.name)
        self.log = (self.home / 'daemon.log').open('ab')
        self.daemon = None
        self.credentials = None
        self.env = dict(os.environ, PYTHONPATH=str(PACKAGE))
        self.extra_processes = []
        self.start()

    def start(self):
        self.daemon = subprocess.Popen([sys.executable, '-m', 'orchestrator.daemon', '--home', str(self.home)],
                                       env=self.env, stdout=self.log, stderr=self.log)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.daemon.poll() is not None:
                self.fail((self.home / 'daemon.log').read_text())
            try:
                if call(self.home, {'op':'ping'}, timeout=.3)['pid'] == self.daemon.pid:
                    return
            except (OSError, RuntimeError):
                pass
            time.sleep(.03)
        self.fail('Daemon did not start: ' + (self.home / 'daemon.log').read_text())

    def stop(self):
        if self.daemon and self.daemon.poll() is None:
            self.daemon.terminate()
            self.daemon.wait(timeout=5)

    def tearDown(self):
        identities = []
        try:
            if self.credentials and self.daemon.poll() is None:
                status = self.status()
                for run in status['runs']:
                    if run['runner_pid']:
                        identities.append((run['runner_pid'], run['runner_identity']))
                    if not run['released']:
                        try:
                            self.command('control', {'run_id':run['id'], 'action':'cancel'})
                        except RuntimeError:
                            pass
                for resource in status['resources']:
                    if resource['kind'] == 'process':
                        detail = json.loads(resource['detail'])
                        identities.append((detail['pid'], detail['start_identity']))
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and any(not r['released'] for r in self.status()['runs']):
                    time.sleep(.05)
            for process in self.extra_processes:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=3)
            for pid, birth in identities:
                if ProcessIdentity.matches(pid, birth) and ProcessIdentity.state(pid, birth) != 'Z':
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        finally:
            self.stop()
            self.log.close()
            self.temporary.cleanup()

    def init(self, config=None):
        self.credentials = call(self.home, {'op':'init', 'objective':'Offline validation', 'config':config or {}})
        return self.credentials

    def command(self, kind, body, request_id=None):
        return call(self.home, {'op':'command', 'token':self.credentials['token'], 'epoch':self.credentials['epoch'],
                               'request_id':request_id or str(uuid.uuid4()), 'kind':kind, 'body':body})

    def status(self):
        return call(self.home, {'op':'read', 'token':self.credentials['token'], 'view':'status'})

    def history(self, **filters):
        return call(self.home, {'op':'read', 'token':self.credentials['token'], 'view':'history', 'filters':filters})

    def until(self, predicate, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(.05)
        self.fail('Timed out; status=' + json.dumps(self.status()) + '\n' + (self.home/'daemon.log').read_text())

    def worker(self, name='worker'):
        return self.command('register', {'name':name, 'adapter':'fake'})

    def task(self, name, delay=0):
        script = {'progress':['progress-visible-' + name], 'delay':delay, 'result':'result-' + name}
        return self.command('task', {'task_id':name, 'spec':{
            'objective':'Do fixture work\nFAKE_SCRIPT=' + json.dumps(script),
            'expected_output':'fixture result', 'criteria':[], 'cwd':str(self.home), 'write':False}})

    def assign(self, task, worker):
        return self.command('assign', {'task_id':task, 'session_id':worker['session_id']})['run_id']

    def finished(self, run_id):
        return self.until(lambda: next((r for r in self.status()['runs'] if r['id']==run_id and r['released']), None))

    def worker_command(self, worker, kind, body):
        return call(self.home, {'op':'command','token':worker['token'],'epoch':self.credentials['epoch'],
                               'request_id':str(uuid.uuid4()),'kind':kind,'body':body})

    def inbox(self, credentials=None):
        return call(self.home, {'op':'read','token':(credentials or self.credentials)['token'],'view':'inbox'})

    def test_bootstrap_request_retries_return_same_private_credential(self):
        request = {'op':'init','objective':'Retry bootstrap','request_id':'bootstrap-id','config':{}}
        self.credentials = call(self.home, request)
        self.assertEqual(self.credentials, call(self.home, request))
        with self.assertRaisesRegex(RuntimeError, 'different content'):
            call(self.home, dict(request, objective='Changed objective'))
        self.stop()
        self.start()
        self.assertEqual(self.credentials, call(self.home, request))
        path = self.home/'credentials'/(self.credentials['session_id']+'.json')
        self.assertEqual(json.loads(path.read_text()), self.credentials)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(self.history(type='team_created')), 1)

    def test_urgent_conflict_pause_replan_cancel_and_reassign(self):
        self.init()
        a, b = self.worker('affected'), self.worker('unrelated')
        self.task('affected', delay=8)
        self.task('unrelated', delay=.6)
        old_run, other_run = self.assign('affected',a), self.assign('unrelated',b)
        self.until(lambda: any(r['id']==old_run and r['health']=='running' for r in self.status()['runs']))
        issue = self.worker_command(a, 'report', {'run_id':old_run,'type':'conflict','text':'Contract changed during execution','priority':'urgent'})
        delivery = next(d for d in self.inbox() if d['event_id']==issue['event_id'])
        self.command('ack', {'delivery_id':delivery['id']})
        self.assertTrue(any(d['id']==delivery['id'] for d in self.inbox()), 'Ack incorrectly resolved urgent issue')
        self.assertEqual(next(i for i in self.status()['issues'] if i['id']==issue['issue_id'])['state'], 'open')
        control = self.command('control', {'run_id':old_run,'action':'pause'})
        stopped = self.until(lambda: next((r for r in self.status()['runs'] if r['id']==old_run and r['observed']=='paused'), None))
        identity = json.loads(next(r for r in self.status()['resources'] if r['kind']=='process' and r['owner_run']==old_run)['detail'])
        self.assertEqual(ProcessIdentity.state(identity['pid'],identity['start_identity']), 'T')
        observation = json.loads(self.history(run_id=old_run,type='runner_control')[-1]['body'])
        self.assertEqual(observation['observed'], 'paused')
        if sys.platform == 'darwin':
            self.assertEqual(observation['outcome'], 'uncertain')
            self.assertLess(stopped['confirmed_generation'], control['generation'])
        self.finished(other_run)
        spec = {'objective':'Return revised contract','expected_output':'Revised evidence','criteria':[],'cwd':str(self.home),'write':False}
        revision = self.command('replan', {'reason':'Urgent contract correction','tasks':{'affected':spec}})['revision']
        self.command('control', {'run_id':old_run,'action':'cancel'})
        cancelled = self.finished(old_run)
        self.assertEqual(cancelled['outcome'], 'cancelled')
        self.assertIn(ProcessIdentity.state(identity['pid'],identity['start_identity']), ('Z','exited','replaced'))
        self.command('resolve', {'issue_id':issue['issue_id'],'resolution':'Revised contract and reaped affected execution'})
        self.command('retry', {'task_id':'affected','reason':'Execute revised contract'})
        retry = self.assign('affected',a)
        done = self.finished(retry)
        self.assertEqual(done['revision'], revision)
        self.assertEqual(done['session_id'], a['session_id'])
        self.assertTrue(done['result_event'])
        self.command('review', {'run_id':retry,'decision':'accept','reason':'Inspected revised artifact','checks':[]})
        self.command('review', {'run_id':other_run,'decision':'accept','reason':'Inspected unchanged independent result',
                                'compatible':True,'compatibility_reason':'Independent task uses no changed contract','checks':[]})
        self.command('finish', {})

    def test_busy_worker_publication_fanout_has_separate_followup_acknowledgments(self):
        self.init()
        a, b = self.worker('a'), self.worker('b')
        self.task('publish-a', delay=2)
        self.task('publish-b', delay=2)
        ra, rb = self.assign('publish-a',a), self.assign('publish-b',b)
        self.until(lambda: all(r['health']=='running' for r in self.status()['runs']))
        proposed = self.worker_command(a,'report',{'run_id':ra,'type':'proposal','text':'Apply versioned contract'})
        publication = self.command('publish',{'proposal_event':proposed['event_id'],'recipients':[a['agent_id'],b['agent_id']]})
        self.assertEqual(len(set(publication['deliveries'])),2)
        for worker in (a,b):
            pending = [d for d in self.inbox(worker) if d['event_id']==publication['event_id']]
            self.assertEqual(len(pending),1)
            self.assertIsNone(pending[0]['acknowledged_at'])
        self.finished(ra)
        self.finished(rb)
        ack_ids = [json.loads(e['body'])['delivery_id'] for e in self.history(type='acknowledged')]
        for delivery in publication['deliveries']:
            self.assertEqual(ack_ids.count(delivery),1)
        for rid,worker in ((ra,a),(rb,b)):
            journal = json.loads((self.home/'runs'/rid/'journal.json').read_text())
            self.assertEqual(journal['turn'],2)
            self.assertFalse(any(d['event_id']==publication['event_id'] for d in self.inbox(worker)))

    def test_committed_observation_lost_ack_replays_once_after_crash(self):
        self.init()
        worker = self.worker()
        self.task('lost-ack')
        rid = self.assign('lost-ack',worker)
        done = self.finished(rid)
        self.until(lambda: ProcessIdentity.state(done['runner_pid'],done['runner_identity']) in ('exited','Z','replaced'))
        self.daemon.kill()
        self.daemon.wait(timeout=3)
        # Reconstruct the durable boundary: server committed, runner still has
        # the same observation in its outbox because the response was lost.
        with sqlite3.connect(self.home/'state.sqlite3') as database:
            payload = database.execute("SELECT payload FROM command_requests WHERE json_extract(payload,'$.op')='runner_observe' AND json_extract(payload,'$.run_id')=? AND json_extract(payload,'$.kind')='progress' LIMIT 1", (rid,)).fetchone()[0]
        journal_path = self.home/'runs'/rid/'journal.json'
        journal = json.loads(journal_path.read_text())
        journal['outbox'] = [json.loads(payload)]
        journal_path.write_text(json.dumps(journal))
        self.start()
        count = len(self.history(run_id=rid,type='runner_progress'))
        token_path = self.home/'credentials'/(worker['session_id']+'.json')
        process = subprocess.Popen([sys.executable,'-m','orchestrator.runner','--home',str(self.home),'--run',rid,'--token-file',str(token_path)],
                                   env=self.env,stdout=self.log,stderr=self.log)
        self.extra_processes.append(process)
        self.assertEqual(process.wait(timeout=8),0)
        self.assertEqual(json.loads(journal_path.read_text())['outbox'],[])
        self.assertEqual(len(self.history(run_id=rid,type='runner_progress')),count)
        self.assertEqual(len(self.history(run_id=rid,type='runner_started')),1)

    def test_async_worktree_operation_enforces_exclusive_writing_scope(self):
        self.init()
        repo, tree = self.home/'repo', self.home/'worktree'
        repo.mkdir()
        def git(*args):
            return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
        git('init','-q')
        git('config','user.name','Fixture')
        git('config','user.email','fixture@example.invalid')
        (repo/'tracked').write_text('original')
        git('add','tracked')
        git('commit','-qm','fixture')
        head = git('rev-parse','HEAD')
        operation = self.command('worktree',{'repo':str(repo),'path':str(tree),'branch':'isolated','ref':head})
        observed = self.until(lambda: next((o for o in self.status()['operations'] if o['id']==operation['operation_id'] and o['state']=='succeeded'),None))
        self.assertEqual(json.loads(observed['outcome'])['base'],head)
        a,b = self.worker('writer-a'),self.worker('writer-b')
        spec = {'objective':'Use exclusive scope\nFAKE_SCRIPT={"progress":["writing scope held"],"delay":1,"result":"scope checked"}',
                'expected_output':'scope evidence','criteria':[],'cwd':str(tree),'write':True}
        for task in ('write-a','write-b'):
            self.command('task',{'task_id':task,'spec':spec})
        first = self.assign('write-a',a)
        with self.assertRaisesRegex(RuntimeError,'idle registered isolated worktree'):
            self.assign('write-b',b)
        self.finished(first)
        self.finished(self.assign('write-b',b))
        self.assertEqual((repo/'tracked').read_text(),'original')
        self.assertEqual(git('rev-parse','HEAD'),head)
        resource = next(r for r in self.status()['resources'] if r['kind']=='worktree')
        self.assertEqual(resource['state'],'idle')
        self.assertIsNone(resource['owner_run'])

    def test_two_tasks_revision_and_evidence_acceptance(self):
        self.init()
        a, b = self.worker('a'), self.worker('b')
        self.task('task-a')
        self.task('task-b')
        run_a, run_b = self.assign('task-a', a), self.assign('task-b', b)
        first, second = self.finished(run_a), self.finished(run_b)
        self.assertTrue(first['result_event'])
        self.assertTrue(second['result_event'])
        self.assertTrue(all(t['state']=='awaiting_review' for t in self.status()['tasks']))
        self.command('review', {'run_id':run_a, 'decision':'revise', 'reason':'Need a second attempt'})
        revised = self.assign('task-a', a)
        self.finished(revised)
        for rid in (revised, run_b):
            result = next(e for e in self.history(run_id=rid) if e['type']=='result')
            self.assertTrue(json.loads(result['body'])['artifact_ids'])
            self.command('review', {'run_id':rid, 'decision':'accept', 'reason':'Inspected fixture artifact', 'checks':[]})
        self.command('finish', {})
        self.assertEqual(self.status()['team']['state'], 'completed')
        self.assertEqual(len(self.status()['runs']), 3)
        self.assertEqual(len(self.history(type='assignment')), 3)

    def test_daemon_restart_preserves_live_runner_and_request_deduplication(self):
        self.init()
        worker = self.worker()
        self.task('long', delay=2)
        body = {'task_id':'long', 'session_id':worker['session_id']}
        receipt = self.command('assign', body, 'same-assignment')
        rid = receipt['run_id']
        live = self.until(lambda: next((r for r in self.status()['runs'] if r['id']==rid and r['health']=='running'), None))
        self.stop()
        self.start()
        self.assertEqual(receipt, self.command('assign', body, 'same-assignment'))
        done = self.finished(rid)
        self.assertEqual(done['runner_pid'], live['runner_pid'])
        self.assertEqual(done['runner_identity'], live['runner_identity'])
        self.assertEqual(len(self.history(type='assignment')), 1)
        self.assertEqual(len(self.history(type='runner_started')), 1)

    def test_ambiguous_launch_journal_is_not_replayed(self):
        self.init()
        worker = self.worker()
        self.task('ambiguous')
        self.stop()
        # Seed the exact crash boundary while the single writer is stopped.
        store = Store(self.home)
        receipt = store.command(self.credentials['token'], 'assign-before-crash', 1, 'assign',
                                {'task_id':'ambiguous', 'session_id':worker['session_id']})
        rid = receipt['run_id']
        with store.transaction():
            store.update('operations', receipt['operation_id'], state='running', updated=now())
        store.db.close()
        directory = self.home / 'runs' / rid
        directory.mkdir(parents=True)
        (directory/'journal.json').write_text(json.dumps({'phase':'launch_intent','outbox':[], 'acked_messages':[], 'turn':1}))
        self.start()
        token_path = self.home/'credentials'/(worker['session_id']+'.json')
        process = subprocess.Popen([sys.executable, '-m', 'orchestrator.runner', '--home', str(self.home),
                                    '--run', rid, '--token-file', str(token_path)], env=self.env, stdout=self.log, stderr=self.log)
        self.extra_processes.append(process)
        process.wait(timeout=8)
        self.assertNotEqual(process.returncode, 0)
        journal = json.loads((directory/'journal.json').read_text())
        self.assertEqual(journal['phase'], 'uncertain')
        self.assertFalse((directory/'provider.log').exists(), 'Ambiguous provider was replayed')
        self.assertFalse(journal['outbox'], 'Daemon rejected recovery observation')
        self.assertTrue(any(e['type'] in ('runner_uncertain','runner_control') for e in self.history(run_id=rid)))

    @unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
    def test_full_pane_queue_survives_liveness_threshold_and_reuses_idle_pane(self):
        socket_path = str(self.home/'queue-tmux.sock')
        def tmux(*args):
            return subprocess.check_output(['tmux','-S',socket_path,*args], text=True).strip()
        tmux('-f','/dev/null','new-session','-d','-s','test','-x','180','-y','60')
        try:
            window = tmux('display-message','-p','#{window_id}')
            self.init({'tmux_socket':socket_path,'tmux_window':window,'max_panes':1})
            a, b = self.worker('a'), self.worker('b')
            self.task('occupy-pane', delay=6.5)
            self.task('queued-pane')
            first = self.assign('occupy-pane',a)
            self.until(lambda: any(r['id']==first and r['health']=='running' for r in self.status()['runs']))
            original_pane = next(p.split()[0] for p in tmux('list-panes','-t',window,'-F','#{pane_id} #{@orch_purpose}').splitlines() if p.endswith(' worker'))
            second = self.assign('queued-pane',b)
            started = time.monotonic()
            self.until(lambda: time.monotonic()-started > 5.3, timeout=7)
            queued = next(r for r in self.status()['runs'] if r['id']==second)
            self.assertIsNone(queued['runner_pid'])
            self.assertNotEqual(queued['outcome'], 'uncertain')
            self.finished(first)
            self.finished(second)
            panes = [p.split() for p in tmux('list-panes','-t',window,'-F','#{pane_id} #{@orch_agent} #{@orch_purpose}').splitlines() if p.endswith(' worker')]
            self.assertEqual(panes, [[original_pane,b['agent_id'],'worker']])
        finally:
            tmux('kill-server')

    @unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
    def test_private_tmux_worker_output_status_and_focus(self):
        socket_path = str(self.home/'tmux.sock')
        def tmux(*args):
            return subprocess.check_output(['tmux','-S',socket_path,*args], text=True).strip()
        tmux('-f','/dev/null','new-session','-d','-s','test','-x','180','-y','60')
        try:
            window = tmux('display-message','-p','#{window_id}')
            focus = tmux('display-message','-p','#{pane_id}')
            self.init({'tmux_socket':socket_path,'tmux_window':window})
            worker = self.worker()
            self.task('visible', delay=.5)
            rid = self.assign('visible',worker)
            self.finished(rid)
            panes = tmux('list-panes','-t',window,'-F','#{pane_id} #{@orch_team} #{@orch_agent} #{@orch_purpose}').splitlines()
            worker_pane = next(p.split()[0] for p in panes if p.endswith(' worker'))
            self.until(lambda: 'progress-visible-visible' in tmux('capture-pane','-p','-t',worker_pane))
            self.assertTrue(any(p.endswith(' status') for p in panes), 'Runtime/status pane absent')
            self.assertEqual(focus, tmux('display-message','-p','#{pane_id}'))
            self.command('review', {'run_id':rid,'decision':'revise','reason':'Verify pane follows new attempt'})
            revised = self.assign('visible',worker)
            self.finished(revised)
            self.until(lambda: revised in tmux('capture-pane','-p','-t',worker_pane))
        finally:
            tmux('kill-server')


if __name__ == '__main__':
    unittest.main()
