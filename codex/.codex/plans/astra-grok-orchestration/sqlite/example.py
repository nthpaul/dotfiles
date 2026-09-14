"""Build a synthetic, inspectable database. No model, tmux, git, or network calls."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parent
TEAM = "demo"
NOW = 1_789_387_200_000


def database():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript((ROOT / "schema.sql").read_text())
    return connection


def insert(connection, table, **values):
    # Identifiers are code-owned constants; all data is bound as parameters.
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values())
    )


def event(connection, event_id, *, actor="coordinator-session", kind="coordinator_command",
          event_type="note", task_id=None, run_id=None, revision=None, priority="normal", body=None):
    sequence = connection.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE team_id = ?", (TEAM,)
    ).fetchone()[0]
    epoch = connection.execute("SELECT current_epoch FROM teams WHERE team_id = ?", (TEAM,)).fetchone()[0]
    request_id = f"request-{event_id}"
    payload = {"type": event_type, "body": body or event_id, "task_id": task_id,
               "run_id": run_id, "revision": revision, "priority": priority}
    insert(connection, "command_requests", team_id=TEAM, request_id=request_id,
           actor_session_id=actor, kind=kind, authority_epoch=epoch if kind == "coordinator_command" else None,
           canonical_body=json.dumps(payload, sort_keys=True, separators=(",", ":")),
           receipt_event_id=event_id, committed_at=NOW + sequence)
    insert(connection, "events", team_id=TEAM, sequence=sequence, event_id=event_id,
           request_id=request_id, type=event_type, task_id=task_id, run_id=run_id,
           revision=revision, priority=priority, body=body or event_id, committed_at=NOW + sequence)
    return event_id


def deliver(connection, event_id, agent_id, session_id, *, acknowledged=False):
    insert(connection, "deliveries", team_id=TEAM, event_id=event_id, recipient_agent_id=agent_id,
           state="delivered", delivered_at=NOW + 100)
    insert(connection, "delivery_attempts", team_id=TEAM, event_id=event_id, recipient_agent_id=agent_id,
           attempt_number=1, target_session_id=session_id, state="submitted", adapter_receipt="synthetic",
           started_at=NOW + 99, finished_at=NOW + 100)
    if acknowledged:
        insert(connection, "recipient_receipts", team_id=TEAM, event_id=event_id,
               recipient_agent_id=agent_id, accepted_session_id=session_id,
               protocol_receipt=f"synthetic-ack-{event_id}", accepted_at=NOW + 101)


def plan(connection, revision):
    insert(connection, "plan_revisions", team_id=TEAM, revision=revision, state="draft",
           summary=f"Demo revision {revision}", decisions="Coordinator reviews all results.", created_at=NOW)
    for task_id in ("contract", "implementation", "integration"):
        insert(connection, "task_specs", team_id=TEAM, task_id=task_id, revision=revision,
               objective=f"Complete {task_id}", context="Synthetic example only.",
               write_scope=f"Exclusive demo worktree for {task_id}", expected_output="Versioned artifact and evidence")
        insert(connection, "acceptance_criteria", team_id=TEAM, task_id=task_id, revision=revision,
               criterion_id="verified", description="Validate the required output.")
    for task_id, dependency in (("implementation", "contract"), ("integration", "contract"),
                                ("integration", "implementation")):
        insert(connection, "task_dependencies", team_id=TEAM, revision=revision,
               task_id=task_id, depends_on_task_id=dependency)


def seed(connection):
    with connection:
        insert(connection, "teams", team_id=TEAM, name="Model-neutral example",
               objective="Inspect the orchestration data model", state="active", created_at=NOW)
        insert(connection, "teams", team_id="other-team", name="Isolation boundary",
               objective="Exercise composite foreign keys", created_at=NOW)
        for profile_id, provider, model in (("planner", "provider-a", "demo-planner-model"),
                                             ("worker", "provider-b", "demo-worker-model")):
            insert(connection, "execution_profiles", team_id=TEAM, profile_id=profile_id,
                   name=profile_id, provider=provider, model=model, adapter="demo-json-lines",
                   adapter_version="fixture-1", settings_json='{"temperature":0}', created_at=NOW)
            for capability in ("launch", "stream", "acknowledge", "deduplicate", "follow_up",
                               "resume_session", "pause", "cancel", "wake_exact_session", "observe_execution"):
                insert(connection, "profile_capabilities", team_id=TEAM, profile_id=profile_id,
                       capability=capability, support="unverified", semantics="Fixture; no transport verification.")
        for agent_id, role, profile in (("coordinator", "coordinator", "planner"),
                                       ("worker-a", "worker", "worker"),
                                       ("worker-b", "worker", "planner"),
                                       ("runtime", "runtime", None)):
            insert(connection, "agents", team_id=TEAM, agent_id=agent_id, name=agent_id, role=role,
                   default_profile_id=profile, created_at=NOW)
            insert(connection, "sessions", team_id=TEAM, session_id=f"{agent_id}-session", agent_id=agent_id,
                   kind="runtime" if role == "runtime" else "model", profile_id=profile,
                   external_session_id=f"synthetic-{agent_id}" if profile else None,
                   availability="available", activity="available", created_at=NOW)
        insert(connection, "ownership_epochs", team_id=TEAM, epoch=1,
               coordinator_session_id="coordinator-session", acquired_at=NOW, reason="Initial demo owner")
        connection.execute("UPDATE teams SET current_epoch=1, authority_state='owned' WHERE team_id=?", (TEAM,))
        for task_id in ("contract", "implementation", "integration"):
            insert(connection, "tasks", team_id=TEAM, task_id=task_id, title=task_id, created_at=NOW)
        plan(connection, 1)
        connection.execute("UPDATE plan_revisions SET state='current' WHERE team_id=? AND revision=1", (TEAM,))

        # A completed first task and a second task that is still executing a tool.
        for number, task_id, agent_id in ((1, "contract", "worker-a"), (2, "implementation", "worker-b")):
            run_id = f"run-{number}"
            insert(connection, "runs", team_id=TEAM, run_id=run_id, task_id=task_id,
                   agent_id=agent_id, session_id=f"{agent_id}-session", attempt_number=1,
                   created_epoch=1, created_at=NOW)
            assignment_event = event(connection, f"assign-{number}", event_type="assignment",
                                     task_id=task_id, run_id=run_id, revision=1)
            insert(connection, "assignments", team_id=TEAM, assignment_id=f"assignment-{number}",
                   run_id=run_id, task_id=task_id, revision=1, generation=1,
                   event_id=assignment_event, instructions=f"Execute {task_id}", created_at=NOW)
            connection.execute("UPDATE runs SET current_assignment_id=? WHERE team_id=? AND run_id=?",
                               (f"assignment-{number}", TEAM, run_id))
            if number == 1:
                connection.execute("UPDATE runs SET health='running', observed_execution='executing' WHERE team_id=? AND run_id=?",
                                   (TEAM, run_id))
                connection.execute("UPDATE tasks SET state='running', owner_agent_id=? WHERE team_id=? AND task_id=?",
                                   (agent_id, TEAM, task_id))
            deliver(connection, assignment_event, agent_id, f"{agent_id}-session", acknowledged=True)

        for artifact_id, filename in (("contract-output", "contract.txt"), ("check-evidence", "checks.txt")):
            content = (ROOT / "demo-artifacts" / filename).read_bytes()
            insert(connection, "artifacts", team_id=TEAM, artifact_id=artifact_id, logical_name=filename,
                   artifact_version=1, uri=f"demo-artifacts/{filename}", media_type="text/plain",
                   finalization="finalized", sha256=hashlib.sha256(content).hexdigest(), byte_count=len(content),
                   integrity="valid", checked_at=NOW, created_at=NOW)
        result_event = event(connection, "contract-result", actor="worker-a-session", kind="worker_report",
                             event_type="result", task_id="contract", run_id="run-1", revision=1)
        deliver(connection, result_event, "coordinator", "coordinator-session", acknowledged=True)
        insert(connection, "results", team_id=TEAM, result_id="result-1", task_id="contract", run_id="run-1",
               assignment_id="assignment-1", event_id=result_event, summary="Synthetic contract result", created_at=NOW)
        for artifact_id, purpose in (("contract-output", "output"), ("check-evidence", "validation")):
            insert(connection, "result_artifacts", team_id=TEAM, result_id="result-1", artifact_id=artifact_id, purpose=purpose)
            insert(connection, "event_artifacts", team_id=TEAM, event_id=result_event, artifact_id=artifact_id)
        insert(connection, "acceptance_checks", team_id=TEAM, check_id="check-1", result_id="result-1", task_id="contract",
               revision=1, criterion_id="verified", attempt_number=1, state="passed", evidence_artifact_id="check-evidence",
               validator_session_id="worker-b-session", detail="Synthetic passing check; not a live validation.", checked_at=NOW)
        connection.execute("UPDATE runs SET outcome='result_reported', observed_execution='finished', released_at=?, health='exited' "
                           "WHERE team_id=? AND run_id='run-1'", (NOW + 200, TEAM))
        connection.execute("UPDATE tasks SET state='awaiting_review' WHERE team_id=? AND task_id='contract'", (TEAM,))
        review_event = event(connection, "accept-contract", event_type="review", task_id="contract", revision=1)
        insert(connection, "reviews", team_id=TEAM, review_id="review-1", result_id="result-1", task_id="contract",
               revision=1, review_number=1, compatibility="current", decision="accepted", event_id=review_event,
               rationale="Demo criteria and evidence are present.", created_at=NOW + 201)

        connection.execute("UPDATE runs SET health='running', observed_execution='executing' WHERE team_id=? AND run_id='run-2'", (TEAM,))
        connection.execute("UPDATE tasks SET state='running', owner_agent_id='worker-b' WHERE team_id=? AND task_id='implementation'", (TEAM,))

        urgent_event = event(connection, "urgent-conflict", actor="worker-b-session", kind="worker_report",
                             event_type="plan_conflict", task_id="implementation", run_id="run-2", revision=1,
                             priority="urgent", body="Current tool is running; the next step needs a revised contract.")
        deliver(connection, urgent_event, "coordinator", "coordinator-session", acknowledged=True)
        insert(connection, "issues", team_id=TEAM, issue_id="issue-1", task_id="implementation",
               source_event_id=urgent_event, kind="conflict", coalesce_key="implementation:contract-shape",
               priority="urgent", created_at=NOW)
        insert(connection, "issue_events", team_id=TEAM, issue_id="issue-1", event_id=urgent_event)
        insert(connection, "dispatch_holds", team_id=TEAM, hold_id="hold-1", scope="task", task_id="implementation",
               reason="Unresolved contract conflict", source_event_id=urgent_event, created_at=NOW)
        connection.execute("UPDATE tasks SET state='blocked', reason='Contract conflict' WHERE team_id=? AND task_id='implementation'", (TEAM,))
        pause_event = event(connection, "pause-implementation", event_type="pause", task_id="implementation", run_id="run-2", revision=1)
        deliver(connection, pause_event, "worker-b", "worker-b-session", acknowledged=True)
        insert(connection, "control_requests", team_id=TEAM, control_id="control-1", run_id="run-2", generation=1,
               desired_execution="pause", outcome="pending", request_event_id=pause_event, requested_at=NOW)

        proposal_event = event(connection, "contract-proposal", actor="worker-a-session", kind="worker_report", event_type="proposal")
        deliver(connection, proposal_event, "coordinator", "coordinator-session", acknowledged=True)
        publication_event = event(connection, "publish-contract", event_type="publication")
        insert(connection, "proposals", team_id=TEAM, proposal_id="proposal-1", source_event_id=proposal_event,
               state="approved", decision_event_id=publication_event)
        insert(connection, "proposal_recipients", team_id=TEAM, proposal_id="proposal-1", suggested_agent_id="worker-b")
        insert(connection, "publications", team_id=TEAM, publication_id="publication-1", proposal_id="proposal-1",
               event_id=publication_event, actionable=1)
        deliver(connection, publication_event, "worker-b", "worker-b-session")
        insert(connection, "publication_recipients", team_id=TEAM, publication_id="publication-1",
               event_id=publication_event, recipient_agent_id="worker-b")
        insert(connection, "event_artifacts", team_id=TEAM, event_id=publication_event, artifact_id="contract-output")

        # A later plan leaves the old assignments/review intact for inspection.
        plan(connection, 2)
        connection.execute("UPDATE plan_revisions SET state='superseded' WHERE team_id=? AND revision=1", (TEAM,))
        connection.execute("UPDATE plan_revisions SET state='current' WHERE team_id=? AND revision=2", (TEAM,))
        compatibility_event = event(connection, "recheck-contract", event_type="compatibility_assessment", task_id="contract", revision=2)
        insert(connection, "compatibility_assessments", team_id=TEAM, assessment_id="assessment-1", result_id="result-1",
               task_id="contract", revision=2, assessment_number=1, state="compatible", event_id=compatibility_event,
               rationale="The accepted contract remains usable under revision 2.", created_at=NOW)

        resource_event = event(connection, "resource-observation", actor="runtime-session", kind="runtime_observation",
                               event_type="reconciliation", body="Synthetic resource registry snapshot")
        for number, session_id, run_id in ((1, "worker-a-session", "run-1"), (2, "worker-b-session", "run-2"),
                                            (3, "runtime-session", None)):
            operation_id = f"launch-{number}"
            insert(connection, "operations", team_id=TEAM, operation_id=operation_id, run_id=run_id,
                   kind="launch_process", target=f"demo-process-{number}", intent_event_id=resource_event,
                   state="succeeded", created_at=NOW, finished_at=NOW + 1)
            insert(connection, "panes", team_id=TEAM, pane_id=f"pane-{number}", host_id="demo-host",
                   server_identity="synthetic-server-start", window_handle="@1", pane_handle=f"%{number}",
                   purpose="runtime_status" if number == 3 else "worker",
                   state="idle" if number == 1 else "occupied", owning_session_id=session_id,
                   reservation_operation_id=operation_id, created_at=NOW)
            insert(connection, "processes", team_id=TEAM, process_id=f"process-{number}", host_id="demo-host",
                   boot_id="synthetic-boot", pid=900_000 + number, start_identity=f"synthetic-start-{number}",
                   session_id=session_id, run_id=run_id, pane_id=f"pane-{number}", launch_operation_id=operation_id,
                   health="exited" if number == 1 else "running", observed_at=NOW)
        insert(connection, "runtime_instances", team_id=TEAM, runtime_id="runtime-1", session_id="runtime-session",
               process_id="process-3", lifecycle="ready", health="healthy", started_at=NOW)
        insert(connection, "operations", team_id=TEAM, operation_id="tool-2", run_id="run-2", kind="tool_call",
               target="synthetic long-running tool", intent_event_id=resource_event, state="in_flight", created_at=NOW)
        for number, task_id in ((1, "contract"), (2, "implementation"), (3, "integration")):
            operation_id = f"worktree-operation-{number}"
            insert(connection, "operations", team_id=TEAM, operation_id=operation_id, kind="create_worktree",
                   target=f"/demo/{task_id}", intent_event_id=resource_event, state="succeeded", created_at=NOW, finished_at=NOW)
            insert(connection, "worktrees", team_id=TEAM, worktree_id=f"worktree-{number}", host_id="demo-host",
                   repository_path="/demo/repository", path=f"/demo/{task_id}", branch=f"demo/{task_id}",
                   base_commit="synthetic-base", state="in_use" if number == 2 else "ready", provisioning_operation_id=operation_id)
            insert(connection, "write_scopes", team_id=TEAM, scope_id=f"scope-{number}", worktree_id=f"worktree-{number}",
                   resource_key="whole_worktree", description="Exclusive whole-worktree write access")
            if number <= 2:
                insert(connection, "scope_claims", team_id=TEAM, claim_id=f"claim-{number}", scope_id=f"scope-{number}",
                       run_id=f"run-{number}", epoch=1, state="released" if number == 1 else "held", acquired_at=NOW,
                       released_at=NOW + 200 if number == 1 else None, release_event_id=resource_event if number == 1 else None)
        insert(connection, "integration_changes", team_id=TEAM, change_id="change-1", integration_task_id="integration",
               source_review_id="review-1", worktree_id="worktree-3", state="pending", source_commit="synthetic-contract-commit")
        insert(connection, "pull_requests", team_id=TEAM, pr_id="pr-1", integration_task_id="integration",
               repository="demo/repository", branch="demo/integration", head_commit="synthetic-head", publication_state="local")
        insert(connection, "ci_checks", team_id=TEAM, pr_id="pr-1", head_commit="synthetic-head", name="required-tests",
               attempt_number=1, required=1, state="not_run", observed_at=NOW)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=ROOT / "example.sqlite3")
    args = parser.parse_args()
    connection = database()
    seed(connection)
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not connection.execute("PRAGMA foreign_key_check").fetchall()
    # Exclusive creation prevents accidental replacement of an existing database.
    with args.output.open("xb"):
        pass
    with sqlite3.connect(args.output) as output:
        connection.backup(output)
    output.close()
    connection.close()
    print(f"Created synthetic example: {args.output.resolve()}")


if __name__ == "__main__":
    main()
