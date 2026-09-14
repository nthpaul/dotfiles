"""Executable checks for the proposed schema's integrity and recovery boundaries."""

import sqlite3
import unittest

from example import NOW, TEAM, database, event, insert, plan, seed


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = database()
        seed(self.db)

    def tearDown(self):
        self.db.close()

    def scalar(self, sql, parameters=()):
        return self.db.execute(sql, parameters).fetchone()[0]

    def rejected(self, sql, parameters=(), message=None):
        with self.assertRaises(sqlite3.IntegrityError) as error:
            self.db.execute(sql, parameters)
        if message:
            self.assertIn(message, str(error.exception))

    def prepare_second_result(self):
        result_event = event(self.db, "second-result", actor="worker-b-session", kind="worker_report",
                             event_type="result", task_id="implementation", run_id="run-2", revision=1)
        insert(self.db, "results", team_id=TEAM, result_id="result-2", task_id="implementation", run_id="run-2",
               assignment_id="assignment-2", event_id=result_event, summary="Synthetic result", created_at=NOW)
        for artifact_id, purpose in (("contract-output", "output"), ("check-evidence", "validation")):
            insert(self.db, "result_artifacts", team_id=TEAM, result_id="result-2", artifact_id=artifact_id, purpose=purpose)
        insert(self.db, "acceptance_checks", team_id=TEAM, check_id="second-check", result_id="result-2",
               task_id="implementation", revision=2, criterion_id="verified", attempt_number=1, state="passed",
               evidence_artifact_id="check-evidence", validator_session_id="worker-a-session", detail="Synthetic",
               checked_at=NOW)
        self.db.execute("UPDATE operations SET state='succeeded', finished_at=? WHERE operation_id='tool-2'", (NOW,))
        self.db.execute("UPDATE control_requests SET outcome='applied', confirmation_event_id=?, confirmed_at=?",
                        (result_event, NOW))
        self.db.execute("UPDATE runs SET outcome='result_reported', observed_execution='finished', released_at=? WHERE run_id='run-2'", (NOW,))
        self.db.execute("UPDATE tasks SET state='awaiting_review' WHERE task_id='implementation'")
        decision_event = event(self.db, "review-second-result", event_type="review", task_id="implementation", revision=2)
        insert(self.db, "compatibility_assessments", team_id=TEAM, assessment_id="assessment-2", result_id="result-2",
               task_id="implementation", revision=2, assessment_number=1, state="compatible", event_id=decision_event,
               rationale="Old result is compatible.", created_at=NOW)
        self.db.execute("UPDATE issues SET state='resolved', resolution_event_id=?, resolved_at=?", (decision_event, NOW))
        self.db.execute("UPDATE dispatch_holds SET cleared_event_id=?, cleared_at=?", (decision_event, NOW))
        return dict(team_id=TEAM, review_id="review-2", result_id="result-2", task_id="implementation", revision=2,
                    review_number=1, compatibility="compatible", assessment_id="assessment-2", decision="accepted", event_id=decision_event,
                    rationale="Original result is compatible with revision 2.", created_at=NOW)

    def test_complete_fixture_and_integrity(self):
        self.assertEqual(self.scalar("PRAGMA integrity_check"), "ok")
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])
        for row in self.db.execute("SELECT name FROM sqlite_schema WHERE type='table'"):
            self.assertGreater(self.scalar(f'SELECT COUNT(*) FROM "{row[0]}"'), 0, row[0])
        for row in self.db.execute("SELECT name FROM sqlite_schema WHERE type='view'"):
            self.db.execute(f'SELECT * FROM "{row[0]}"').fetchall()

    def test_roles_do_not_constrain_models(self):
        rows = self.db.execute("SELECT role, provider, model FROM agent_registry WHERE agent_id IN ('coordinator','worker-b')").fetchall()
        self.assertEqual({row[0] for row in rows}, {"coordinator", "worker"})
        self.assertEqual({row[2] for row in rows}, {"demo-planner-model"})
        self.assertEqual(self.scalar("SELECT COUNT(DISTINCT provider) FROM execution_profiles"), 2)

    def test_strict_types_and_enum_checks(self):
        self.rejected("UPDATE tasks SET required='maybe' WHERE task_id='integration'")
        self.rejected("UPDATE runs SET health='accepted' WHERE run_id='run-2'")

    def test_cross_team_reference_is_rejected(self):
        self.rejected("INSERT INTO tasks(team_id,task_id,title,owner_agent_id,created_at) VALUES('other-team','x','x','worker-b',0)")

    def test_duplicate_task_execution_is_rejected(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "UNIQUE"):
            insert(self.db, "runs", team_id=TEAM, run_id="duplicate", task_id="implementation", agent_id="worker-a",
                   session_id="worker-a-session", attempt_number=2, created_epoch=1, created_at=NOW)

    def test_duplicate_worker_execution_is_rejected(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "UNIQUE"):
            insert(self.db, "runs", team_id=TEAM, run_id="duplicate", task_id="integration", agent_id="worker-b",
                   session_id="worker-b-session", attempt_number=1, created_epoch=1, created_at=NOW)

    def test_unresolved_effect_prevents_release(self):
        self.rejected("UPDATE runs SET outcome='failed', observed_execution='finished', released_at=1 WHERE run_id='run-2'",
                      message="unresolved effects")

    def test_unresolved_control_prevents_release(self):
        self.db.execute("UPDATE operations SET state='succeeded' WHERE operation_id='tool-2'")
        self.rejected("UPDATE runs SET outcome='failed', observed_execution='finished', released_at=1 WHERE run_id='run-2'",
                      message="unresolved control")

    def test_released_run_cannot_resume(self):
        self.rejected("UPDATE runs SET observed_execution='executing', released_at=NULL WHERE run_id='run-1'",
                      message="released run")

    def test_session_profile_cannot_change_historical_run(self):
        self.rejected("UPDATE sessions SET profile_id='worker' WHERE session_id='worker-b-session'", message="immutable")

    def test_old_result_compatibility_is_not_assumed(self):
        plan(self.db, 3)
        self.db.execute("UPDATE plan_revisions SET state='superseded' WHERE revision=2")
        self.db.execute("UPDATE plan_revisions SET state='current' WHERE revision=3")
        row = self.db.execute("SELECT review_state, reviewed_revision, current_revision, current_compatibility FROM result_review_status").fetchone()
        self.assertEqual(tuple(row), ("accepted", 1, 3, "unchecked"))

    def test_compatibility_does_not_rewrite_historical_acceptance(self):
        row = self.db.execute("SELECT review_state, reviewed_revision, current_revision, current_compatibility FROM result_review_status").fetchone()
        self.assertEqual(tuple(row), ("accepted", 1, 2, "compatible"))

    def test_dependency_cycle_is_rejected(self):
        plan(self.db, 3)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "cycle"):
            insert(self.db, "task_dependencies", team_id=TEAM, revision=3, task_id="contract", depends_on_task_id="integration")

    def test_current_revision_cannot_gain_new_criteria(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "draft"):
            insert(self.db, "acceptance_criteria", team_id=TEAM, task_id="implementation", revision=2,
                   criterion_id="late-addition", description="Would silently change a published contract")

    def test_only_one_current_revision(self):
        plan(self.db, 3)
        self.rejected("UPDATE plan_revisions SET state='current' WHERE revision=3", message="UNIQUE")

    def test_event_history_is_immutable(self):
        self.rejected("UPDATE events SET body='rewritten' WHERE event_id='urgent-conflict'", message="append-only")
        self.rejected("DELETE FROM events WHERE event_id='urgent-conflict'", message="append-only")

    def test_request_receipt_requires_event_in_same_transaction(self):
        insert(self.db, "command_requests", team_id=TEAM, request_id="no-event", actor_session_id="runtime-session",
               kind="runtime_observation", canonical_body="{}", receipt_event_id="missing", committed_at=NOW)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.commit()
        self.db.rollback()
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM command_requests WHERE request_id='no-event'"), 0)

    def test_duplicate_request_id_cannot_mutate_receipt(self):
        row = dict(self.db.execute("SELECT * FROM command_requests LIMIT 1").fetchone())
        row["canonical_body"] = '{"changed":true}'
        with self.assertRaises(sqlite3.IntegrityError):
            insert(self.db, "command_requests", **row)
        self.rejected("UPDATE command_requests SET canonical_body='{}'", message="immutable")

    def test_stale_coordinator_is_rejected_after_takeover(self):
        insert(self.db, "sessions", team_id=TEAM, session_id="new-coordinator-session", agent_id="coordinator",
               kind="model", profile_id="worker", created_at=NOW + 1)
        insert(self.db, "ownership_epochs", team_id=TEAM, epoch=2, coordinator_session_id="new-coordinator-session",
               acquired_at=NOW + 1, reason="Recovery")
        self.db.execute("UPDATE teams SET current_epoch=2, authority_state='recovering' WHERE team_id='demo'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "stale"):
            insert(self.db, "command_requests", team_id=TEAM, request_id="old-owner", actor_session_id="coordinator-session",
                   kind="coordinator_command", authority_epoch=1, canonical_body="{}", receipt_event_id="missing", committed_at=NOW)
        self.assertEqual(self.scalar("SELECT released_at IS NULL FROM runs WHERE run_id='run-2'"), 1)

    def test_worker_cannot_send_to_worker(self):
        self.rejected("INSERT INTO deliveries(team_id,event_id,recipient_agent_id) VALUES('demo','contract-proposal','worker-b')",
                      message="only coordinator")

    def test_acknowledged_issue_stays_in_override_inbox(self):
        row = self.db.execute("SELECT delivery_state,needs_acknowledgment,needs_resolution FROM override_inbox").fetchone()
        self.assertEqual(tuple(row), ("acknowledged", 0, 1))

    def test_acknowledged_pause_is_not_applied(self):
        row = self.db.execute("SELECT desired_execution,control_outcome,observed_execution FROM current_controls WHERE run_id='run-2'").fetchone()
        self.assertEqual(tuple(row), ("pause", "pending", "executing"))
        self.rejected("UPDATE control_requests SET outcome='applied' WHERE control_id='control-1'")

    def test_acknowledgment_cannot_regress(self):
        self.rejected("UPDATE deliveries SET state='retry_wait', acknowledged_at=NULL WHERE event_id='urgent-conflict'",
                      message="regress")

    def test_late_acknowledgment_after_closed_delivery(self):
        self.db.execute("UPDATE deliveries SET state='closed', reason='Superseded' WHERE event_id='publish-contract'")
        insert(self.db, "recipient_receipts", team_id=TEAM, event_id="publish-contract", recipient_agent_id="worker-b",
               accepted_session_id="worker-b-session", protocol_receipt="late-ack", accepted_at=NOW + 999)
        row = self.db.execute("SELECT state,acknowledged_at FROM deliveries WHERE event_id='publish-contract'").fetchone()
        self.assertEqual(tuple(row), ("closed", NOW + 999))

    def test_cancel_cannot_be_undone_by_resume(self):
        cancel_event = event(self.db, "cancel-run", event_type="cancel", task_id="implementation", run_id="run-2")
        insert(self.db, "control_requests", team_id=TEAM, control_id="cancel", run_id="run-2", generation=2,
               desired_execution="cancel", request_event_id=cancel_event, requested_at=NOW)
        resume_event = event(self.db, "resume-run", event_type="resume", task_id="implementation", run_id="run-2")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "cancelled intent"):
            insert(self.db, "control_requests", team_id=TEAM, control_id="resume", run_id="run-2", generation=3,
                   desired_execution="run", request_event_id=resume_event, requested_at=NOW)

    def test_quarantined_scope_still_excludes_other_writers(self):
        self.db.execute("UPDATE scope_claims SET state='quarantined' WHERE claim_id='claim-2'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "UNIQUE"):
            insert(self.db, "scope_claims", team_id=TEAM, claim_id="duplicate", scope_id="scope-2", run_id="run-1",
                   epoch=1, state="held", acquired_at=NOW)

    def test_acceptance_requires_fresh_compatibility_decision(self):
        review = self.prepare_second_result()
        review["compatibility"] = "current"
        review["assessment_id"] = None
        with self.assertRaisesRegex(sqlite3.IntegrityError, "compatibility"):
            insert(self.db, "reviews", **review)

    def test_acceptance_rejects_missing_artifact(self):
        review = self.prepare_second_result()
        self.db.execute("UPDATE artifacts SET integrity='missing' WHERE artifact_id='contract-output'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "valid artifacts"):
            insert(self.db, "reviews", **review)

    def test_latest_failed_check_overrides_earlier_pass(self):
        review = self.prepare_second_result()
        insert(self.db, "acceptance_checks", team_id=TEAM, check_id="failed-retry", result_id="result-2", task_id="implementation",
               revision=2, criterion_id="verified", attempt_number=2, state="failed", validator_session_id="worker-a-session",
               detail="Later check found a problem", checked_at=NOW)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "checks have not passed"):
            insert(self.db, "reviews", **review)

    def test_compatible_result_accepts_atomically(self):
        review = self.prepare_second_result()
        insert(self.db, "reviews", **review)
        self.assertEqual(tuple(self.db.execute("SELECT state,accepted_review_id FROM tasks WHERE task_id='implementation'").fetchone()),
                         ("accepted", "review-2"))
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_worker_cannot_accept_result(self):
        review = self.prepare_second_result()
        review["event_id"] = "second-result"
        with self.assertRaisesRegex(sqlite3.IntegrityError, "coordinator authority"):
            insert(self.db, "reviews", **review)

    def test_finalized_artifact_and_accepted_task_are_immutable(self):
        self.rejected("UPDATE artifacts SET sha256=? WHERE artifact_id='contract-output'", ("0" * 64,), "immutable")
        self.rejected("UPDATE tasks SET state='queued', accepted_review_id=NULL WHERE task_id='contract'")

    def test_ci_evidence_is_for_current_head_and_latest_attempt(self):
        self.db.execute("UPDATE ci_checks SET state='passed'")
        self.db.execute("UPDATE pull_requests SET head_commit='new-head'")
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM current_ci_checks"), 0)
        for attempt, state in ((1, "passed"), (2, "failed")):
            insert(self.db, "ci_checks", team_id=TEAM, pr_id="pr-1", head_commit="new-head", name="required-tests",
                   attempt_number=attempt, required=1, state=state, observed_at=NOW)
        self.assertEqual(self.scalar("SELECT state FROM current_ci_checks"), "failed")


if __name__ == "__main__":
    unittest.main()
