"""Full-screen curses board with a deterministic non-TTY snapshot."""
from __future__ import annotations

import curses
import json
import sys
import uuid
from pathlib import Path

from .board_model import load_coordinator_credentials, load_homes, probe_pane, sanitize_text
from .client import call

SECTIONS = (
    ('teams', 'Teams'),
    ('tasks', 'Tasks'),
    ('epochs', 'Epochs'),
    ('revisions', 'Revisions'),
    ('attempts', 'Attempts'),
    ('workers', 'Workers'),
    ('inbox', 'Inbox'),
    ('issues', 'Issues'),
    ('deliveries', 'Deliveries'),
    ('operations', 'Operations'),
    ('resources', 'Resources'),
)
SECTION_KEYS = [name for name, _ in SECTIONS]


def clip(text, width):
    text = sanitize_text(text).replace('\t', ' ').replace('\n', ' ')
    if width <= 0:
        return ''
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + '$'


def default_control(home, credentials, kind, body):
    return call(home, {
        'op': 'command', 'token': credentials['token'], 'epoch': credentials['epoch'],
        'request_id': str(uuid.uuid4()), 'kind': kind, 'body': body,
    })


def default_tmux(socket, window, pane):
    import subprocess
    subprocess.run(['tmux', '-S', socket, 'select-window', '-t', window], check=False, capture_output=True, timeout=2)
    subprocess.run(['tmux', '-S', socket, 'select-pane', '-t', pane], check=False, capture_output=True, timeout=2)
    return True


def format_usage(usage):
    if not usage:
        return 'usage unknown'
    source = usage.get('delta') or usage.get('current') or {}
    if not source:
        return 'usage unknown'
    parts = [f'{key}={source[key]}' for key in source]
    return 'usage ' + ' '.join(parts)


def _agent_map(snapshot):
    return {agent['id']: agent for agent in snapshot.get('agents') or []}


def _session_map(snapshot):
    return {session['id']: session for session in snapshot.get('sessions') or []}


class Board:
    def __init__(self, homes, team=None, section='tasks', filter_text='',
                 control=None, probe=None, tmux=None, credentials_loader=None):
        self.homes = [Path(home).expanduser().resolve() for home in homes]
        self.home_index = 0
        self.team_id = team
        self.section = section if section in SECTION_KEYS else 'tasks'
        self.filter_text = filter_text or ''
        self.cursor = 0
        self.offset = 0
        self.detail = True
        self.message = ''
        self.requested = []
        self.filter_mode = False
        self.control = control or default_control
        self.probe = probe or probe_pane
        self.tmux = tmux or default_tmux
        self.credentials_loader = credentials_loader or load_coordinator_credentials
        self.snapshots = []
        self.reload()

    def reload(self):
        self.snapshots = load_homes(self.homes, probe=self.probe)
        if self.home_index >= len(self.snapshots):
            self.home_index = 0
        snapshot = self.snapshot
        teams = snapshot.get('teams') or []
        if self.team_id and not any(team['id'] == self.team_id for team in teams):
            self.team_id = teams[0]['id'] if teams else None
        elif not self.team_id and teams:
            self.team_id = teams[0]['id']
        rows = self.rows()
        if self.cursor >= len(rows):
            self.cursor = max(0, len(rows) - 1)

    @property
    def snapshot(self):
        return self.snapshots[self.home_index] if self.snapshots else {'home': '', 'error': 'no homes', 'teams': []}

    def team(self):
        for team in self.snapshot.get('teams') or []:
            if team['id'] == self.team_id:
                return team
        return None

    def scoped(self, table):
        rows = self.snapshot.get(table) or []
        if table == 'teams' or not self.team_id:
            return rows
        if table == 'runs':
            task_ids = {task['id'] for task in self.snapshot.get('tasks') or [] if task.get('team_id') == self.team_id}
            session_ids = {session['id'] for session in self.snapshot.get('sessions') or []
                           if _agent_map(self.snapshot).get(session.get('agent_id'), {}).get('team_id') == self.team_id}
            return [row for row in rows if row.get('task_id') in task_ids or row.get('session_id') in session_ids]
        if table == 'sessions':
            agents = _agent_map(self.snapshot)
            return [row for row in rows if agents.get(row.get('agent_id'), {}).get('team_id') == self.team_id]
        if table == 'deliveries':
            agent_ids = {agent['id'] for agent in self.snapshot.get('agents') or [] if agent.get('team_id') == self.team_id}
            return [row for row in rows if row.get('recipient') in agent_ids]
        return [row for row in rows if row.get('team_id') == self.team_id]

    def rows(self):
        section = self.section
        items = []
        if section == 'teams':
            for home in self.snapshots:
                for team in home.get('teams') or []:
                    items.append({'id': team['id'], 'label': f"{team['id']}  {team.get('state')}  epoch={team.get('epoch')}  rev={team.get('revision')}  {team.get('objective','')}",
                                  'kind': 'team', 'team_id': team['id'], 'home': home.get('home'), 'record': team, 'error': home.get('error')})
                if home.get('error'):
                    items.append({'id': home.get('home'), 'label': f"HOME ERROR {home.get('home')}  {home.get('error')}",
                                  'kind': 'home-error', 'record': home})
        elif section == 'tasks':
            for task in self.scoped('tasks'):
                spec = task.get('spec') if isinstance(task.get('spec'), dict) else {}
                deps = spec.get('dependencies') or []
                holds = task.get('holds') or []
                items.append({'id': task['id'], 'label': f"{task['id']}  {task.get('state')}  holds={holds or '-'}  deps={deps or '-'}  rev={task.get('revision')}",
                              'kind': 'task', 'record': task})
        elif section == 'epochs':
            team = self.team() or {}
            items.append({'id': f"epoch-{team.get('epoch')}", 'label': f"current epoch={team.get('epoch')}  coordinator={team.get('coordinator_session')}",
                          'kind': 'epoch', 'record': team})
            for event in self.scoped('events'):
                if event.get('type') == 'ownership_acquired':
                    items.append({'id': event['id'], 'label': f"seq {event.get('sequence')}  ownership_acquired  {event.get('body')}",
                                  'kind': 'event', 'record': event})
        elif section == 'revisions':
            team = self.team() or {}
            items.append({'id': f"rev-{team.get('revision')}", 'label': f"current revision={team.get('revision')}",
                          'kind': 'revision', 'record': team})
            for event in self.scoped('events'):
                if event.get('type') == 'replan':
                    items.append({'id': event['id'], 'label': f"seq {event.get('sequence')}  replan  {event.get('body')}",
                                  'kind': 'event', 'record': event})
        elif section == 'attempts':
            for run in self.scoped('runs'):
                drift = ' REQUESTED!=OBSERVED' if run.get('drift') else ''
                items.append({'id': run['id'], 'label': (
                    f"{run['id']}  task={run.get('task_id')}  rev={run.get('revision')}  "
                    f"desired={run.get('desired')} observed={run.get('observed')}{drift}  "
                    f"health={run.get('health')} released={run.get('released')}  {format_usage(run.get('usage'))}"),
                    'kind': 'run', 'record': run})
        elif section == 'workers':
            sessions = _session_map(self.snapshot)
            runs = self.scoped('runs')
            for agent in self.scoped('agents'):
                if agent.get('role') != 'worker':
                    continue
                config = agent.get('config') if isinstance(agent.get('config'), dict) else {}
                agent_sessions = [session for session in self.scoped('sessions') if session.get('agent_id') == agent['id']]
                session = agent_sessions[-1] if agent_sessions else {}
                session_config = session.get('config') if isinstance(session.get('config'), dict) else config
                mode = session_config.get('mode')
                mode_label = f"mode={mode}" if mode else 'mode=omitted'
                active = next((run for run in runs if not run.get('released') and sessions.get(run.get('session_id'), {}).get('agent_id') == agent['id']), None)
                usage = format_usage(active.get('usage') if active else None)
                items.append({'id': agent['id'], 'label': (
                    f"{agent.get('name')}  {agent['id']}  {config.get('adapter')} {config.get('model')} "
                    f"effort={config.get('effort')}  {mode_label}  session={session.get('id','-')}  "
                    f"ext={session.get('external_id') or '-'}  {session.get('state','-')}  {usage}"),
                    'kind': 'worker', 'record': agent, 'session': session, 'run': active})
        elif section == 'inbox':
            issues_by_event = {issue.get('event_id') for issue in self.scoped('issues') if issue.get('state') == 'open'}
            events = {event['id']: event for event in self.snapshot.get('events') or []}
            for delivery in self.scoped('deliveries'):
                event = events.get(delivery.get('event_id'), {})
                if delivery.get('acknowledged_at') and delivery.get('event_id') not in issues_by_event:
                    continue
                items.append({'id': delivery['id'], 'label': (
                    f"{delivery['id']}  {delivery.get('state')}  {event.get('type')}  pri={event.get('priority')}  "
                    f"{event.get('body')}"),
                    'kind': 'delivery', 'record': delivery, 'event': event})
        elif section == 'issues':
            for issue in self.scoped('issues'):
                items.append({'id': issue['id'], 'label': (
                    f"{issue['id']}  {issue.get('state')}  {issue.get('priority')}  {issue.get('coalescing_key')}  "
                    f"blocks={issue.get('blocks_acceptance')}  task={issue.get('task_id') or '-'}"),
                    'kind': 'issue', 'record': issue})
        elif section == 'deliveries':
            events = {event['id']: event for event in self.snapshot.get('events') or []}
            for delivery in self.scoped('deliveries'):
                event = events.get(delivery.get('event_id'), {})
                items.append({'id': delivery['id'], 'label': (
                    f"{delivery['id']}  {delivery.get('state')}  to={delivery.get('recipient')}  "
                    f"ack={delivery.get('acknowledged_at') or '-'}  {event.get('type')}"),
                    'kind': 'delivery', 'record': delivery})
        elif section == 'operations':
            for operation in self.scoped('operations'):
                ci = operation.get('ci')
                ci_label = ''
                if ci:
                    passed = ci.get('passed')
                    if passed is None and not ci.get('head'):
                        verdict = 'unchecked'
                    elif passed is True:
                        verdict = 'passed'
                    elif passed is False:
                        verdict = 'failed'
                    else:
                        verdict = 'unchecked'
                    ci_label = f"  ci={verdict} expected={ci.get('expected_head') or '-'} head={ci.get('head') or '-'}"
                items.append({'id': operation['id'], 'label': (
                    f"{operation['id']}  {operation.get('kind')}  {operation.get('state')}  run={operation.get('run_id') or '-'}{ci_label}"),
                    'kind': 'operation', 'record': operation})
        elif section == 'resources':
            for resource in self.scoped('resources'):
                pane = resource.get('pane_state') or {}
                extra = f"  pane={pane.get('state')}" if pane else ''
                items.append({'id': resource['id'], 'label': (
                    f"{resource['id']}  {resource.get('kind')}  {resource.get('state')}  "
                    f"{resource.get('identity')}  owner={resource.get('owner_run') or '-'}{extra}"),
                    'kind': 'resource', 'record': resource})
        needle = self.filter_text.lower()
        if needle:
            items = [item for item in items if needle in item['label'].lower() or needle in str(item.get('id', '')).lower()]
        return items

    def selected(self):
        rows = self.rows()
        if not rows:
            return None
        return rows[self.cursor]

    def detail_lines(self):
        row = self.selected()
        if not row:
            return ['(empty)']
        record = row.get('record') or {}
        lines = [f"{row['kind']} {row['id']}"]
        if row['kind'] == 'task':
            spec = record.get('spec') if isinstance(record.get('spec'), dict) else {}
            lines += [f"state={record.get('state')} revision={record.get('revision')} holds={record.get('holds') or []}",
                      f"deps={spec.get('dependencies') or []} budgets={spec.get('budgets') or {}}",
                      clip(spec.get('objective') or '', 200)]
        elif row['kind'] == 'run':
            lines += [
                f"task={record.get('task_id')} session={record.get('session_id')} revision={record.get('revision')}",
                f"requested desired={record.get('desired')}  observed={record.get('observed')}  health={record.get('health')}",
                f"released={record.get('released')} pid={record.get('runner_pid') or '-'} identity={record.get('runner_identity') or '-'}",
                format_usage(record.get('usage')),
            ]
            if record.get('drift'):
                lines.append('REQUESTED!=OBSERVED')
        elif row['kind'] == 'worker':
            config = record.get('config') if isinstance(record.get('config'), dict) else {}
            session = row.get('session') or {}
            run = row.get('run')
            lines += [f"adapter={config.get('adapter')} model={config.get('model')} effort={config.get('effort')} mode={config.get('mode') or (session.get('config') or {}).get('mode') or 'omitted'}",
                      f"session={session.get('id')} external_id={session.get('external_id') or '-'} state={session.get('state')}",
                      format_usage(run.get('usage') if run else None)]
        elif row['kind'] == 'resource':
            pane = record.get('pane_state')
            lines += [f"kind={record.get('kind')} state={record.get('state')} identity={record.get('identity')}",
                      f"owner_run={record.get('owner_run')}", f"pane={pane}" if pane else 'pane=-']
        elif row['kind'] == 'operation':
            ci = record.get('ci')
            lines += [f"kind={record.get('kind')} state={record.get('state')}",
                      f"intent={record.get('intent')}", f"outcome={record.get('outcome')}"]
            if ci:
                lines.append(f"ci passed={ci.get('passed')} expected_head={ci.get('expected_head')} head={ci.get('head')} reason={ci.get('reason')}")
        elif row['kind'] == 'team':
            lines += [f"epoch={record.get('epoch')} revision={record.get('revision')} state={record.get('state')}",
                      f"home={row.get('home')} error={row.get('error') or '-'}",
                      clip(record.get('objective') or '', 200)]
        else:
            body = record.get('body')
            if body:
                lines.append(f"body={body}")
            lines.append(clip(json.dumps({key: record[key] for key in record if key not in ('body', 'spec', 'token', 'token_hash')}, default=str), 240))
        return lines

    def render(self, width=100, height=30):
        width, height = max(20, int(width)), max(8, int(height))
        snapshot = self.snapshot
        team = self.team() or {}
        homes = f"{self.home_index + 1}/{len(self.snapshots)}"
        header = clip(
            f"board  home={snapshot.get('home')}  {homes}  tables={snapshot.get('schema_tables', 0)}  "
            f"team={self.team_id or '-'}  epoch={team.get('epoch', '-')}  rev={team.get('revision', '-')}  "
            f"state={team.get('state', snapshot.get('error') or '-')}", width)
        tabs = ' '.join(('[' + name + ']' if name == self.section else name) for name, _ in SECTIONS)
        filter_line = ('filter> ' if self.filter_mode else 'filter: ') + (self.filter_text or '')
        rows = self.rows()
        list_height = max(3, height - 12) if self.detail else max(3, height - 5)
        if self.cursor < self.offset:
            self.offset = self.cursor
        if self.cursor >= self.offset + list_height:
            self.offset = max(0, self.cursor - list_height + 1)
        window = rows[self.offset:self.offset + list_height]
        body = []
        if snapshot.get('error') and self.section != 'teams':
            body.append(clip('HOME ERROR ' + snapshot['error'], width))
        if not window:
            body.append(clip('(no rows)', width))
        for index, row in enumerate(window):
            mark = '>' if (self.offset + index) == self.cursor else ' '
            body.append(clip(mark + row['label'], width))
        lines = [header, clip(tabs, width), clip(filter_line, width), clip('-' * width, width), *body]
        if self.detail:
            lines.append(clip('-' * width, width))
            lines.append(clip('detail', width))
            lines.extend(clip(line, width) for line in self.detail_lines()[: max(1, height - len(lines) - 2)])
        status = 'requested: ' + ('; '.join(self.requested[-3:]) or '-')
        if self.message:
            status += '  |  ' + self.message
        help_line = 'q quit  n home  t team  / filter  a attach  p pause  r resume  x cancel  h hold'
        lines.append(clip(status, width))
        lines.append(clip(help_line, width))
        lines = lines[:height]
        while len(lines) < height:
            lines.append(' ' * min(width, 0))
        return '\n'.join(lines)

    def handle(self, key):
        if self.filter_mode:
            if key in ('enter', '\n', '\r'):
                self.filter_mode = False
            elif key in ('esc',):
                self.filter_mode = False
                self.filter_text = ''
            elif key in ('backspace', '\x7f'):
                self.filter_text = self.filter_text[:-1]
            elif isinstance(key, str) and len(key) == 1 and 32 <= ord(key) < 127:
                self.filter_text += key
            self.cursor = 0
            return None
        if key in ('q',):
            return 'quit'
        if key in ('n',):
            if self.snapshots:
                self.home_index = (self.home_index + 1) % len(self.snapshots)
                self.team_id = None
                self.cursor = 0
                self.reload()
        elif key in ('t',):
            teams = [team['id'] for team in self.snapshot.get('teams') or []]
            if teams:
                self.team_id = teams[(teams.index(self.team_id) + 1) % len(teams)] if self.team_id in teams else teams[0]
                self.cursor = 0
        elif key in ('tab',):
            self.section = SECTION_KEYS[(SECTION_KEYS.index(self.section) + 1) % len(SECTION_KEYS)]
            self.cursor = 0
        elif key in SECTION_KEYS:
            self.section = key
            self.cursor = 0
        elif key.isdigit() and 1 <= int(key) <= len(SECTION_KEYS):
            self.section = SECTION_KEYS[int(key) - 1]
            self.cursor = 0
        elif key in ('j', 'down'):
            self.cursor = min(self.cursor + 1, max(0, len(self.rows()) - 1))
        elif key in ('k', 'up'):
            self.cursor = max(0, self.cursor - 1)
        elif key in ('g',):
            self.cursor = 0
        elif key in ('G',):
            self.cursor = max(0, len(self.rows()) - 1)
        elif key in ('enter',):
            self.detail = not self.detail
        elif key in ('/',):
            self.filter_mode = True
        elif key in ('a',):
            self.attach()
        elif key in ('p',):
            self.submit_control('pause')
        elif key in ('r',):
            self.submit_control('resume')
        elif key in ('x', 'c'):
            self.submit_control('cancel')
        elif key in ('h',):
            self.submit_hold(clear=False)
        elif key in ('H',):
            self.submit_hold(clear=True)
        elif key in ('R',):
            self.reload()
        elif key in ('?',):
            self.message = 'sections 1-9/tab  homes n  teams t  attach a  control p/r/x  hold h'
        return None

    def _credentials(self):
        credentials = self.credentials_loader(self.snapshot.get('home'))
        if not credentials or not credentials.get('token'):
            self.message = 'no coordinator credentials; control not sent'
            return None
        team = self.team()
        if team and credentials.get('epoch') is not None and team.get('epoch') is not None and credentials['epoch'] != team['epoch']:
            self.message = f"stale coordinator epoch credentials={credentials['epoch']} team={team['epoch']}; control not sent"
            return None
        return credentials

    def submit_control(self, action):
        row = self.selected()
        run = None
        if row and row['kind'] == 'run':
            run = row['record']
        elif row and row.get('run'):
            run = row['run']
        if not run:
            self.message = 'select an attempt or busy worker'
            return
        credentials = self._credentials()
        if not credentials:
            return
        try:
            result = self.control(self.snapshot.get('home'), credentials, 'control',
                                  {'run_id': run['id'], 'action': action})
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            self.message = f'requested {action} failed: {error}'
            return
        desired = result.get('desired') if isinstance(result, dict) else action
        note = f"{action} {run['id']} requested desired={desired}"
        self.requested.append(note)
        self.message = note + f"  observed={run.get('observed')}"

    def submit_hold(self, clear=False):
        row = self.selected()
        if not row or row['kind'] != 'task':
            self.message = 'select a task to hold'
            return
        credentials = self._credentials()
        if not credentials:
            return
        reason = self.filter_text.strip() or 'board'
        body = {'task_id': row['id'], 'reason': reason}
        if clear:
            body['clear'] = True
        try:
            result = self.control(self.snapshot.get('home'), credentials, 'hold', body)
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            self.message = f'requested hold failed: {error}'
            return
        note = f"hold {'clear ' if clear else ''}{row['id']} requested holds={result.get('holds') if isinstance(result, dict) else reason}"
        self.requested.append(note)
        self.message = note

    def attach(self):
        row = self.selected()
        resource = None
        if row and row['kind'] == 'resource' and row['record'].get('kind') == 'pane':
            resource = row['record']
        elif row and row['kind'] in ('worker', 'run'):
            owner = None
            if row['kind'] == 'run':
                owner = row['id']
            elif row.get('run'):
                owner = row['run']['id']
            for candidate in self.scoped('resources'):
                if candidate.get('kind') == 'pane' and candidate.get('owner_run') == owner:
                    resource = candidate
                    break
        if not resource:
            self.message = 'no owned pane on this row'
            return
        pane = resource.get('pane_state') or {}
        if pane.get('state') != 'live':
            self.message = f"pane {pane.get('state') or 'unknown'}; not attached"
            return
        detail = resource.get('detail') or {}
        socket = pane.get('socket') or detail.get('socket')
        window = pane.get('window') or detail.get('window')
        pane_id = pane.get('pane') or detail.get('pane')
        if not (socket and window and pane_id):
            self.message = 'pane handles incomplete; not attached'
            return
        try:
            self.tmux(socket, window, pane_id)
        except (OSError, RuntimeError, ValueError) as error:
            self.message = f'attach failed: {error}'
            return
        self.message = f'focused {socket} {window} {pane_id}'


def run_curses(board):
    def loop(stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        stdscr.timeout(500)
        while True:
            height, width = stdscr.getmaxyx()
            text = board.render(width, height)
            stdscr.erase()
            for index, line in enumerate(text.splitlines()[:height]):
                try:
                    stdscr.addnstr(index, 0, line[: max(0, width - 1)], max(0, width - 1))
                except curses.error:
                    pass
            stdscr.refresh()
            try:
                key = stdscr.get_wch()
            except curses.error:
                board.reload()
                continue
            if key == curses.KEY_RESIZE:
                continue
            mapped = _map_key(key)
            if board.handle(mapped) == 'quit':
                return 0
    return curses.wrapper(loop)


def _map_key(key):
    if key in (curses.KEY_DOWN,):
        return 'down'
    if key in (curses.KEY_UP,):
        return 'up'
    if key in (curses.KEY_BACKSPACE, 127):
        return 'backspace'
    if key in (9,):
        return 'tab'
    if key in (10, 13):
        return 'enter'
    if key in (27,):
        return 'esc'
    if isinstance(key, str):
        return key
    return ''


def main(args):
    homes = [Path(args.home).expanduser().resolve()]
    for extra in getattr(args, 'homes', None) or []:
        path = Path(extra).expanduser().resolve()
        if path not in homes:
            homes.append(path)
    board = Board(homes, team=getattr(args, 'team', None), section=getattr(args, 'section', None) or 'tasks',
                  filter_text=getattr(args, 'board_filter', '') or getattr(args, 'filter', '') or '')
    snapshot = bool(getattr(args, 'snapshot', False) or not sys.stdout.isatty())
    if snapshot:
        print(board.render(getattr(args, 'width', 100), getattr(args, 'height', 30)))
        return 0
    return run_curses(board)
