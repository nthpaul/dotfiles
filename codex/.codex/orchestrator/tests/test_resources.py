import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.resources import ProcessIdentity, control_tree, TmuxManager, WorktreeManager, IntegrationManager


class ProcessTests(unittest.TestCase):
    def test_birth_identity_and_recycled_pid_refusal(self):
        child = subprocess.Popen(['sleep', '30'])
        try:
            identity = ProcessIdentity.read(child.pid)
            self.assertTrue(ProcessIdentity.matches(child.pid, identity['start_identity']))
            self.assertFalse(ProcessIdentity.matches(child.pid, 'wrong-birth'))
            with patch('orchestrator.resources.os.kill') as kill:
                result = control_tree(child.pid, 'wrong-birth', 'cancel')
            self.assertEqual(result['outcome'], 'uncertain')
            kill.assert_not_called()
            self.assertIsNone(child.poll())
        finally:
            child.kill()
            child.wait()

    def test_pause_resume_cancel_tool_child(self):
        with tempfile.TemporaryDirectory() as directory:
            pidfile = Path(directory) / 'child'
            script = ('import subprocess,time,pathlib; '
                      'p=subprocess.Popen(["sleep","30"]); '
                      f'pathlib.Path({str(pidfile)!r}).write_text(str(p.pid)); '
                      'p.wait()')
            child = subprocess.Popen([sys.executable, '-c', script])
            tool = None
            try:
                deadline = time.monotonic() + 5
                while not pidfile.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                tool = int(pidfile.read_text())
                identity = ProcessIdentity.read(child.pid)
                paused = control_tree(child.pid, identity['start_identity'], 'pause')
                self.assertIn(tool, paused['states'])
                self.assertTrue(all(s == 'T' for s in paused['states'].values()), paused)
                resumed = control_tree(child.pid, identity['start_identity'], 'resume')
                self.assertTrue(all(s not in ('T', 't') for s in resumed['states'].values()), resumed)
                cancelled = control_tree(child.pid, identity['start_identity'], 'cancel')
                self.assertTrue(all(s in ('exited', 'Z') for s in cancelled['states'].values()), cancelled)
                child.wait(timeout=5)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
                if tool:
                    try:
                        os.kill(tool, 9)
                    except ProcessLookupError:
                        pass


@unittest.skipUnless(shutil.which('tmux'), 'tmux unavailable')
class TmuxTests(unittest.TestCase):
    def test_owned_panes_reuse_queue_focus_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            socket = str(Path(directory) / 'tmux.sock')
            def tmux(*args):
                return subprocess.check_output(['tmux', '-S', socket, *args], text=True).strip()
            tmux('-f', '/dev/null', 'new-session', '-d', '-s', 'test', '-x', '180', '-y', '60')
            try:
                window = tmux('display-message', '-p', '#{window_id}')
                focused = tmux('display-message', '-p', '#{pane_id}')
                manager = TmuxManager(socket, window, 'team', max_panes=1)
                first = manager.ensure_pane('a', ['sleep', '30'])
                self.assertEqual(first, manager.ensure_pane('a', ['sleep', '30']))
                self.assertIsNone(manager.ensure_pane('b', ['sleep', '30']))
                self.assertEqual(focused, tmux('display-message', '-p', '#{pane_id}'))
                self.assertFalse(manager.cleanup(first['pane'], 'wrong-agent'))
                self.assertFalse(manager.cleanup(focused, 'a'))
                self.assertTrue(manager.cleanup(first['pane'], 'a'))
                self.assertEqual(focused, tmux('display-message', '-p', '#{pane_id}'))
                quick = manager.ensure_pane('quick', ['true'])
                deadline = time.monotonic() + 5
                while tmux('display-message', '-p', '-t', quick['pane'], '#{pane_dead}') != '1' and time.monotonic() < deadline:
                    time.sleep(.02)
                reused = manager.ensure_pane('replacement', ['sleep', '30'])
                self.assertEqual(quick['pane'], reused['pane'])
                self.assertFalse(manager.cleanup(reused['pane'], 'quick'))
                self.assertTrue(manager.cleanup(reused['pane'], 'replacement'))
            finally:
                tmux('kill-server')


class GitTests(unittest.TestCase):
    def test_create_isolated_worktree_preserves_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, worktree = Path(directory) / 'repo', Path(directory) / 'worker'
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()
            git('init', '-q')
            git('config', 'user.email', 'test@example.invalid')
            git('config', 'user.name', 'Test')
            (repo / 'file').write_text('base')
            git('add', 'file')
            git('commit', '-qm', 'fixture')
            head = git('rev-parse', 'HEAD')
            identity = WorktreeManager.create(repo, worktree, 'worker', head)
            self.assertEqual(identity['base'], head)
            (worktree / 'file').write_text('worker change')
            self.assertEqual((repo / 'file').read_text(), 'base')
            self.assertEqual(git('rev-parse', 'HEAD'), head)

    @unittest.skipUnless(shutil.which('gt'), 'Graphite CLI unavailable')
    def test_graphite_creates_two_buildable_commits_in_isolated_worktree(self):
        with tempfile.TemporaryDirectory(prefix='orch-graphite-', dir='/tmp') as directory:
            repo, tree = Path(directory)/'repo', Path(directory)/'integration'
            repo.mkdir()
            def git(*args, cwd=repo):
                return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
            git('init','-q','-b','main')
            git('config','user.email','fixture@example.invalid')
            git('config','user.name','Fixture')
            (repo/'check.py').write_text('assert 1 + 1 == 2\n')
            git('add','check.py')
            git('commit','-qm','fixture')
            base = git('rev-parse','HEAD')
            WorktreeManager.create(repo,tree,'integration','main')
            (tree/'first.py').write_text('assert 2 + 2 == 4\n')
            IntegrationManager.create(tree,'step-one','First independently passing step',trunk='main',parent='main')
            first = git('rev-parse','HEAD',cwd=tree)
            subprocess.run([sys.executable,'check.py'],cwd=tree,check=True)
            subprocess.run([sys.executable,'first.py'],cwd=tree,check=True)
            self.assertEqual(git('rev-parse','HEAD^',cwd=tree),base)
            (tree/'second.py').write_text('assert 3 + 3 == 6\n')
            IntegrationManager.create(tree,'step-two','Second independently passing step')
            subprocess.run([sys.executable,'check.py'],cwd=tree,check=True)
            subprocess.run([sys.executable,'first.py'],cwd=tree,check=True)
            subprocess.run([sys.executable,'second.py'],cwd=tree,check=True)
            self.assertEqual(git('rev-parse','HEAD^',cwd=tree),first)
            self.assertEqual(git('rev-list','--count','main..HEAD',cwd=tree),'2')
            self.assertEqual(git('rev-parse','HEAD'),base)
            self.assertFalse((repo/'first.py').exists())
            self.assertEqual(git('status','--porcelain',cwd=tree),'')

    def test_empty_ci_and_changed_head_are_not_success(self):
        with patch('orchestrator.resources.run', side_effect=['{"headRefOid":"a"}', '[]', '{"headRefOid":"a"}']):
            self.assertFalse(IntegrationManager.verify_ci('.', 1, 'a')['passed'])
        with patch('orchestrator.resources.run', return_value='{"headRefOid":"b"}'):
            self.assertFalse(IntegrationManager.verify_ci('.', 1, 'a')['passed'])
        with patch('orchestrator.resources.run', side_effect=['{"headRefOid":"a"}', '[{"bucket":"pass"}]', '{"headRefOid":"a"}']):
            self.assertTrue(IntegrationManager.verify_ci('.', 1, 'a')['passed'])


if __name__ == '__main__':
    unittest.main()
