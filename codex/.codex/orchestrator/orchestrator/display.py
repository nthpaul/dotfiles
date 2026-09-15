"""Read-only live pane display. Never changes database state."""
import argparse
import json
from pathlib import Path
import sqlite3
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', required=True)
    parser.add_argument('--team', required=True)
    parser.add_argument('--agent')
    args = parser.parse_args()
    home = Path(args.home)
    database = sqlite3.connect(f'file:{home / "state.sqlite3"}?mode=ro', uri=True)
    database.row_factory = sqlite3.Row
    previous = None
    while True:
        try:
            completed = False
            if args.agent:
                rows = database.execute('SELECT r.* FROM runs r JOIN sessions s ON s.id=r.session_id JOIN tasks t ON t.id=r.task_id WHERE s.agent_id=? AND t.team_id=? ORDER BY r.rowid DESC LIMIT 1', (args.agent, args.team)).fetchall()
                if rows:
                    run = dict(rows[0])
                    completed = bool(run['released'])
                    log = home / 'runs' / run['id'] / 'runner.log'
                    text = log.read_text(errors='replace')[-12000:] if log.exists() else 'Waiting for runner'
                    screen = f"Worker {args.agent}\nRun {run['id']}\nHealth {run['health']} | desired {run['desired']} | observed {run['observed']}\n\n{text}"
                else:
                    screen = f'Worker {args.agent}: idle'
            else:
                team = database.execute('SELECT * FROM teams WHERE id=?', (args.team,)).fetchone()
                tasks = database.execute('SELECT id,state FROM tasks WHERE team_id=? ORDER BY rowid', (args.team,)).fetchall()
                issues = database.execute("SELECT COUNT(*) FROM issues WHERE team_id=? AND state='open'", (args.team,)).fetchone()[0]
                inbox = database.execute("SELECT COUNT(*) FROM deliveries d JOIN agents a ON a.id=d.recipient WHERE a.team_id=? AND a.role='coordinator' AND d.acknowledged_at IS NULL AND d.state<>'cancelled'", (args.team,)).fetchone()[0]
                screen = f"{team['objective']}\nRevision {team['revision']} | epoch {team['epoch']} | {team['state']}\nOpen issues: {issues} | coordinator inbox: {inbox}\n\n" + '\n'.join(f"{t['id']}: {t['state']}" for t in tasks)
            if screen != previous:
                # Strip control bytes from provider output before displaying in our pane.
                screen = ''.join(c for c in screen if c in '\n\t' or ord(c)>=32 and ord(c)!=127)
                print('\033[2J\033[H' + screen, flush=True)
                previous = screen
            if completed:
                return  # remain-on-exit preserves output and makes this pane reusable.
        except (sqlite3.Error, OSError) as error:
            print(f'Status temporarily unavailable: {error}', flush=True)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
