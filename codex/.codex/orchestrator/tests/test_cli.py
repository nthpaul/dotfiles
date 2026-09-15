"""User-facing startup and local capability checks; no default runtime is touched."""
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.cli import doctor
from orchestrator.client import call
from orchestrator.resources import ProcessIdentity

PACKAGE = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_doctor_missing_optional_tools_is_read_only_and_successful(self):
        with patch('orchestrator.cli.shutil.which', return_value=None):
            result = doctor()
        self.assertTrue(result['ready'])
        self.assertTrue(result['required']['sqlite']['json'])
        self.assertTrue(result['required']['sqlite']['strict'])
        self.assertTrue(all(not c['available'] and c['path'] is None for c in result['optional'].values()))
        with tempfile.TemporaryDirectory(prefix='orch-doctor-', dir='/tmp') as directory:
            home = Path(directory)/'must-not-be-created'
            env = dict(os.environ, PYTHONPATH=str(PACKAGE), OPENAI_API_KEY='secret-doctor-sentinel')
            response = subprocess.run([sys.executable,'-m','orchestrator','--home',str(home),'doctor'],
                                      env=env,capture_output=True,text=True,check=True,timeout=5)
            self.assertTrue(json.loads(response.stdout)['ready'])
            self.assertNotIn('secret-doctor-sentinel',response.stdout+response.stderr)
            self.assertFalse(home.exists())

    def test_doctor_required_sqlite_failure_blocks_readiness(self):
        with patch('orchestrator.cli.sqlite3.connect', side_effect=sqlite3.OperationalError('SQLite feature unavailable')):
            result = doctor()
        self.assertFalse(result['ready'])
        self.assertFalse(result['required']['sqlite']['available'])

    def test_start_detaches_and_reuses_existing_daemon(self):
        with tempfile.TemporaryDirectory(prefix='orch-start-', dir='/tmp') as directory:
            home = Path(directory)/'runtime'
            env = dict(os.environ,PYTHONPATH=str(PACKAGE))
            command = [sys.executable,'-m','orchestrator','--home',str(home),'start']
            identity = None
            try:
                first = subprocess.run(command,env=env,capture_output=True,text=True,check=True,timeout=8)
                started = json.loads(first.stdout)
                identity = ProcessIdentity.read(started['pid'])
                self.assertFalse(started['already_running'])
                self.assertTrue(ProcessIdentity.matches(started['pid'],identity['start_identity']))
                self.assertEqual(call(home,{'op':'ping'})['pid'],started['pid'])
                self.assertEqual(home.stat().st_mode & 0o777,0o700)
                self.assertEqual((home/'daemon.log').stat().st_mode & 0o777,0o600)
                second = subprocess.run(command,env=env,capture_output=True,text=True,check=True,timeout=3)
                existing = json.loads(second.stdout)
                self.assertTrue(existing['already_running'])
                self.assertEqual(existing['pid'],started['pid'])
                self.assertEqual(existing['socket'],str(home.resolve()/'runtime.sock'))
                self.assertEqual((home/'daemon.log').read_text().count('Runtime ready:'),1)
                credentials = call(home,{'op':'init','objective':'Startup test','request_id':'init-test','config':{}})
                call(home,{'op':'shutdown','token':credentials['token'],'epoch':credentials['epoch']})
                deadline = time.monotonic()+5
                while (home/'runtime.sock').exists() and time.monotonic()<deadline:
                    time.sleep(.03)
                self.assertFalse((home/'runtime.sock').exists())
            finally:
                if identity and ProcessIdentity.matches(identity['pid'],identity['start_identity']):
                    try:
                        os.kill(identity['pid'],signal.SIGTERM)
                    except ProcessLookupError:
                        pass

    def test_register_personal_default_is_grok_high_without_mode(self):
        from orchestrator.cli import parser, register_body
        self.assertEqual(register_body(parser().parse_args(['register', 'w'])),
                         {'name': 'w', 'adapter': 'grok', 'model': 'grok-4.6', 'effort': 'high'})
        self.assertEqual(register_body(parser().parse_args(['register', 'w', '--adapter', 'codex'])),
                         {'name': 'w', 'adapter': 'codex'})
        self.assertEqual(register_body(parser().parse_args(['register', 'w', '--adapter', 'fake'])),
                         {'name': 'w', 'adapter': 'fake'})
        self.assertEqual(register_body(parser().parse_args(['register', 'w', '--mode', 'exec']))['mode'], 'exec')


if __name__ == '__main__':
    unittest.main()
