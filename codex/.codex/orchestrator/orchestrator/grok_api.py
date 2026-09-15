"""CLI and MCP entry points for the five Grok bridge operations."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Literal

from .grok_bridge import Bridge

INSTRUCTIONS = '''Astra owns planning, review, and next steps. Delegate bounded tasks to Grok.
Include objective, relevant context and paths, constraints, and observable completion criteria
in task. Empty write_scope means read-only; writers require separate linked worktrees.
Default Grok medium; choose high for difficult work, xhigh before escalating the hardest
problems to a native Astra high subagent. Grok workers must not spawn subagents.
After spawn/resume, do useful work or wait until terminal. Pending is not completion.
Review the worker report and evidence; execution completed does not prove correctness.
Use inspect for tool history, and resume the exact session for related fixes or missing evidence.
Use a fresh request ID for new work; retry identical requests with the original ID.
After an interrupted run, inspect worktree/history and external effects before recovery_checked.
Wait cursors apply to a fixed run set; start at zero for a new set. Results remain inspectable.
The bridge does not wake an idle/exited coordinator or integrate with native subagent UI.'''


def server(bridge):
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP('grok-bridge', instructions=INSTRUCTIONS)

    @mcp.tool()
    async def spawn(task: str, cwd: str, request_id: str, write_scope: list[str] | None = None,
                    effort: Literal['low', 'medium', 'high', 'xhigh'] = 'medium') -> dict:
        """Start a bounded headless Grok task; return durable run/session IDs promptly."""
        return await asyncio.to_thread(bridge.spawn, task, cwd, request_id, write_scope, effort)

    @mcp.tool()
    async def wait(run_ids: list[str], after: int = 0, timeout: float = 30) -> dict:
        """Collect terminal reports or pending status; timeout is 0..30 seconds."""
        return await asyncio.to_thread(bridge.wait, run_ids, after, timeout)

    @mcp.tool()
    async def inspect(run_id: str | None = None, session_id: str | None = None,
                      after: int = 0, limit: int = 100) -> dict:
        """List runs, or read a report and bounded message/tool history (limit 1..200)."""
        return await asyncio.to_thread(bridge.inspect, run_id, session_id, after, limit)

    @mcp.tool()
    async def resume(session_id: str, task: str, request_id: str,
                     effort: Literal['low', 'medium', 'high', 'xhigh'] = 'medium',
                     recovery_checked: bool = False) -> dict:
        """Continue the exact Grok conversation in a distinct run; busy sessions reject."""
        return await asyncio.to_thread(bridge.resume, session_id, task, request_id, effort, recovery_checked)

    @mcp.tool()
    async def cancel(run_id: str) -> dict:
        """Request owned process termination; inspect/wait for observed settlement."""
        return await asyncio.to_thread(bridge.cancel, run_id)

    return mcp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path)
    parser.add_argument('operation', choices=('mcp', 'spawn', 'wait', 'inspect', 'resume', 'cancel'))
    parser.add_argument('--input', type=Path, help='JSON arguments file; otherwise read stdin')
    args = parser.parse_args()
    os.umask(0o077)
    bridge = Bridge(args.home)
    if args.operation == 'mcp':
        server(bridge).run(transport='stdio')
        return 0
    import sys
    try:
        inputs = json.loads(args.input.read_text() if args.input else sys.stdin.read() or '{}')
        result = getattr(bridge, args.operation)(**inputs)
    except (ValueError, TypeError, OSError) as error:
        print(json.dumps({'error': str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
