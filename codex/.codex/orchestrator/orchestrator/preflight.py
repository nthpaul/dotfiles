"""Deterministic preflight keyed by command, scope, env, and dirty worktree bytes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess


def _run(args, cwd):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, timeout=60)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _in_scope(relative, scope):
    if not scope:
        return True
    path = Path(relative)
    for item in scope:
        root = Path(item)
        if path == root or root == Path('.') or root in path.parents:
            return True
    return False


def _parse_status(line):
    if len(line) < 4:
        return None
    body = line[3:]
    if ' -> ' in body:
        body = body.split(' -> ', 1)[1]
    return body.strip()


def code_state(cwd, scope):
    cwd = Path(cwd).resolve()
    scope = [str(Path(item)) for item in (scope or [])]
    git = cwd / '.git'
    files = {}
    head, status = None, ''
    if git.exists():
        head_proc = _run(['git', 'rev-parse', 'HEAD'], cwd)
        if head_proc.returncode == 0:
            head = head_proc.stdout.strip()
        args = ['git', 'status', '--porcelain=v1', '-uall']
        if scope:
            args += ['--', *scope]
        status_proc = _run(args, cwd)
        status = status_proc.stdout
        for line in status.splitlines():
            relative = _parse_status(line)
            if not relative or not _in_scope(relative, scope):
                continue
            path = cwd / relative
            files[relative] = _sha(path.read_bytes()) if path.is_file() else 'missing'
    else:
        roots = [cwd / item for item in scope] or [cwd]
        for root in roots:
            if root.is_file() and _in_scope(str(root.relative_to(cwd)), scope or ['.']):
                files[str(root.relative_to(cwd))] = _sha(root.read_bytes())
                continue
            if not root.is_dir():
                continue
            for path in sorted(root.rglob('*')):
                if not path.is_file():
                    continue
                relative = str(path.relative_to(cwd))
                if _in_scope(relative, scope or ['.']):
                    files[relative] = _sha(path.read_bytes())
    return {'head': head, 'status': status, 'files': files}


def fingerprint(cwd, commands, scope=None, environment=None):
    payload = {
        'commands': commands,
        'scope': list(scope or []),
        'environment': dict(environment or {}),
        'code': code_state(cwd, scope),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return _sha(encoded), payload


def run_commands(commands, environment=None):
    env = dict(os.environ)
    if environment:
        env.update(environment)
    outputs = []
    for command in commands:
        argv = command['argv']
        cwd = command.get('cwd')
        proc = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False, timeout=60)
        outputs.append({'argv': argv, 'cwd': cwd, 'exit_code': proc.returncode,
                        'stdout_sha256': _sha(proc.stdout.encode()), 'stderr_sha256': _sha(proc.stderr.encode())})
        if proc.returncode != 0:
            return False, outputs
    return True, outputs
