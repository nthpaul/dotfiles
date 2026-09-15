import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.preflight import fingerprint, run_commands


class PreflightTests(unittest.TestCase):
    def git(self, repo, *args):
        return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()

    def repo(self, directory):
        repo = Path(directory) / 'repo'
        repo.mkdir()
        self.git(repo, 'init', '-q')
        self.git(repo, 'config', 'user.email', 'test@example.invalid')
        self.git(repo, 'config', 'user.name', 'Test')
        (repo / 'tracked.py').write_text('print(1)\n')
        self.git(repo, 'add', 'tracked.py')
        self.git(repo, 'commit', '-qm', 'base')
        return repo

    def test_dirty_and_untracked_bytes_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repo(directory)
            commands = [{'argv': ['true']}]
            clean, _ = fingerprint(repo, commands, ['tracked.py'], {})
            (repo / 'tracked.py').write_text('print(2)\n')
            dirty, payload = fingerprint(repo, commands, ['tracked.py'], {})
            self.assertNotEqual(clean, dirty)
            self.assertIn('tracked.py', payload['code']['files'])
            (repo / 'extra.py').write_text('secret\n')
            untracked, _ = fingerprint(repo, commands, ['.'], {})
            self.assertNotEqual(dirty, untracked)

    def test_command_scope_env_are_part_of_key(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repo(directory)
            a, _ = fingerprint(repo, [{'argv': ['true']}], [], {'A': '1'})
            b, _ = fingerprint(repo, [{'argv': ['false']}], [], {'A': '1'})
            c, _ = fingerprint(repo, [{'argv': ['true']}], ['tracked.py'], {'A': '1'})
            d, _ = fingerprint(repo, [{'argv': ['true']}], [], {'A': '2'})
            self.assertEqual(len({a, b, c, d}), 4)

    def test_reuse_only_when_commands_pass(self):
        ok, outputs = run_commands([{'argv': ['true']}])
        self.assertTrue(ok)
        self.assertEqual(outputs[0]['exit_code'], 0)
        bad, failed = run_commands([{'argv': ['false']}])
        self.assertFalse(bad)
        self.assertEqual(failed[0]['exit_code'], 1)


if __name__ == '__main__':
    unittest.main()
