"""OS resource handles. Callers persist returned identities before subsequent use.

Process trees are snapshots, not security boundaries. Daemonized/reparented tools
cannot be discovered retrospectively. macOS signals are inherently PID-addressed;
results stay uncertain there even when all observed processes reach the target state.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import platform
import shlex
import signal
import subprocess
import time


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True, timeout=60).stdout.strip()


class _BSDInfo(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in (
        'flags', 'status', 'xstatus', 'pid', 'ppid', 'uid', 'gid', 'ruid',
        'rgid', 'svuid', 'svgid', 'reserved')]
    _fields_ += [('comm', ctypes.c_char * 16), ('name', ctypes.c_char * 32)]
    _fields_ += [(name, ctypes.c_uint32) for name in (
        'nfiles', 'pgid', 'jobc', 'tdev', 'tpgid', 'nice')]
    _fields_ += [('start_sec', ctypes.c_uint64), ('start_usec', ctypes.c_uint64)]


class ProcessIdentity:
    @staticmethod
    def read(pid):
        """Return exact kernel birth identity; None means absent, errors are not absence."""
        pid = int(pid)
        if pid <= 1:
            raise ValueError('PID must be greater than 1')
        if platform.system() == 'Linux':
            try:
                raw = Path(f'/proc/{pid}/stat').read_text()
            except FileNotFoundError:
                return None
            fields = raw[raw.rfind(')') + 2:].split()
            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            return dict(pid=pid, start_identity=f'linux:{boot}:{fields[19]}',
                        ppid=int(fields[1]), state=fields[0])
        if platform.system() == 'Darwin':
            lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
            info = _BSDInfo()
            size = lib.proc_pidinfo(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info))
            if size != ctypes.sizeof(info):
                error = ctypes.get_errno()
                if error == 3:  # ESRCH only; permission errors must not look like exits.
                    return None
                raise OSError(error, 'proc_pidinfo could not establish identity')
            boot = run(['sysctl', '-n', 'kern.boottime'])
            return dict(pid=pid, start_identity=f'darwin:{boot}:{info.start_sec}:{info.start_usec}',
                        ppid=info.ppid, state={5: 'Z', 4: 'T'}.get(info.status, 'R'))
        raise RuntimeError('Process identities require Linux or macOS')

    @staticmethod
    def matches(pid, start_identity):
        identity = ProcessIdentity.read(pid)
        return bool(identity and identity['start_identity'] == start_identity)

    @staticmethod
    def state(pid, start_identity):
        identity = ProcessIdentity.read(pid)
        if identity is None:
            return 'exited'
        if identity['start_identity'] != start_identity:
            return 'replaced'
        return identity['state']


def _snapshot(parents):
    identities = {}
    for line in run(['ps', '-axo', 'pid=,ppid=']).splitlines():
        value, parent = map(int, line.split())
        if value <= 1 or parent not in parents:
            continue
        identity = ProcessIdentity.read(value)
        if identity and identity['ppid'] in parents:
            identities[value] = identity
    return identities


def control_tree(pid, start_identity, action, timeout=2.0):
    """Control observed descendants, checking every birth identity before signaling.

    A confirmed outcome covers only the observed tree; the caller must isolate
    workers to prevent escaped descendants. Never use a process group kill, since
    membership and IDs can be recycled independently of the registered root.
    """
    signals = {'pause': signal.SIGSTOP, 'resume': signal.SIGCONT, 'cancel': signal.SIGKILL}
    if action not in signals:
        raise ValueError('action must be pause, resume, or cancel')
    root = ProcessIdentity.read(pid)
    if root is None or root['start_identity'] != start_identity:
        return dict(outcome='exited' if root is None else 'uncertain', observed=[],
                    reason='root absent or birth identity changed')
    observed = {pid: root}
    errors = []
    atomic = hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal')

    def send(identity, sig):
        descriptor = None
        try:
            if atomic:
                descriptor = os.pidfd_open(identity['pid'])
            if not ProcessIdentity.matches(identity['pid'], identity['start_identity']):
                errors.append(f"identity changed: {identity['pid']}")
                return
            if descriptor is not None:
                signal.pidfd_send_signal(descriptor, sig)
            else:
                os.kill(identity['pid'], sig)
        except ProcessLookupError:
            pass
        except OSError as error:
            errors.append(str(error))
        finally:
            if descriptor is not None:
                os.close(descriptor)

    # Freeze ancestors first so their child sets stop growing; then recurse.
    # Resume leaves the tree stopped during collection; cancellation kills only
    # after the observed closure has been frozen.
    if action != 'resume':
        send(root, signal.SIGSTOP)
    for _ in range(32):
        try:
            snapshot = _snapshot(observed)
        except OSError as error:
            errors.append('cannot inspect descendant: ' + str(error))
            break
        additions = [item for item in snapshot.values()
                     if item['ppid'] in observed and item['pid'] not in observed]
        if not additions:
            break
        for item in additions:
            observed[item['pid']] = item
            if action != 'resume':
                send(item, signal.SIGSTOP)
    else:
        errors.append('process tree did not stabilize')
    for identity in reversed(list(observed.values())):
        send(identity, signals[action])
    deadline = time.monotonic() + timeout
    states = {}
    while True:
        states = {p: ProcessIdentity.state(p, item['start_identity']) for p, item in observed.items()}
        desired = all((s in ('T', 't') if action == 'pause' else
                       s in ('exited', 'Z') if action == 'cancel' else
                       s not in ('T', 't', 'replaced', 'exited', 'Z')) for s in states.values())
        if desired or time.monotonic() >= deadline:
            break
        time.sleep(0.02)
    if not atomic:
        errors.append('macOS lacks identity-bound signaling; PID check/signal race cannot be excluded')
    return dict(outcome='confirmed' if desired and not errors else 'uncertain',
                observed=list(observed.values()), states=states, observed_state=('paused' if action == 'pause' else 'resumed' if action == 'resume' else 'cancelled') if desired else 'unknown', reason='; '.join(errors),
                scope='observed descendants; escaped or reparented tools are not covered')


class TmuxManager:
    def __init__(self, socket, window, team, max_panes=4):
        if not str(window).startswith('@') or max_panes < 1:
            raise ValueError('exact @window ID and positive max_panes required')
        self.socket, self.window, self.team, self.max_panes = str(socket), window, team, max_panes

    def _tmux(self, *args):
        return run(['tmux', '-S', self.socket, *args])

    def _panes(self):
        fmt = '#{pane_id}\t#{@orch_team}\t#{@orch_agent}\t#{@orch_purpose}\t#{pane_dead}'
        return [line.split('\t') for line in self._tmux('list-panes', '-t', self.window, '-F', fmt).splitlines()]

    def ensure_pane(self, agent, command, purpose='worker'):
        if purpose not in ('worker', 'status') or not isinstance(command, list) or not command:
            raise ValueError('worker/status purpose and command argv required')
        panes = self._panes()
        owned = [p for p in panes if p[1:4] == [self.team, agent, purpose]]
        if len(owned) > 1:
            raise RuntimeError('ambiguous owned panes')
        if not owned:
            idle = [p for p in panes if p[1] == self.team and p[3] == purpose and p[4] == '1']
            if idle:
                owned = [idle[0]]
                self._tmux('set-option', '-p', '-t', idle[0][0], '@orch_agent', agent)
        if owned:
            pane = owned[0][0]
            if owned[0][4] == '1':
                self._tmux('respawn-pane', '-t', pane, shlex.join(command))
        else:
            workers = sum(p[1] == self.team and p[3] == 'worker' for p in panes)
            if purpose == 'worker' and workers >= self.max_panes:
                return None
            try:
                pane = self._tmux('split-window', '-d', '-t', self.window, '-P', '-F', '#{pane_id}', 'exec sleep 86400')
            except subprocess.CalledProcessError as error:
                if 'no space' in error.stderr.lower() or 'too small' in error.stderr.lower():
                    return None
                raise
            for key, value in [('team', self.team), ('agent', agent), ('purpose', purpose)]:
                self._tmux('set-option', '-p', '-t', pane, '@orch_' + key, value)
            self._tmux('set-option', '-p', '-t', pane, 'remain-on-exit', 'on')
            self._tmux('respawn-pane', '-k', '-t', pane, shlex.join(command))
        self._tmux('select-layout', '-t', self.window, 'tiled')
        return dict(socket=self.socket, window=self.window, pane=pane, team=self.team, agent=agent, purpose=purpose)

    def cleanup(self, pane, agent):
        matches = [p for p in self._panes() if p[0] == pane and p[1:4] == [self.team, agent, 'worker']]
        if len(matches) != 1:
            return False
        self._tmux('kill-pane', '-t', pane)
        return True


class WorktreeManager:
    @staticmethod
    def create(repo, path, branch, ref):
        repo, path = str(Path(repo).resolve()), str(Path(path).resolve())
        commit = run(['git', 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}'], cwd=repo)
        run(['git', 'check-ref-format', '--branch', branch], cwd=repo)
        run(['git', 'worktree', 'add', '-b', branch, path, commit], cwd=repo)
        return dict(repo=repo, path=path, branch=branch, base=commit)


class IntegrationManager:
    @staticmethod
    def cherry_pick(repo, commits):
        if not commits:
            raise ValueError('commits required')
        resolved = [run(['git', 'rev-parse', '--verify', '--end-of-options', c + '^{commit}'], cwd=repo) for c in commits]
        run(['git', 'cherry-pick', *resolved], cwd=repo)
        return run(['git', 'rev-parse', 'HEAD'], cwd=repo)

    @staticmethod
    def prepare(repo, trunk, parent):
        """Explicit repository-local Graphite setup for an isolated git worktree."""
        for name in (trunk, parent):
            run(['git', 'check-ref-format', '--branch', name], cwd=repo)
            run(['git', 'rev-parse', '--verify', '--end-of-options', 'refs/heads/' + name], cwd=repo)
        current = run(['git', 'symbolic-ref', '--quiet', '--short', 'HEAD'], cwd=repo)
        if current != trunk:
            if current == parent:
                raise ValueError('Graphite parent must differ from the current worktree branch')
            run(['git', 'merge-base', '--is-ancestor', parent, 'HEAD'], cwd=repo)
        elif parent != trunk:
            raise ValueError('Creating from trunk requires parent to name the same trunk')
        run(['gt', 'init', '--trunk', trunk, '--no-interactive'], cwd=repo)
        if current != trunk:
            run(['gt', 'track', current, '--parent', parent, '--no-interactive'], cwd=repo)
        return dict(branch=current, trunk=trunk, parent=parent)

    @staticmethod
    def create(repo, branch, message, trunk=None, parent=None):
        if (trunk is None) != (parent is None):
            raise ValueError('Provide both Graphite trunk and parent for worktree initialization')
        if trunk is not None:
            IntegrationManager.prepare(repo, trunk, parent)
        try:
            return run(['gt', 'create', branch, '--all', '-m', message, '--no-interactive'], cwd=repo)
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or '') + (error.stdout or '')
            if 'untracked branch' in detail or 'not been initialized' in detail:
                raise ValueError('Initialize this isolated worktree with explicit trunk and parent, then retry after inspecting its branch state: ' + detail.strip()) from error
            raise

    @staticmethod
    def submit(repo):
        return run(['gt', 'submit', '--no-interactive'], cwd=repo)

    @staticmethod
    def verify_ci(repo, pr, expected_head):
        details = json.loads(run(['gh', 'pr', 'view', str(pr), '--json', 'headRefOid'], cwd=repo))
        if details['headRefOid'] != expected_head:
            return dict(passed=False, reason='PR head differs from expected commit')
        try:
            checks = json.loads(run(['gh', 'pr', 'checks', str(pr), '--required', '--json', 'name,bucket,state,link'], cwd=repo))
        except subprocess.CalledProcessError as error:
            return dict(passed=False, reason='required checks failed or unavailable', detail=error.stderr)
        # Recheck after fetching statuses; a moving PR must never validate an old head.
        after = json.loads(run(['gh', 'pr', 'view', str(pr), '--json', 'headRefOid'], cwd=repo))
        passed = bool(checks) and all(c['bucket'] == 'pass' for c in checks) and after['headRefOid'] == expected_head
        return dict(passed=passed, head=expected_head, checks=checks,
                    reason='' if passed else 'no required checks, pending/failing checks, or changed head')


def verify_stack_ci(repo, pr, expected_head):
    """Discover downstack PRs through base branches and verify every exact head."""
    default = json.loads(run(['gh', 'repo', 'view', '--json', 'defaultBranchRef'], cwd=repo))['defaultBranchRef']['name']
    stack, seen = [], set()
    reference, expected = str(pr), expected_head
    while True:
        details = json.loads(run(['gh', 'pr', 'view', reference, '--json', 'number,headRefOid,baseRefName,state,url'], cwd=repo))
        number = details['number']
        if number in seen or len(seen) >= 50:
            return {'passed':False, 'reason':'Cyclic or oversized PR stack', 'stack':stack}
        seen.add(number)
        if details['state'] != 'OPEN' or details['headRefOid'] != expected:
            return {'passed':False, 'reason':'PR is closed or head changed', 'stack':stack}
        check = IntegrationManager.verify_ci(repo, number, expected)
        stack.append(dict(details, checks=check))
        if not check['passed']:
            return {'passed':False, 'reason':check['reason'], 'stack':stack}
        if details['baseRefName'] == default:
            break
        parents = json.loads(run(['gh','pr','list','--head',details['baseRefName'],'--state','open','--json','number,headRefOid'],cwd=repo))
        if len(parents) != 1:
            return {'passed':False, 'reason':'Cannot identify a unique downstack PR; restack first', 'stack':stack}
        reference, expected = str(parents[0]['number']), parents[0]['headRefOid']
    for item in stack:
        current = json.loads(run(['gh','pr','view',str(item['number']),'--json','headRefOid,baseRefName,state'],cwd=repo))
        if current['headRefOid'] != item['headRefOid'] or current['baseRefName'] != item['baseRefName'] or current['state'] != 'OPEN':
            return {'passed':False, 'reason':'Stack changed during verification', 'stack':stack}
    return {'passed':True, 'head':expected_head, 'stack':stack, 'reason':''}
