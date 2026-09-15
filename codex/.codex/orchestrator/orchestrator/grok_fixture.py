"""Offline wire fixture, selected explicitly and never as a fallback."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
parser = argparse.ArgumentParser()
parser.add_argument('--session-id', required=True)
parser.add_argument('--prompt-file', type=Path, required=True)
args = parser.parse_args()
spec = {}
for line in args.prompt_file.read_text().splitlines():
    if line.startswith('FAKE_SCRIPT='):
        spec = json.loads(line.split('=', 1)[1])
print(json.dumps({'type': 'system', 'session_id': args.session_id}), flush=True)
if spec.get('child_seconds'):
    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(' + str(float(spec['child_seconds'])) + ')'])
time.sleep(spec.get('delay', 0))
if spec.get('progress'):
    print(json.dumps({'type': 'stream_event', 'event': {'delta': {'type': 'text_delta', 'text': spec['progress']}}}), flush=True)
report = spec.get('report', {'outcome': 'completed', 'summary': 'Fixture complete',
                           'changes': [], 'validation': [], 'unresolved': [], 'artifacts': []})
if not spec.get('missing_result'):
    print(json.dumps({'type': 'result', 'subtype': 'error' if spec.get('error') else 'success',
                      'is_error': bool(spec.get('error')), 'result': spec.get('error') or json.dumps(report)}), flush=True)
sys.exit(spec.get('exit_code', 0))
