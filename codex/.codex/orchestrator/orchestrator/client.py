"""Small request/response protocol over a mode-0600 local Unix socket."""
import json
import socket
from pathlib import Path

MAX_MESSAGE = 8 * 1024 * 1024


def call(home, message, timeout=30):
    path = str(Path(home).expanduser().resolve() / 'runtime.sock')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(path)
        payload = json.dumps(message, separators=(',', ':'), allow_nan=False).encode() + b'\n'
        if len(payload) > MAX_MESSAGE:
            raise ValueError('Request too large; use an artifact file')
        connection.sendall(payload)
        with connection.makefile('rb') as stream:
            line = stream.readline(MAX_MESSAGE+1)
        if not line or len(line) > MAX_MESSAGE:
            raise RuntimeError('Runtime returned an incomplete or oversized response')
        response = json.loads(line)
        if not response.get('ok'):
            raise RuntimeError(response.get('error', 'Runtime request failed'))
        return response['result']
