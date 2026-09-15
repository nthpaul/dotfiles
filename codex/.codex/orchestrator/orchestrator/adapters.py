"""Explicit-session provider commands and stateless NDJSON normalization.

Callers execute argv directly (never through a shell), with stdin=DEVNULL and cwd
set to the assignment worktree. Prompts are argv and therefore visible in ps.
Results are candidates for review, never acceptance or delivery acknowledgment.
"""
import json
import sys
import uuid


def _session(value: str) -> str:
    """Reject names, --last, and accidental option values for exact routing."""
    return str(uuid.UUID(value))


def capabilities(adapter: str) -> dict:
    if adapter not in {"codex", "grok", "fake"}:
        raise ValueError(f"Unknown adapter: {adapter}")
    return {
        "streaming": True,
        "text_deltas": adapter == "grok",
        "explicit_resume": True,
        "live_steering": False,
        "protocol_ack": False,
        "cooperative_pause": False,
        "process_group_signals": True,
        "predetermined_session": adapter in {"grok", "fake"},
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
