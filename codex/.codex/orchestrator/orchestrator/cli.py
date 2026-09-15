"""Local daemon client. Credentials stay in owner-readable files, never stdout."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
import shutil
import sqlite3
import time
import tempfile
import uuid


def json_object(value):
    try:
        result = json.loads(Path(value[1:]).expanduser().read_text() if value.startswith('@') else value)
    except (OSError, ValueError) as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    if not isinstance(result, dict):
        raise argparse.ArgumentTypeError('Expected a JSON object')
    return result


def tmux_config(args):
    explicit = bool(args.tmux_socket or args.tmux_window)
    if args.headless:
        if explicit:
            raise ValueError('--headless cannot be combined with tmux targets')
        return {}
    if explicit:
        if not args.tmux_socket or not args.tmux_window:
            raise ValueError('Provide both --tmux-socket and --tmux-window')
        return {'tmux_socket': args.tmux_socket, 'tmux_window': args.tmux_window}
    server, pane = os.environ.get('TMUX'), os.environ.get('TMUX_PANE')
    if not server or not pane:
        return {}
    socket_path = server.rsplit(',', 2)[0]
    result = subprocess.run(['tmux', '-S', socket_path, 'display-message', '-p', '-t', pane,
                             '#{socket_path}\t#{window_id}'], capture_output=True, text=True, check=True)
    actual_socket, window = result.stdout.strip().split('\t')
    if not window.startswith('@'):
        raise ValueError('Could not determine exact current tmux window')
    return {'tmux_socket': actual_socket, 'tmux_window': window}


def save_credentials(path, value):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.credentials-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return str(path)


def doctor():
    """Inspect local capabilities without opening runtime state or invoking providers."""
    python = {'available': sys.version_info >= (3, 11), 'version': sys.version.split()[0]}
    sqlite = {'available': False, 'version': sqlite3.sqlite_version, 'json': False, 'strict': False}
    try:
        with sqlite3.connect(':memory:') as database:
            sqlite['json'] = database.execute("SELECT json_extract('{\"ok\":1}', '$.ok')").fetchone()[0] == 1
            database.execute('CREATE TABLE capability_test (value INTEGER) STRICT')
            sqlite['strict'] = True
            sqlite['available'] = sqlite['json'] and sqlite['strict']
    except sqlite3.Error as error:
        sqlite['error'] = str(error)
    capabilities = {}
    for name in ('codex', 'grok', 'tmux', 'git', 'gt', 'gh'):
        path = shutil.which(name)
        capabilities[name] = {'available': path is not None, 'path': path}
    return {'ready': python['available'] and sqlite['available'],
            'required': {'python': python, 'sqlite': sqlite}, 'optional': capabilities}


def start_daemon(home):
    """Start without a shell; the daemon lock resolves simultaneous starts."""
    from .client import call
    home = Path(home).expanduser().resolve()
    log_path = home / 'daemon.log'
    def description(ping, existing):
        return dict(ping, home=str(home), socket=str(home / 'runtime.sock'),
                    log=str(log_path), already_running=existing)
    try:
        return description(call(home, {'op': 'ping'}, timeout=.25), True)
    except (OSError, RuntimeError, ValueError):
        pass
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(home, 0o700)
    environment = dict(os.environ)
    package = str(Path(__file__).resolve().parents[1])
    environment['PYTHONPATH'] = package + (os.pathsep + environment['PYTHONPATH'] if environment.get('PYTHONPATH') else '')
    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'ab') as log:
        process = subprocess.Popen([sys.executable, '-m', 'orchestrator.daemon', '--home', str(home)],
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                   start_new_session=True, env=environment)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            ping = call(home, {'op': 'ping'}, timeout=min(.25, max(.01, deadline-time.monotonic())))
            # Reap a losing startup process if another starter won the daemon lock.
            process.poll()
            return description(ping, ping['pid'] != process.pid)
        except (OSError, RuntimeError, ValueError):
            process.poll()
            time.sleep(.05)
    raise RuntimeError(f'Daemon did not answer within 5 seconds; inspect {log_path} (startup PID {process.pid})')


def parser():
    root = argparse.ArgumentParser(description='Durable local orchestration runtime')
    def common(command, defaults=False):
        command.add_argument('--home', default='~/.codex/orchestration' if defaults else argparse.SUPPRESS,
                             help='Runtime state directory (default: ~/.codex/orchestration)')
        command.add_argument('--credentials', default=None if defaults else argparse.SUPPRESS,
                             help='Session credential JSON (default: HOME/coordinator.json)')
    common(root, True)
    commands = root.add_subparsers(dest='operation', required=True)
    for name in ('start', 'doctor', 'daemon', 'ping', 'shutdown'):
        common(commands.add_parser(name))
    init = commands.add_parser('init', help='Create a team and save coordinator credentials')
    common(init)
    init.add_argument('objective')
    init.add_argument('--team')
    init.add_argument('--request-id', help='Reuse this ID after a lost initialization response')
    init.add_argument('--coordinator-thread')
    init.add_argument('--tmux-socket')
    init.add_argument('--tmux-window')
    init.add_argument('--headless', action='store_true', help='Do not allocate tmux panes, even inside tmux')
    request = commands.add_parser('request', help='Submit a durable command; retry with the same request ID')
    common(request)
    request.add_argument('kind')
    request.add_argument('--body', type=json_object, default={})
    request.add_argument('--request-id', default=None)
    request.add_argument('--save-credentials', help='Destination for a returned session token')
    register = commands.add_parser('register', help='Register a worker and save its credentials')
    common(register)
    register.add_argument('name')
    register.add_argument('--adapter', choices=('codex', 'grok', 'fake'), default='codex')
    register.add_argument('--model', help='Override adapter default (Codex: gpt-6-astra)')
    register.add_argument('--effort', default='medium')
    register.add_argument('--request-id', default=None)
    register.add_argument('--save-credentials')
    for name in ('status', 'history', 'inbox', 'bulletin'):
        view = commands.add_parser(name)
        common(view)
        view.add_argument('--filters', type=json_object, default={})
        view.add_argument('--task-id')
        view.add_argument('--run-id')
        view.add_argument('--type')
        view.add_argument('--priority', choices=('normal', 'urgent'))
        view.add_argument('--after', type=int)
        view.add_argument('--limit', type=int)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    home = Path(args.home).expanduser().resolve()
    credentials_path = Path(args.credentials).expanduser() if args.credentials else home / 'coordinator.json'
    if args.operation == 'daemon':
        os.execv(sys.executable, [sys.executable, '-m', 'orchestrator.daemon', '--home', str(home)])
    from .client import call
    try:
        if args.operation in ('doctor', 'start'):
            result = doctor() if args.operation == 'doctor' else start_daemon(home)
            print(json.dumps(result, indent=2))
            return 0 if args.operation == 'start' or result['ready'] else 1
        if args.operation == 'init':
            if credentials_path.exists():
                raise ValueError(f'Credential file already exists: {credentials_path}; select a new --credentials path for a new team')
            config = tmux_config(args)
            if args.coordinator_thread:
                config['coordinator_thread'] = args.coordinator_thread
            request_id = args.request_id or str(uuid.uuid4())
            print(f'request_id={request_id}', file=sys.stderr)
            message = dict(op='init', objective=args.objective, team_id=args.team, config=config, request_id=request_id)
        elif args.operation == 'ping':
            message = dict(op='ping')
        else:
            credentials = json.loads(credentials_path.read_text())
            token, epoch = credentials['token'], credentials.get('epoch', 1)
            if args.operation == 'shutdown':
                message = dict(op='shutdown', token=token, epoch=epoch)
            elif args.operation in ('request', 'register'):
                request_id = args.request_id or str(uuid.uuid4())
                # Print before transport, so a lost response can be retried with the same ID.
                print(f'request_id={request_id}', file=sys.stderr)
                if args.operation == 'register':
                    kind = 'register'
                    body = {key: getattr(args, key) for key in ('name', 'adapter', 'model', 'effort') if getattr(args, key) is not None}
                else:
                    kind, body = args.kind, args.body
                message = dict(op='command', token=token, epoch=epoch, request_id=request_id, kind=kind, body=body)
            else:
                filters = dict(args.filters)
                filters.update({key: getattr(args, key) for key in ('task_id', 'run_id', 'type', 'priority', 'after', 'limit') if getattr(args, key) is not None})
                message = dict(op='read', token=token, view=args.operation, filters=filters)
        result = call(home, message)
        if isinstance(result, dict) and 'token' in result:
            destination = getattr(args, 'save_credentials', None)
            if not destination:
                if args.operation == 'init' or (args.operation == 'request' and args.kind == 'takeover'):
                    destination = credentials_path
                else:
                    destination = home / 'workers' / (result['session_id'] + '.json')
            saved = save_credentials(destination, result)
            result = {key: value for key, value in result.items() if key != 'token'}
            result['credentials'] = saved
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'codex-orch: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
