import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from orchestrator.grok_bridge import Bridge


class GrokApiTests(unittest.TestCase):
    def test_cli_lists_saved_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-m', 'orchestrator.grok_api', '--home', directory, 'inspect'],
                                    input='{}', text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {'runs': []})

    def test_mcp_disconnect_reconnect_and_validation(self):
        async def exercise(directory):
            bridge = Bridge(Path(directory) / 'state')
            run = bridge.spawn('FAKE_SCRIPT={"delay":0.3}', directory, 'mcp', adapter='fake')
            env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1])}
            params = StdioServerParameters(command=sys.executable,
                args=['-m', 'orchestrator.grok_api', '--home', str(bridge.home), 'mcp'], env=env)
            async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
                await client.initialize()
                tools = await client.list_tools()
                self.assertEqual({t.name for t in tools.tools}, {'spawn', 'wait', 'inspect', 'resume', 'cancel'})
                bad = await client.call_tool('wait', {'run_ids': [run['run_id']], 'timeout': 31})
                self.assertTrue(bad.isError)
            async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
                await client.initialize()
                done = await client.call_tool('wait', {'run_ids': [run['run_id']], 'timeout': 10})
                self.assertFalse(done.isError)
                result = json.loads(done.content[0].text)
                self.assertEqual(result['results'][0]['state'], 'completed')
                history = await client.call_tool('inspect', {'run_id': run['run_id'], 'limit': 1})
                self.assertEqual(json.loads(history.content[0].text)['history'][0]['role'], 'user')
        with tempfile.TemporaryDirectory() as directory:
            asyncio.run(exercise(directory))
