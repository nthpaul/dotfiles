"""Deterministic subprocess fixture. No model, tools, filesystem writes or network.

Prompts may contain one line `FAKE_SCRIPT=<JSON object>` with keys `progress`
(list of strings), `delay` (seconds between progress items), `result`, `error`,
and `exit_code`. Otherwise the worker returns a fixed successful result.
"""
import argparse
import json
import time


def emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()
    script = {}
    for line in args.prompt.splitlines():
        if line.startswith("FAKE_SCRIPT="):
            script = json.loads(line.removeprefix("FAKE_SCRIPT="))
            break
    emit({"type": "thread.started", "thread_id": args.session_id})
    emit({"type": "turn.started"})
    for index, progress in enumerate(script.get("progress", ["Working on assignment"])):
        emit({"type": "item.completed", "item": {"id": f"progress_{index}",
              "type": "agent_message", "text": str(progress)}})
        time.sleep(float(script.get("delay", 0)))
    if script.get("error"):
        emit({"type": "turn.failed", "error": {"message": str(script["error"])}})
        return int(script.get("exit_code", 1))
    emit({"type": "item.completed", "item": {"id": "final", "type": "agent_message",
          "text": str(script.get("result", "Fake worker completed assignment."))}})
    emit({"type": "turn.completed"})
    return int(script.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
