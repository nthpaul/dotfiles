"""Opt-in live pilot: matching code fixtures, Codex alone vs Codex with two Groks.

Run with --output outside the repository. Requires authenticated codex/grok CLIs.
Creates detached worktrees and retains all logs/diffs for independent inspection.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

SPECS = {
    'intervals': '''Implement merge_intervals(intervals) in intervals.py. Return sorted merged
closed intervals as a list of (start,end) tuples. Merge overlaps and touching endpoints.
Accept an iterable of pairs; empty input returns []; reject reversed endpoints with
ValueError. Do not mutate the input. Only edit intervals.py. Run the supplied tests.''',
    'ordering': '''Implement dependency_order(graph) in ordering.py. Input maps string nodes
to iterables of prerequisite node names. Include prerequisite-only nodes. Return the
lexicographically smallest valid topological order, choosing the smallest available
node at each step. Deduplicate edges. A cycle including a self cycle raises ValueError.
Do not mutate the input. Only edit ordering.py. Run the supplied tests.''',
}
STARTERS = {'intervals': 'def merge_intervals(intervals):\n    return sorted(intervals)\n',
            'ordering': 'def dependency_order(graph):\n    return sorted(graph)\n'}
TESTS = '''import unittest
from intervals import merge_intervals
from ordering import dependency_order
class Cases(unittest.TestCase):
    def test_intervals(self):
        self.assertEqual(merge_intervals([(3,5),(1,3)]), [(1,5)])
        self.assertEqual(merge_intervals([]), [])
    def test_ordering(self):
        self.assertEqual(dependency_order({'a':['b']}), ['b','a'])
        self.assertEqual(dependency_order({}), [])
if __name__ == '__main__': unittest.main()
'''
HOLDOUT = '''import copy,itertools,random
from intervals import merge_intervals
from ordering import dependency_order
assert merge_intervals(iter([(4,9),(1,2),(2,5),(11,11)]))==[(1,9),(11,11)]
a=[(3,7),(1,2),(2,3)];saved=copy.deepcopy(a);assert merge_intervals(a)==[(1,7)];assert a==saved
for bad in [[(2,1)], [(0,1),(8,7)]]:
 try: merge_intervals(bad)
 except ValueError: pass
 else: raise AssertionError('reversed endpoint accepted')
assert dependency_order({'b':['a','a'],'d':['c'],'a':[]})==['a','b','c','d']
assert dependency_order({'z':(x for x in ['x','y'])})==['x','y','z']
g={'b':['a'],'c':['b']};saved=copy.deepcopy(g);assert dependency_order(g)==['a','b','c'];assert g==saved
for bad in [{'a':['a']},{'a':['b'],'b':['a']},{'a':[],'b':['c'],'c':['b']}]:
 try: dependency_order(bad)
 except ValueError: pass
 else: raise AssertionError('cycle accepted')
r=random.Random(731)
for _ in range(30):
 names=list('abcde');r.shuffle(names)
 g={n:[p for p in names[:i] if r.random()<.4] for i,n in enumerate(names)}
 expected=min(p for p in itertools.permutations(names) if all(p.index(d)<p.index(n) for n,deps in g.items() for d in deps))
 assert dependency_order(g)==list(expected)
print('holdout: passed')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--mode', choices=('baseline', 'medium', 'high'), required=True)
    args = parser.parse_args()
    root = args.output.resolve() / args.mode
    root.mkdir(parents=True, exist_ok=False)
    repository = Path(__file__).resolve().parents[4]
    revision = subprocess.check_output(['git', 'rev-parse', args.revision], cwd=repository, text=True).strip()
    paths = {}
    for name in ('combined', *SPECS):
        path = root / name
        subprocess.run(['git', 'worktree', 'add', '--detach', str(path), revision], cwd=repository, check=True, capture_output=True)
        fixture = path / 'pilot_fixture'
        fixture.mkdir()
        for module, code in STARTERS.items():
            (fixture / (module+'.py')).write_text(code)
        (fixture/'test_cases.py').write_text(TESTS)
        (fixture/'AGENTS.md').write_text('This is an isolated benchmark fixture. Only edit the assigned Python implementation files. No commits, publishing, external messages, or changes to tests. Use python3 -m unittest -v. Do not spawn workers except the explicitly requested Grok workers.\n')
        paths[name] = str(fixture)
    prompt = 'Complete both independent Python tasks below, and verify the combined result. Do not edit tests or AGENTS.md. Do not commit, publish, or contact anyone.\n' + '\n'.join(SPECS.values())
    command = ['codex','exec','--ignore-user-config','--ephemeral','--skip-git-repo-check',
               '-m','gpt-6-astra','-c','model_reasoning_effort="high"',
               '--dangerously-bypass-approvals-and-sandbox','-C',paths['combined'],'--json',
               '-o',str(root/'final.txt')]
    if args.mode == 'baseline':
        prompt += '\nDo these tasks yourself; do not delegate or spawn subagents.'
    else:
        wrapper=repository/'codex/.local/bin/grok-bridge'
        command += ['-c','mcp_servers.grok_bridge.command='+json.dumps(str(wrapper)),
                    '-c','mcp_servers.grok_bridge.args='+json.dumps(['--home',str(root/'bridge'),'mcp']),
                    '-c','mcp_servers.grok_bridge.tool_timeout_sec=45']
        prompt += f'''\nThis is an explicit orchestration integration test. Use grok_bridge MCP to
spawn exactly two independent workers before waiting, at {args.mode} effort. Assign intervals
in cwd {paths['intervals']} with write_scope ["intervals.py"], and ordering in cwd
{paths['ordering']} with write_scope ["ordering.py"]. Give each its full task specification,
context, scope and completion criteria. Request relevant tests, allowing the other starter's
test to fail because it belongs to the other worker. While they run, inspect the supplied tests.
Wait for both terminal results, inspect one worker's message/tool history, review the code,
and copy the two implementations into your combined cwd. Run combined tests. Resume one
worker's exact session to ask it to recall its original task and explain a relevant edge case
without editing files. Collect that report too. Fix any real defects with same-session follow-up.
Keep working until verified or explicitly blocked. Do not spawn native Codex subagents.
In the final report state results, retry count, defects found, and unresolved issues.'''
    (root/'prompt.txt').write_text(prompt)
    started = time.monotonic()
    with (root/'events.jsonl').open('w') as out, (root/'stderr.log').open('w') as err:
        run = subprocess.run(command, input=prompt, text=True, stdout=out, stderr=err, timeout=900)
    verified = subprocess.run(['python3','-c',HOLDOUT],cwd=paths['combined'],text=True,capture_output=True)
    result={'mode':args.mode,'revision':revision,'elapsed_seconds':time.monotonic()-started,
            'codex_exit':run.returncode,'holdout_exit':verified.returncode,'holdout_output':verified.stdout+verified.stderr,
            'paths':paths}
    (root/'metrics.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)


if __name__ == '__main__': main()
