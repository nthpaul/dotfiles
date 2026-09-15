"""Explicit-session provider commands and stateless NDJSON normalization.

Callers execute argv directly (never through a shell), with stdin=DEVNULL and cwd
set to the assignment worktree. Prompts are argv and therefore visible in ps.
Results are candidates for review, never acceptance or delivery acknowledgment.
"""
import json
from pathlib import Path
import sys
import uuid


def _session(value: str) -> str:
    """Reject names, --last, and accidental option values for exact routing."""
    return str(uuid.UUID(value))


def is_interactive(config: dict) -> bool:
    adapter = config.get("adapter")
    mode = config.get("mode")
    if mode == "exec":
        return False
    if mode == "interactive":
        return True
    return adapter == "grok"


def capabilities(adapter: str, mode: str | None = None) -> dict:
    if adapter not in {"codex", "grok", "fake"}:
        raise ValueError(f"Unknown adapter: {adapter}")
    interactive = is_interactive({"adapter": adapter, "mode": mode})
    return {
        "streaming": True,
        "text_deltas": adapter == "grok" and not interactive,
        "explicit_resume": True,
        "live_steering": False,
        "protocol_ack": False,
        "cooperative_pause": False,
        "process_group_signals": True,
        "predetermined_session": adapter in {"grok", "fake"},
        "visible_tui": interactive,
        "prompt_transport": "argv",
    }


def build_command(adapter: str, model: str, effort: str,
                  external_session_id: str | None, prompt: str, cwd: str) -> list[str]:
    capabilities(adapter)
    session = _session(external_session_id) if external_session_id else None
    if adapter == "codex":
        command = ["codex", "exec", "--json", "--skip-git-repo-check",
                   "-C", cwd,
                   "-c", "features.multi_agent=false", "-m", model,
                   "-c", f"model_reasoning_effort={json.dumps(effort)}"]
        if session:
            command += ["resume", session]
        return command + ["--", prompt]
    if adapter == "grok":
        command = ["grok", "--cwd", cwd, "--no-subagents", "--always-approve",
                   "--output-format", "streaming-messages-json", "--include-partial-messages",
                   "--model", model, "--reasoning-effort", effort]
        command += ["--resume", session] if session else ["--session-id", str(uuid.uuid4())]
        return command + ["--single=" + prompt]
    return [sys.executable, "-m", "orchestrator.fake_worker",
            "--session-id", session or str(uuid.uuid4()), "--prompt=" + prompt]


def build_interactive_command(model: str, effort: str, external_session_id: str,
                              prompt: str, cwd: str, resume: bool = False) -> list[str]:
    session = _session(external_session_id)
    command = ["grok", "--cwd", cwd, "--fullscreen", "--no-subagents", "--always-approve",
               "--model", model, "--reasoning-effort", effort]
    command += ["--resume", session] if resume else ["--session-id", session]
    return command + [prompt]


def harvest_tui_result(session_directory) -> str | None:
    path = Path(session_directory) / "updates.jsonl"
    if not path.is_file():
        return None
    chunks = []
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        update = (event.get("params") or {}).get("update") or {}
        if update.get("sessionUpdate") != "agent_message_chunk":
            continue
        content = update.get("content") or {}
        if content.get("type") == "text" and isinstance(content.get("text"), str):
            chunks.append(content["text"])
    text = "".join(chunks).strip()
    return text or None


def tui_turn_idle(session_directory) -> bool:
    path = Path(session_directory) / "updates.jsonl"
    if not path.is_file():
        return False
    pending = False
    saw_assistant = False
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        update = (event.get("params") or {}).get("update") or {}
        kind = update.get("sessionUpdate")
        status = str(update.get("status") or "").lower()
        if kind in {"tool_call", "tool_call_update"}:
            if status in {"pending", "in_progress", "running"}:
                pending = True
            elif status in {"completed", "failed", "cancelled"}:
                pending = False
        if kind == "agent_message_chunk":
            saw_assistant = True
    return saw_assistant and not pending


def build_wake_command(thread_id: str, message: str) -> list[str]:
    return ["codex", "queue", "--thread", _session(thread_id), "--message", message]


def parse_line(adapter: str, line: str) -> dict:
    """Ignore log noise and unknown records; preserve provider errors.

    Codex emits whole completed agent messages, not token deltas. Each is a
    candidate result; the runner retains the last one and requires successful
    turn/process completion. Grok final result replaces the accumulated deltas.
    """
    capabilities(adapter)
    try:
        event = json.loads(line)
    except (ValueError, TypeError):
        return {}
    if not isinstance(event, dict):
        return {}
    result = {}
    kind = event.get("type")
    sid = event.get("thread_id") if adapter != "grok" else event.get("session_id")
    if isinstance(sid, str):
        try:
            result["external_session_id"] = _session(sid)
        except ValueError:
            result["error"] = "Provider emitted an invalid session UUID"
    if adapter in {"codex", "fake"}:
        item = event.get("item")
        if kind == "item.completed" and isinstance(item, dict):
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                result.update(text=item["text"], result=item["text"])
        if kind in {"error", "turn.failed"}:
            error = event.get("error", event.get("message", "Provider failed"))
            result["error"] = error.get("message", str(error)) if isinstance(error, dict) else str(error)
    else:
        if kind == "stream_event":
            inner = event.get("event")
            delta = inner.get("delta") if isinstance(inner, dict) else None
            if isinstance(delta, dict) and delta.get("type") == "text_delta" and isinstance(delta.get("text"), str):
                result["text"] = delta["text"]
        elif kind == "result":
            if event.get("is_error") or event.get("subtype") not in {None, "success"}:
                result["error"] = str(event.get("result") or event.get("errors") or "Provider failed")
            elif isinstance(event.get("result"), str):
                result["result"] = event["result"]
        elif kind == "error":
            result["error"] = str(event.get("error", event.get("message", "Provider failed")))
    return result
