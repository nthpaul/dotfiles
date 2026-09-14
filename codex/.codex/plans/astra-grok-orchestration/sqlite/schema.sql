-- Proposed orchestration schema v1. SQLite >= 3.38 with JSON functions.
-- No provider/model identifiers are enums. All timestamps are Unix milliseconds.
-- The runtime is the sole writer. Enable these connection settings on EVERY connection.
PRAGMA foreign_keys = ON;
PRAGMA recursive_triggers = ON;
PRAGMA busy_timeout = 5000;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;

BEGIN IMMEDIATE;
PRAGMA user_version = 1;

-- IDENTITY AND EXECUTION CONFIGURATION -----------------------------------------

CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    objective TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'created'
        CHECK (state IN ('created', 'active', 'completed', 'cancelled')),
    authority_state TEXT NOT NULL DEFAULT 'unowned'
        CHECK (authority_state IN ('unowned', 'owned', 'recovering')),
    current_epoch INTEGER,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at INTEGER NOT NULL,
    CHECK ((authority_state = 'unowned' AND current_epoch IS NULL)
        OR (authority_state <> 'unowned' AND current_epoch IS NOT NULL)),
    FOREIGN KEY (team_id, current_epoch) REFERENCES ownership_epochs(team_id, epoch)
        DEFERRABLE INITIALLY DEFERRED
) STRICT;

CREATE TABLE execution_profiles (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    profile_id TEXT NOT NULL,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    adapter TEXT NOT NULL,
    adapter_version TEXT NOT NULL,
    endpoint TEXT,
    credential_ref TEXT, -- Reference to a credential store; never an API key.
    settings_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(settings_json) AND json_type(settings_json) = 'object'),
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, profile_id)
) STRICT;

CREATE TABLE profile_capabilities (
    team_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    capability TEXT NOT NULL CHECK (capability IN (
        'launch', 'stream', 'acknowledge', 'deduplicate', 'follow_up',
        'resume_session', 'pause', 'cancel', 'wake_exact_session', 'observe_execution')),
    support TEXT NOT NULL CHECK (support IN ('unverified', 'supported', 'unsupported')),
    semantics TEXT NOT NULL, -- E.g. pause only between tool calls.
    evidence_uri TEXT,
    checked_at INTEGER,
    PRIMARY KEY (team_id, profile_id, capability),
    FOREIGN KEY (team_id, profile_id) REFERENCES execution_profiles(team_id, profile_id),
    CHECK (support = 'unverified' OR (evidence_uri IS NOT NULL AND checked_at IS NOT NULL))
) STRICT;

CREATE TABLE agents (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    agent_id TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('coordinator', 'worker', 'runtime')),
    registration TEXT NOT NULL DEFAULT 'registered'
        CHECK (registration IN ('registered', 'retired')),
    default_profile_id TEXT,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, agent_id),
    FOREIGN KEY (team_id, default_profile_id) REFERENCES execution_profiles(team_id, profile_id)
) STRICT;

CREATE TABLE sessions (
    team_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('model', 'runtime')),
    profile_id TEXT,
    external_session_id TEXT, -- Opaque adapter handle, not a durable agent/run ID.
    availability TEXT NOT NULL DEFAULT 'unknown'
        CHECK (availability IN ('available', 'unavailable', 'unknown')),
    activity TEXT NOT NULL DEFAULT 'unknown'
        CHECK (activity IN ('available', 'busy', 'unresponsive', 'disconnected', 'unknown')),
    last_heartbeat_at INTEGER,
    last_substantive_event_at INTEGER,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, session_id),
    UNIQUE (team_id, agent_id, session_id),
    UNIQUE (team_id, profile_id, external_session_id),
    FOREIGN KEY (team_id, agent_id) REFERENCES agents(team_id, agent_id),
    FOREIGN KEY (team_id, profile_id) REFERENCES execution_profiles(team_id, profile_id),
    CHECK ((kind = 'model' AND profile_id IS NOT NULL)
        OR (kind = 'runtime' AND profile_id IS NULL))
) STRICT;

CREATE TABLE runtime_instances (
    team_id TEXT NOT NULL,
    runtime_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    process_id TEXT,
    lifecycle TEXT NOT NULL CHECK (lifecycle IN ('starting', 'reconciling', 'ready', 'draining', 'stopped')),
    health TEXT NOT NULL CHECK (health IN ('healthy', 'degraded', 'unavailable', 'unknown')),
    reason TEXT,
    started_at INTEGER NOT NULL,
    last_heartbeat_at INTEGER,
    PRIMARY KEY (team_id, runtime_id),
    UNIQUE (team_id, session_id),
    FOREIGN KEY (team_id, session_id) REFERENCES sessions(team_id, session_id),
    FOREIGN KEY (team_id, process_id) REFERENCES processes(team_id, process_id)
) STRICT;

CREATE TABLE ownership_epochs (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    epoch INTEGER NOT NULL CHECK (epoch > 0),
    coordinator_session_id TEXT NOT NULL,
    acquired_at INTEGER NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY (team_id, epoch),
    FOREIGN KEY (team_id, coordinator_session_id) REFERENCES sessions(team_id, session_id)
) STRICT;

-- DURABLE REQUEST RECEIPTS AND APPEND-ONLY EVENTS ------------------------------
-- Deferred receipt FK allows the receipt and its event(s) to commit together.

CREATE TABLE command_requests (
    team_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    actor_session_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('coordinator_command', 'worker_report', 'runtime_observation')),
    authority_epoch INTEGER,
    canonical_body TEXT NOT NULL CHECK (json_valid(canonical_body) AND json_type(canonical_body) = 'object'),
    receipt_event_id TEXT NOT NULL,
    committed_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, request_id),
    UNIQUE (team_id, request_id, receipt_event_id),
    FOREIGN KEY (team_id, actor_session_id) REFERENCES sessions(team_id, session_id),
    FOREIGN KEY (team_id, authority_epoch) REFERENCES ownership_epochs(team_id, epoch),
    FOREIGN KEY (team_id, request_id, receipt_event_id)
        REFERENCES events(team_id, request_id, event_id) DEFERRABLE INITIALLY DEFERRED,
    CHECK (kind <> 'coordinator_command' OR authority_epoch IS NOT NULL)
) STRICT;

CREATE TABLE events (
    team_id TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK (sequence > 0), -- Allocate per team inside the write transaction.
    event_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version > 0),
    type TEXT NOT NULL, -- Extensible protocol event name; runtime validates its payload schema.
    task_id TEXT,
    run_id TEXT,
    revision INTEGER,
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('normal', 'urgent')),
    body TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(metadata_json) AND json_type(metadata_json) = 'object'),
    reply_to_event_id TEXT,
    occurred_at INTEGER,
    committed_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, sequence),
    UNIQUE (team_id, event_id),
    UNIQUE (team_id, request_id, event_id),
    FOREIGN KEY (team_id, request_id) REFERENCES command_requests(team_id, request_id),
    FOREIGN KEY (team_id, task_id) REFERENCES tasks(team_id, task_id),
    FOREIGN KEY (team_id, task_id, run_id) REFERENCES runs(team_id, task_id, run_id),
    FOREIGN KEY (team_id, revision) REFERENCES plan_revisions(team_id, revision),
    FOREIGN KEY (team_id, reply_to_event_id) REFERENCES events(team_id, event_id),
    CHECK (run_id IS NULL OR task_id IS NOT NULL)
) STRICT;

-- VERSIONED PLANS AND TASKS ---------------------------------------------------

CREATE TABLE plan_revisions (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    revision INTEGER NOT NULL CHECK (revision > 0),
    state TEXT NOT NULL CHECK (state IN ('draft', 'current', 'superseded', 'abandoned')),
    summary TEXT NOT NULL,
    decisions TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, revision)
) STRICT;
CREATE UNIQUE INDEX one_current_revision ON plan_revisions(team_id) WHERE state = 'current';

CREATE TABLE tasks (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    task_id TEXT NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued', 'running', 'blocked', 'awaiting_review', 'accepted', 'failed', 'cancelled')),
    owner_agent_id TEXT,
    follow_up_to_task_id TEXT,
    required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0, 1)),
    reason TEXT,
    accepted_review_id TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, task_id),
    FOREIGN KEY (team_id, owner_agent_id) REFERENCES agents(team_id, agent_id),
    FOREIGN KEY (team_id, follow_up_to_task_id) REFERENCES tasks(team_id, task_id),
    FOREIGN KEY (team_id, task_id, accepted_review_id) REFERENCES reviews(team_id, task_id, review_id),
    CHECK ((state = 'accepted' AND accepted_review_id IS NOT NULL)
        OR (state <> 'accepted' AND accepted_review_id IS NULL)),
    CHECK (follow_up_to_task_id IS NULL OR follow_up_to_task_id <> task_id)
) STRICT;

CREATE TABLE task_specs (
    team_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    objective TEXT NOT NULL,
    context TEXT NOT NULL,
    write_scope TEXT NOT NULL, -- Human contract; enforced resource claims are separate.
    expected_output TEXT NOT NULL,
    PRIMARY KEY (team_id, task_id, revision),
    FOREIGN KEY (team_id, task_id) REFERENCES tasks(team_id, task_id),
    FOREIGN KEY (team_id, revision) REFERENCES plan_revisions(team_id, revision)
) STRICT;

CREATE TABLE task_dependencies (
    team_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    PRIMARY KEY (team_id, revision, task_id, depends_on_task_id),
    FOREIGN KEY (team_id, task_id, revision) REFERENCES task_specs(team_id, task_id, revision),
    FOREIGN KEY (team_id, depends_on_task_id, revision) REFERENCES task_specs(team_id, task_id, revision),
    CHECK (task_id <> depends_on_task_id)
) STRICT;

CREATE TABLE acceptance_criteria (
    team_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    criterion_id TEXT NOT NULL,
    description TEXT NOT NULL,
    required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0, 1)),
    PRIMARY KEY (team_id, task_id, revision, criterion_id),
    FOREIGN KEY (team_id, task_id, revision) REFERENCES task_specs(team_id, task_id, revision)
) STRICT;

-- RUNS, ASSIGNMENT GENERATIONS, DISPATCH HOLDS, AND CONTROL ---------------------

CREATE TABLE runs (
    team_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    created_epoch INTEGER NOT NULL,
    current_assignment_id TEXT,
    health TEXT NOT NULL DEFAULT 'starting'
        CHECK (health IN ('starting', 'running', 'unresponsive', 'exited', 'unknown')),
    outcome TEXT NOT NULL DEFAULT 'open'
        CHECK (outcome IN ('open', 'result_reported', 'failed', 'cancelled', 'superseded')),
    observed_execution TEXT NOT NULL DEFAULT 'not_started'
        CHECK (observed_execution IN ('not_started', 'executing', 'paused', 'finished', 'unknown')),
    last_heartbeat_at INTEGER,
    last_substantive_event_at INTEGER,
    created_at INTEGER NOT NULL,
    released_at INTEGER, -- Holds the exclusive slot until execution is accounted for.
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    PRIMARY KEY (team_id, run_id),
    UNIQUE (team_id, task_id, run_id),
    UNIQUE (team_id, session_id, run_id),
    UNIQUE (team_id, task_id, attempt_number),
    FOREIGN KEY (team_id, task_id) REFERENCES tasks(team_id, task_id),
    FOREIGN KEY (team_id, agent_id, session_id) REFERENCES sessions(team_id, agent_id, session_id),
    FOREIGN KEY (team_id, created_epoch) REFERENCES ownership_epochs(team_id, epoch),
    FOREIGN KEY (team_id, run_id, current_assignment_id) REFERENCES assignments(team_id, run_id, assignment_id),
    CHECK (released_at IS NULL OR (observed_execution = 'finished' AND outcome <> 'open')),
    CHECK (observed_execution <> 'executing' OR current_assignment_id IS NOT NULL)
) STRICT;
CREATE UNIQUE INDEX one_unreleased_run_per_task ON runs(team_id, task_id) WHERE released_at IS NULL;
CREATE UNIQUE INDEX one_unreleased_run_per_agent ON runs(team_id, agent_id) WHERE released_at IS NULL;
CREATE UNIQUE INDEX one_unreleased_run_per_session ON runs(team_id, session_id) WHERE released_at IS NULL;

CREATE TABLE assignments (
    team_id TEXT NOT NULL,
    assignment_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    generation INTEGER NOT NULL CHECK (generation > 0),
    event_id TEXT NOT NULL,
    instructions TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, assignment_id),
    UNIQUE (team_id, run_id, assignment_id),
    UNIQUE (team_id, run_id, generation),
    UNIQUE (team_id, task_id, run_id, assignment_id),
    FOREIGN KEY (team_id, task_id, run_id) REFERENCES runs(team_id, task_id, run_id),
    FOREIGN KEY (team_id, task_id, revision) REFERENCES task_specs(team_id, task_id, revision),
    FOREIGN KEY (team_id, event_id) REFERENCES events(team_id, event_id)
) STRICT;

CREATE TABLE dispatch_holds (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    hold_id TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('team', 'task', 'profile')),
    task_id TEXT,
    profile_id TEXT,
    reason TEXT NOT NULL,
    source_event_id TEXT NOT NULL,
    cleared_event_id TEXT,
    created_at INTEGER NOT NULL,
    cleared_at INTEGER,
    PRIMARY KEY (team_id, hold_id),
    FOREIGN KEY (team_id, task_id) REFERENCES tasks(team_id, task_id),
    FOREIGN KEY (team_id, profile_id) REFERENCES execution_profiles(team_id, profile_id),
    FOREIGN KEY (team_id, source_event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, cleared_event_id) REFERENCES events(team_id, event_id),
    CHECK ((scope = 'team' AND task_id IS NULL AND profile_id IS NULL)
        OR (scope = 'task' AND task_id IS NOT NULL AND profile_id IS NULL)
        OR (scope = 'profile' AND task_id IS NULL AND profile_id IS NOT NULL)),
    CHECK ((cleared_at IS NULL) = (cleared_event_id IS NULL))
) STRICT;
CREATE INDEX active_holds ON dispatch_holds(team_id, scope, task_id, profile_id) WHERE cleared_at IS NULL;

CREATE TABLE control_requests (
    team_id TEXT NOT NULL,
    control_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    generation INTEGER NOT NULL CHECK (generation > 0),
    desired_execution TEXT NOT NULL CHECK (desired_execution IN ('run', 'pause', 'cancel')),
    outcome TEXT NOT NULL DEFAULT 'pending'
        CHECK (outcome IN ('pending', 'applied', 'rejected', 'uncertain', 'superseded')),
    request_event_id TEXT NOT NULL,
    confirmation_event_id TEXT,
    reason TEXT,
    requested_at INTEGER NOT NULL,
    confirmed_at INTEGER,
    PRIMARY KEY (team_id, control_id),
    UNIQUE (team_id, run_id, generation),
    FOREIGN KEY (team_id, run_id) REFERENCES runs(team_id, run_id),
    FOREIGN KEY (team_id, request_event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, confirmation_event_id) REFERENCES events(team_id, event_id),
    CHECK (outcome <> 'applied' OR (confirmation_event_id IS NOT NULL AND confirmed_at IS NOT NULL))
) STRICT;

-- TRANSPORT AND RECIPIENT DEDUPLICATION ----------------------------------------

CREATE TABLE deliveries (
    team_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    recipient_agent_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending', 'sending', 'delivered', 'acknowledged', 'retry_wait', 'uncertain', 'failed', 'closed')),
    delivered_at INTEGER,
    acknowledged_at INTEGER,
    next_attempt_at INTEGER,
    reason TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    PRIMARY KEY (team_id, event_id, recipient_agent_id),
    FOREIGN KEY (team_id, event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, recipient_agent_id) REFERENCES agents(team_id, agent_id),
    CHECK (state <> 'delivered' OR delivered_at IS NOT NULL),
    CHECK (state <> 'acknowledged' OR acknowledged_at IS NOT NULL),
    CHECK (acknowledged_at IS NULL OR state IN ('acknowledged', 'closed')),
    CHECK (state <> 'closed' OR reason IS NOT NULL)
) STRICT;
CREATE INDEX delivery_schedule ON deliveries(team_id, state, next_attempt_at);

CREATE TABLE delivery_attempts (
    team_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    recipient_agent_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    target_session_id TEXT NOT NULL,
    target_epoch INTEGER,
    state TEXT NOT NULL CHECK (state IN ('intended', 'in_flight', 'submitted', 'failed', 'uncertain')),
    adapter_receipt TEXT,
    error_code TEXT,
    error_detail TEXT,
    started_at INTEGER NOT NULL,
    finished_at INTEGER,
    PRIMARY KEY (team_id, event_id, recipient_agent_id, attempt_number),
    FOREIGN KEY (team_id, event_id, recipient_agent_id) REFERENCES deliveries(team_id, event_id, recipient_agent_id),
    FOREIGN KEY (team_id, recipient_agent_id, target_session_id) REFERENCES sessions(team_id, agent_id, session_id),
    FOREIGN KEY (team_id, target_epoch) REFERENCES ownership_epochs(team_id, epoch)
) STRICT;

CREATE TABLE recipient_receipts (
    team_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    recipient_agent_id TEXT NOT NULL,
    accepted_session_id TEXT NOT NULL,
    protocol_receipt TEXT NOT NULL,
    accepted_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, event_id, recipient_agent_id),
    FOREIGN KEY (team_id, event_id, recipient_agent_id) REFERENCES deliveries(team_id, event_id, recipient_agent_id),
    FOREIGN KEY (team_id, recipient_agent_id, accepted_session_id) REFERENCES sessions(team_id, agent_id, session_id)
) STRICT;

-- ISSUES AND COORDINATOR-MEDIATED PUBLICATION ----------------------------------

CREATE TABLE issues (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    issue_id TEXT NOT NULL,
    task_id TEXT,
    source_event_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('question', 'conflict', 'blocker')),
    coalesce_key TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'resolved', 'dismissed', 'superseded')),
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('normal', 'urgent')),
    blocks_acceptance INTEGER NOT NULL DEFAULT 1 CHECK (blocks_acceptance IN (0, 1)),
    resolution_event_id TEXT,
    superseded_by_issue_id TEXT,
    created_at INTEGER NOT NULL,
    resolved_at INTEGER,
    PRIMARY KEY (team_id, issue_id),
    UNIQUE (team_id, source_event_id),
    FOREIGN KEY (team_id, task_id) REFERENCES tasks(team_id, task_id),
    FOREIGN KEY (team_id, source_event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, resolution_event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, superseded_by_issue_id) REFERENCES issues(team_id, issue_id),
    CHECK ((state = 'open' AND resolved_at IS NULL AND resolution_event_id IS NULL)
        OR (state <> 'open' AND resolved_at IS NOT NULL AND resolution_event_id IS NOT NULL)),
    CHECK ((state = 'superseded' AND superseded_by_issue_id IS NOT NULL)
        OR (state <> 'superseded' AND superseded_by_issue_id IS NULL)),
    CHECK (superseded_by_issue_id IS NULL OR superseded_by_issue_id <> issue_id)
) STRICT;
CREATE UNIQUE INDEX one_open_issue_per_key ON issues(team_id, coalesce_key) WHERE state = 'open';

CREATE TABLE issue_events (
    team_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    PRIMARY KEY (team_id, issue_id, event_id),
    FOREIGN KEY (team_id, issue_id) REFERENCES issues(team_id, issue_id),
    FOREIGN KEY (team_id, event_id) REFERENCES events(team_id, event_id)
) STRICT;

CREATE TABLE proposals (
    team_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    source_event_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'approved', 'rejected', 'superseded')),
    decision_event_id TEXT,
    PRIMARY KEY (team_id, proposal_id),
    UNIQUE (team_id, source_event_id),
    FOREIGN KEY (team_id, source_event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, decision_event_id) REFERENCES events(team_id, event_id),
    CHECK ((state = 'pending' AND decision_event_id IS NULL)
        OR (state <> 'pending' AND decision_event_id IS NOT NULL))
) STRICT;

CREATE TABLE proposal_recipients (
    team_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    suggested_agent_id TEXT NOT NULL,
    PRIMARY KEY (team_id, proposal_id, suggested_agent_id),
    FOREIGN KEY (team_id, proposal_id) REFERENCES proposals(team_id, proposal_id),
    FOREIGN KEY (team_id, suggested_agent_id) REFERENCES agents(team_id, agent_id)
) STRICT;

CREATE TABLE publications (
    team_id TEXT NOT NULL,
    publication_id TEXT NOT NULL,
    proposal_id TEXT,
    event_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'current' CHECK (state IN ('current', 'superseded', 'withdrawn')),
    actionable INTEGER NOT NULL CHECK (actionable IN (0, 1)),
    disposition_event_id TEXT,
    PRIMARY KEY (team_id, publication_id),
    UNIQUE (team_id, publication_id, event_id),
    UNIQUE (team_id, event_id),
    FOREIGN KEY (team_id, proposal_id) REFERENCES proposals(team_id, proposal_id),
    FOREIGN KEY (team_id, event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, disposition_event_id) REFERENCES events(team_id, event_id),
    CHECK ((state = 'current' AND disposition_event_id IS NULL)
        OR (state <> 'current' AND disposition_event_id IS NOT NULL))
) STRICT;

CREATE TABLE publication_recipients (
    team_id TEXT NOT NULL,
    publication_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    recipient_agent_id TEXT NOT NULL,
    PRIMARY KEY (team_id, publication_id, recipient_agent_id),
    FOREIGN KEY (team_id, publication_id, event_id) REFERENCES publications(team_id, publication_id, event_id),
    FOREIGN KEY (team_id, event_id, recipient_agent_id) REFERENCES deliveries(team_id, event_id, recipient_agent_id)
        DEFERRABLE INITIALLY DEFERRED
) STRICT;

-- VERSIONED ARTIFACTS, RESULTS, CHECKS, AND REVIEW DECISIONS ---------------------

CREATE TABLE artifacts (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    artifact_id TEXT NOT NULL,
    logical_name TEXT NOT NULL,
    artifact_version INTEGER NOT NULL CHECK (artifact_version > 0),
    uri TEXT NOT NULL,
    media_type TEXT NOT NULL,
    finalization TEXT NOT NULL CHECK (finalization IN ('staging', 'finalized')),
    sha256 TEXT CHECK (sha256 IS NULL OR (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*')),
    byte_count INTEGER CHECK (byte_count IS NULL OR byte_count >= 0),
    integrity TEXT NOT NULL DEFAULT 'unchecked' CHECK (integrity IN ('unchecked', 'valid', 'missing', 'mismatch', 'unreadable')),
    checked_at INTEGER,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, artifact_id),
    UNIQUE (team_id, logical_name, artifact_version),
    CHECK (finalization <> 'finalized' OR (sha256 IS NOT NULL AND byte_count IS NOT NULL)),
    CHECK (integrity <> 'valid' OR (finalization = 'finalized' AND checked_at IS NOT NULL))
) STRICT;

CREATE TABLE event_artifacts (
    team_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    PRIMARY KEY (team_id, event_id, artifact_id),
    FOREIGN KEY (team_id, event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, artifact_id) REFERENCES artifacts(team_id, artifact_id)
) STRICT;

CREATE TABLE results (
    team_id TEXT NOT NULL,
    result_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    assignment_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, result_id),
    UNIQUE (team_id, task_id, result_id),
    UNIQUE (team_id, event_id),
    FOREIGN KEY (team_id, task_id, run_id, assignment_id)
        REFERENCES assignments(team_id, task_id, run_id, assignment_id),
    FOREIGN KEY (team_id, event_id) REFERENCES events(team_id, event_id)
) STRICT;

CREATE TABLE result_artifacts (
    team_id TEXT NOT NULL,
    result_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('output', 'validation', 'context')),
    PRIMARY KEY (team_id, result_id, artifact_id),
    FOREIGN KEY (team_id, result_id) REFERENCES results(team_id, result_id),
    FOREIGN KEY (team_id, artifact_id) REFERENCES artifacts(team_id, artifact_id)
) STRICT;

CREATE TABLE acceptance_checks (
    team_id TEXT NOT NULL,
    check_id TEXT NOT NULL,
    result_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL, -- Criteria revision being evaluated, not necessarily original assignment revision.
    criterion_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    state TEXT NOT NULL CHECK (state IN ('pending', 'passed', 'failed', 'inconclusive')),
    evidence_artifact_id TEXT,
    validator_session_id TEXT NOT NULL,
    detail TEXT NOT NULL,
    checked_at INTEGER,
    PRIMARY KEY (team_id, check_id),
    UNIQUE (team_id, result_id, revision, criterion_id, attempt_number),
    FOREIGN KEY (team_id, task_id, result_id) REFERENCES results(team_id, task_id, result_id),
    FOREIGN KEY (team_id, task_id, revision, criterion_id) REFERENCES acceptance_criteria(team_id, task_id, revision, criterion_id),
    FOREIGN KEY (team_id, result_id, evidence_artifact_id) REFERENCES result_artifacts(team_id, result_id, artifact_id),
    FOREIGN KEY (team_id, validator_session_id) REFERENCES sessions(team_id, session_id),
    CHECK (state <> 'passed' OR (evidence_artifact_id IS NOT NULL AND checked_at IS NOT NULL))
) STRICT;

CREATE TABLE compatibility_assessments (
    team_id TEXT NOT NULL,
    assessment_id TEXT NOT NULL,
    result_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    assessment_number INTEGER NOT NULL CHECK (assessment_number > 0),
    state TEXT NOT NULL CHECK (state IN ('compatible', 'incompatible')),
    event_id TEXT NOT NULL,
    rationale TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, assessment_id),
    UNIQUE (team_id, result_id, revision, assessment_number),
    UNIQUE (team_id, task_id, result_id, revision, assessment_id),
    FOREIGN KEY (team_id, task_id, result_id) REFERENCES results(team_id, task_id, result_id),
    FOREIGN KEY (team_id, task_id, revision) REFERENCES task_specs(team_id, task_id, revision),
    FOREIGN KEY (team_id, event_id) REFERENCES events(team_id, event_id)
) STRICT;

CREATE TABLE reviews (
    team_id TEXT NOT NULL,
    review_id TEXT NOT NULL,
    result_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    review_number INTEGER NOT NULL CHECK (review_number > 0),
    compatibility TEXT NOT NULL CHECK (compatibility IN ('current', 'unchecked', 'compatible', 'incompatible')),
    assessment_id TEXT,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'changes_requested', 'rejected', 'superseded')),
    event_id TEXT NOT NULL,
    rationale TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, review_id),
    UNIQUE (team_id, task_id, review_id),
    UNIQUE (team_id, result_id, review_number),
    FOREIGN KEY (team_id, task_id, result_id) REFERENCES results(team_id, task_id, result_id),
    FOREIGN KEY (team_id, task_id, revision) REFERENCES task_specs(team_id, task_id, revision),
    FOREIGN KEY (team_id, event_id) REFERENCES events(team_id, event_id),
    FOREIGN KEY (team_id, task_id, result_id, revision, assessment_id)
        REFERENCES compatibility_assessments(team_id, task_id, result_id, revision, assessment_id),
    CHECK ((compatibility IN ('current', 'unchecked') AND assessment_id IS NULL)
        OR (compatibility IN ('compatible', 'incompatible') AND assessment_id IS NOT NULL)),
    CHECK (decision <> 'accepted' OR compatibility IN ('current', 'compatible'))
) STRICT;

-- EFFECT INTENTS AND RESOURCE OWNERSHIP ---------------------------------------

CREATE TABLE operations (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    operation_id TEXT NOT NULL,
    run_id TEXT,
    parent_operation_id TEXT,
    retry_of_operation_id TEXT,
    kind TEXT NOT NULL, -- launch_process, create_pane, tool_call, submit_pr, etc.
    target TEXT NOT NULL,
    external_idempotency_key TEXT,
    external_correlation_id TEXT,
    intent_event_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('intended', 'in_flight', 'succeeded', 'failed', 'uncertain', 'cancelled')),
    outcome_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(outcome_json) AND json_type(outcome_json) = 'object'),
    created_at INTEGER NOT NULL,
    finished_at INTEGER,
    PRIMARY KEY (team_id, operation_id),
    FOREIGN KEY (team_id, run_id) REFERENCES runs(team_id, run_id),
    FOREIGN KEY (team_id, parent_operation_id) REFERENCES operations(team_id, operation_id),
    FOREIGN KEY (team_id, retry_of_operation_id) REFERENCES operations(team_id, operation_id),
    FOREIGN KEY (team_id, intent_event_id) REFERENCES events(team_id, event_id),
    CHECK (parent_operation_id IS NULL OR parent_operation_id <> operation_id),
    CHECK (retry_of_operation_id IS NULL OR retry_of_operation_id <> operation_id)
) STRICT;

CREATE TABLE panes (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    pane_id TEXT NOT NULL, -- Durable registry ID, distinct from tmux's %N handle.
    host_id TEXT NOT NULL,
    server_identity TEXT NOT NULL, -- Socket plus verified server start identity.
    window_handle TEXT,
    pane_handle TEXT,
    purpose TEXT NOT NULL CHECK (purpose IN ('coordinator', 'worker', 'runtime_status')),
    state TEXT NOT NULL CHECK (state IN ('reserved', 'idle', 'occupied', 'releasing', 'missing', 'uncertain')),
    owning_session_id TEXT,
    reservation_operation_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, pane_id),
    UNIQUE (host_id, server_identity, pane_handle),
    FOREIGN KEY (team_id, owning_session_id) REFERENCES sessions(team_id, session_id),
    FOREIGN KEY (team_id, reservation_operation_id) REFERENCES operations(team_id, operation_id),
    CHECK (state NOT IN ('idle', 'occupied') OR (window_handle IS NOT NULL AND pane_handle IS NOT NULL)),
    CHECK (state <> 'occupied' OR owning_session_id IS NOT NULL)
) STRICT;

CREATE TABLE processes (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    process_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    pid INTEGER NOT NULL CHECK (pid > 0),
    start_identity TEXT NOT NULL,
    parent_process_id TEXT,
    session_id TEXT,
    run_id TEXT,
    pane_id TEXT,
    launch_operation_id TEXT NOT NULL,
    health TEXT NOT NULL CHECK (health IN ('starting', 'running', 'unresponsive', 'exited', 'unknown')),
    exit_code INTEGER,
    exit_signal INTEGER,
    observed_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, process_id),
    UNIQUE (host_id, boot_id, pid, start_identity),
    FOREIGN KEY (team_id, parent_process_id) REFERENCES processes(team_id, process_id),
    FOREIGN KEY (team_id, session_id) REFERENCES sessions(team_id, session_id),
    FOREIGN KEY (team_id, run_id) REFERENCES runs(team_id, run_id),
    FOREIGN KEY (team_id, pane_id) REFERENCES panes(team_id, pane_id),
    FOREIGN KEY (team_id, launch_operation_id) REFERENCES operations(team_id, operation_id),
    FOREIGN KEY (team_id, session_id, run_id) REFERENCES runs(team_id, session_id, run_id),
    CHECK (run_id IS NULL OR session_id IS NOT NULL)
) STRICT;

CREATE TABLE worktrees (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    worktree_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    repository_path TEXT NOT NULL,
    path TEXT NOT NULL,
    branch TEXT NOT NULL,
    base_commit TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('provisioning', 'ready', 'in_use', 'releasing', 'released', 'failed', 'uncertain')),
    provisioning_operation_id TEXT NOT NULL,
    PRIMARY KEY (team_id, worktree_id),
    FOREIGN KEY (team_id, provisioning_operation_id) REFERENCES operations(team_id, operation_id)
) STRICT;
CREATE UNIQUE INDEX one_owned_worktree_path ON worktrees(host_id, path) WHERE state <> 'released';

CREATE TABLE write_scopes (
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    scope_id TEXT NOT NULL,
    worktree_id TEXT NOT NULL,
    resource_key TEXT NOT NULL, -- Canonical lock identity; v1 defaults to the whole worktree.
    description TEXT NOT NULL,
    PRIMARY KEY (team_id, scope_id),
    UNIQUE (team_id, worktree_id), -- V1 locks the whole worktree; no overlapping path-lock semantics.
    UNIQUE (team_id, worktree_id, resource_key),
    FOREIGN KEY (team_id, worktree_id) REFERENCES worktrees(team_id, worktree_id)
) STRICT;

CREATE TABLE scope_claims (
    team_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('held', 'quarantined', 'released')),
    acquired_at INTEGER NOT NULL,
    released_at INTEGER,
    release_event_id TEXT,
    PRIMARY KEY (team_id, claim_id),
    FOREIGN KEY (team_id, scope_id) REFERENCES write_scopes(team_id, scope_id),
    FOREIGN KEY (team_id, run_id) REFERENCES runs(team_id, run_id),
    FOREIGN KEY (team_id, epoch) REFERENCES ownership_epochs(team_id, epoch),
    FOREIGN KEY (team_id, release_event_id) REFERENCES events(team_id, event_id),
    CHECK ((state = 'released' AND released_at IS NOT NULL AND release_event_id IS NOT NULL)
        OR (state <> 'released' AND released_at IS NULL AND release_event_id IS NULL))
) STRICT;
CREATE UNIQUE INDEX one_live_claim_per_scope ON scope_claims(team_id, scope_id) WHERE state <> 'released';

-- INTEGRATION AND CI BY COMMIT ------------------------------------------------

CREATE TABLE integration_changes (
    team_id TEXT NOT NULL,
    change_id TEXT NOT NULL,
    integration_task_id TEXT NOT NULL,
    source_review_id TEXT NOT NULL,
    worktree_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'applying', 'conflicted', 'assembled', 'abandoned')),
    source_commit TEXT NOT NULL,
    integrated_commit TEXT,
    PRIMARY KEY (team_id, change_id),
    FOREIGN KEY (team_id, integration_task_id) REFERENCES tasks(team_id, task_id),
    FOREIGN KEY (team_id, source_review_id) REFERENCES reviews(team_id, review_id),
    FOREIGN KEY (team_id, worktree_id) REFERENCES worktrees(team_id, worktree_id),
    CHECK (state <> 'assembled' OR integrated_commit IS NOT NULL)
) STRICT;

CREATE TABLE pull_requests (
    team_id TEXT NOT NULL,
    pr_id TEXT NOT NULL,
    integration_task_id TEXT NOT NULL,
    parent_pr_id TEXT,
    repository TEXT NOT NULL,
    branch TEXT NOT NULL,
    head_commit TEXT NOT NULL,
    publication_state TEXT NOT NULL CHECK (publication_state IN ('local', 'submitting', 'published', 'uncertain', 'failed')),
    submission_operation_id TEXT,
    url TEXT,
    disposition TEXT CHECK (disposition IN ('open', 'merged', 'closed')),
    PRIMARY KEY (team_id, pr_id),
    UNIQUE (repository, url),
    FOREIGN KEY (team_id, integration_task_id) REFERENCES tasks(team_id, task_id),
    FOREIGN KEY (team_id, parent_pr_id) REFERENCES pull_requests(team_id, pr_id),
    FOREIGN KEY (team_id, submission_operation_id) REFERENCES operations(team_id, operation_id),
    CHECK (parent_pr_id IS NULL OR parent_pr_id <> pr_id),
    CHECK (publication_state <> 'published' OR (url IS NOT NULL AND disposition IS NOT NULL)),
    CHECK ((url IS NULL) = (disposition IS NULL))
) STRICT;

CREATE TABLE ci_checks (
    team_id TEXT NOT NULL,
    pr_id TEXT NOT NULL,
    head_commit TEXT NOT NULL,
    name TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    required INTEGER NOT NULL CHECK (required IN (0, 1)),
    state TEXT NOT NULL CHECK (state IN ('not_run', 'pending', 'passed', 'failed', 'cancelled', 'unavailable')),
    evidence_url TEXT,
    observed_at INTEGER NOT NULL,
    PRIMARY KEY (team_id, pr_id, head_commit, name, attempt_number),
    FOREIGN KEY (team_id, pr_id) REFERENCES pull_requests(team_id, pr_id)
) STRICT;

-- INTEGRITY GUARDS ------------------------------------------------------------

CREATE TRIGGER ownership_requires_coordinator BEFORE INSERT ON ownership_epochs
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM sessions s JOIN agents a USING (team_id, agent_id)
        WHERE s.team_id = NEW.team_id AND s.session_id = NEW.coordinator_session_id
            AND a.role = 'coordinator' AND a.registration = 'registered'
    ) THEN RAISE(ABORT, 'ownership requires a registered coordinator session') END;
    SELECT CASE WHEN NEW.epoch <> COALESCE((SELECT MAX(epoch) FROM ownership_epochs WHERE team_id = NEW.team_id), 0) + 1
        THEN RAISE(ABORT, 'ownership epoch must increase monotonically') END;
END;

CREATE TRIGGER team_epoch_cannot_regress BEFORE UPDATE OF current_epoch ON teams
WHEN NEW.current_epoch IS NOT NULL
BEGIN
    SELECT CASE WHEN NEW.current_epoch <> (SELECT MAX(epoch) FROM ownership_epochs WHERE team_id = NEW.team_id)
        THEN RAISE(ABORT, 'current ownership must use newest epoch') END;
END;

CREATE TRIGGER request_actor_and_epoch BEFORE INSERT ON command_requests
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM sessions s JOIN agents a USING (team_id, agent_id)
        WHERE s.team_id = NEW.team_id AND s.session_id = NEW.actor_session_id
          AND a.role = CASE NEW.kind WHEN 'coordinator_command' THEN 'coordinator'
              WHEN 'worker_report' THEN 'worker' ELSE 'runtime' END
    ) THEN RAISE(ABORT, 'request kind does not match actor role') END;
    SELECT CASE WHEN NEW.kind = 'coordinator_command' AND NOT EXISTS (
        SELECT 1 FROM teams t JOIN ownership_epochs o ON o.team_id = t.team_id AND o.epoch = t.current_epoch
        WHERE t.team_id = NEW.team_id AND t.authority_state IN ('owned', 'recovering')
          AND o.epoch = NEW.authority_epoch AND o.coordinator_session_id = NEW.actor_session_id
    ) THEN RAISE(ABORT, 'stale or unauthorized coordinator command') END;
END;

CREATE TRIGGER dependency_cycle BEFORE INSERT ON task_dependencies
BEGIN
    SELECT CASE WHEN EXISTS (
        WITH RECURSIVE reachable(task_id) AS (
            SELECT NEW.depends_on_task_id
            UNION
            SELECT d.depends_on_task_id FROM task_dependencies d JOIN reachable r ON d.task_id = r.task_id
            WHERE d.team_id = NEW.team_id AND d.revision = NEW.revision
        ) SELECT 1 FROM reachable WHERE task_id = NEW.task_id
    ) THEN RAISE(ABORT, 'task dependency cycle') END;
END;

CREATE TRIGGER event_sequence_increases BEFORE INSERT ON events
WHEN NEW.sequence <> COALESCE((SELECT MAX(sequence) FROM events WHERE team_id = NEW.team_id), 0) + 1
BEGIN SELECT RAISE(ABORT, 'event sequence must follow team commit order'); END;

CREATE TRIGGER tasks_start_queued BEFORE INSERT ON tasks
WHEN NEW.state <> 'queued'
BEGIN SELECT RAISE(ABORT, 'new tasks start queued'); END;

CREATE TRIGGER task_transition BEFORE UPDATE OF state ON tasks
WHEN NEW.state <> OLD.state AND NOT (
    (OLD.state = 'queued' AND NEW.state IN ('running', 'blocked', 'failed', 'cancelled')) OR
    (OLD.state = 'running' AND NEW.state IN ('awaiting_review', 'blocked', 'failed', 'cancelled')) OR
    (OLD.state = 'blocked' AND NEW.state IN ('running', 'queued', 'awaiting_review', 'failed', 'cancelled')) OR
    (OLD.state = 'awaiting_review' AND NEW.state IN ('accepted', 'running', 'queued', 'blocked', 'failed', 'cancelled')) OR
    (OLD.state = 'failed' AND NEW.state = 'queued')
)
BEGIN SELECT RAISE(ABORT, 'invalid task state transition'); END;

CREATE TRIGGER task_termination_requires_release BEFORE UPDATE OF state ON tasks
WHEN NEW.state IN ('failed', 'cancelled') AND EXISTS (
    SELECT 1 FROM runs WHERE team_id = NEW.team_id AND task_id = NEW.task_id AND released_at IS NULL)
BEGIN SELECT RAISE(ABORT, 'task termination requires execution slot release'); END;

CREATE TRIGGER task_specs_require_draft BEFORE INSERT ON task_specs
WHEN NOT EXISTS (SELECT 1 FROM plan_revisions WHERE team_id = NEW.team_id AND revision = NEW.revision AND state = 'draft')
BEGIN SELECT RAISE(ABORT, 'task specs require a draft revision'); END;

CREATE TRIGGER dependencies_require_draft BEFORE INSERT ON task_dependencies
WHEN NOT EXISTS (SELECT 1 FROM plan_revisions WHERE team_id = NEW.team_id AND revision = NEW.revision AND state = 'draft')
BEGIN SELECT RAISE(ABORT, 'dependencies require a draft revision'); END;

CREATE TRIGGER criteria_require_draft BEFORE INSERT ON acceptance_criteria
WHEN NOT EXISTS (SELECT 1 FROM plan_revisions WHERE team_id = NEW.team_id AND revision = NEW.revision AND state = 'draft')
BEGIN SELECT RAISE(ABORT, 'criteria require a draft revision'); END;

CREATE TRIGGER published_plan_is_immutable BEFORE UPDATE ON plan_revisions
WHEN (NEW.team_id <> OLD.team_id OR NEW.revision <> OLD.revision)
  OR (OLD.state <> 'draft' AND (NEW.summary <> OLD.summary OR NEW.decisions <> OLD.decisions))
  OR (NEW.state <> OLD.state AND NOT (
      (OLD.state = 'draft' AND NEW.state IN ('current', 'abandoned')) OR
      (OLD.state = 'current' AND NEW.state = 'superseded')))
BEGIN SELECT RAISE(ABORT, 'invalid plan mutation; create a new revision'); END;

CREATE TRIGGER session_binding_is_immutable BEFORE UPDATE ON sessions
WHEN NEW.team_id <> OLD.team_id OR NEW.session_id <> OLD.session_id OR NEW.agent_id <> OLD.agent_id
  OR NEW.profile_id IS NOT OLD.profile_id OR NEW.kind <> OLD.kind
  OR (OLD.external_session_id IS NOT NULL AND NEW.external_session_id IS NOT OLD.external_session_id)
BEGIN SELECT RAISE(ABORT, 'session identity and execution profile are immutable'); END;

CREATE TRIGGER run_binding_is_immutable BEFORE UPDATE ON runs
WHEN NEW.team_id <> OLD.team_id OR NEW.run_id <> OLD.run_id OR NEW.task_id <> OLD.task_id
  OR NEW.agent_id <> OLD.agent_id OR NEW.session_id <> OLD.session_id OR NEW.attempt_number <> OLD.attempt_number
  OR NEW.created_epoch <> OLD.created_epoch
BEGIN SELECT RAISE(ABORT, 'run identity is immutable'); END;

CREATE TRIGGER assignment_requires_coordinator BEFORE INSERT ON assignments
WHEN NOT EXISTS (
    SELECT 1 FROM events e JOIN command_requests c USING (team_id, request_id)
    WHERE e.team_id = NEW.team_id AND e.event_id = NEW.event_id AND c.kind = 'coordinator_command'
      AND e.task_id = NEW.task_id AND e.run_id = NEW.run_id AND e.revision = NEW.revision)
BEGIN SELECT RAISE(ABORT, 'assignment requires matching coordinator event'); END;

CREATE TRIGGER control_requires_coordinator BEFORE INSERT ON control_requests
WHEN NOT EXISTS (
    SELECT 1 FROM events e JOIN command_requests c USING (team_id, request_id)
    WHERE e.team_id = NEW.team_id AND e.event_id = NEW.request_event_id
      AND e.run_id = NEW.run_id AND c.kind = 'coordinator_command')
BEGIN SELECT RAISE(ABORT, 'control requires matching coordinator event'); END;

CREATE TRIGGER publication_requires_coordinator BEFORE INSERT ON publications
WHEN NOT EXISTS (
    SELECT 1 FROM events e JOIN command_requests c USING (team_id, request_id)
    WHERE e.team_id = NEW.team_id AND e.event_id = NEW.event_id AND c.kind = 'coordinator_command')
BEGIN SELECT RAISE(ABORT, 'publication requires coordinator event'); END;

CREATE TRIGGER delivery_routing BEFORE INSERT ON deliveries
WHEN EXISTS (SELECT 1 FROM agents WHERE team_id = NEW.team_id AND agent_id = NEW.recipient_agent_id AND role = 'worker')
  AND NOT EXISTS (
      SELECT 1 FROM events e JOIN command_requests c USING (team_id, request_id)
      WHERE e.team_id = NEW.team_id AND e.event_id = NEW.event_id AND c.kind = 'coordinator_command')
BEGIN SELECT RAISE(ABORT, 'only coordinator commands may enter worker inboxes'); END;

CREATE TRIGGER delivery_identity_is_immutable BEFORE UPDATE ON deliveries
WHEN NEW.team_id <> OLD.team_id OR NEW.event_id <> OLD.event_id OR NEW.recipient_agent_id <> OLD.recipient_agent_id
BEGIN SELECT RAISE(ABORT, 'delivery identity is immutable'); END;

CREATE TRIGGER run_requires_worker BEFORE INSERT ON runs
BEGIN
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM agents WHERE team_id = NEW.team_id
        AND agent_id = NEW.agent_id AND role = 'worker' AND registration = 'registered')
        THEN RAISE(ABORT, 'run requires a registered worker') END;
END;

CREATE TRIGGER released_run_cannot_reopen BEFORE UPDATE ON runs
WHEN OLD.released_at IS NOT NULL AND (NEW.released_at IS NOT OLD.released_at OR NEW.observed_execution <> 'finished')
BEGIN SELECT RAISE(ABORT, 'released run cannot execute again; create a new run'); END;

CREATE TRIGGER run_release_requires_reconciliation BEFORE UPDATE OF released_at ON runs
WHEN OLD.released_at IS NULL AND NEW.released_at IS NOT NULL
BEGIN
    SELECT CASE WHEN EXISTS (SELECT 1 FROM operations WHERE team_id = NEW.team_id AND run_id = NEW.run_id
        AND state IN ('intended', 'in_flight', 'uncertain'))
        THEN RAISE(ABORT, 'run has unresolved effects') END;
    SELECT CASE WHEN EXISTS (SELECT 1 FROM control_requests WHERE team_id = NEW.team_id AND run_id = NEW.run_id
        AND outcome IN ('pending', 'uncertain'))
        THEN RAISE(ABORT, 'run has unresolved control requests') END;
END;

CREATE TRIGGER cancel_is_irreversible BEFORE INSERT ON control_requests
WHEN NEW.desired_execution <> 'cancel' AND EXISTS (
    SELECT 1 FROM control_requests WHERE team_id = NEW.team_id AND run_id = NEW.run_id AND desired_execution = 'cancel'
)
BEGIN SELECT RAISE(ABORT, 'cancelled intent cannot resume the same run'); END;

CREATE TRIGGER control_generation_increases BEFORE INSERT ON control_requests
WHEN NEW.generation <> COALESCE((SELECT MAX(generation) FROM control_requests
    WHERE team_id = NEW.team_id AND run_id = NEW.run_id), 0) + 1
BEGIN SELECT RAISE(ABORT, 'control generation must increase monotonically'); END;

CREATE TRIGGER acknowledge_delivery AFTER INSERT ON recipient_receipts
BEGIN
    UPDATE deliveries SET acknowledged_at = NEW.accepted_at,
        state = CASE WHEN state = 'closed' THEN 'closed' ELSE 'acknowledged' END,
        next_attempt_at = NULL, version = version + 1
    WHERE team_id = NEW.team_id AND event_id = NEW.event_id AND recipient_agent_id = NEW.recipient_agent_id;
END;

CREATE TRIGGER delivery_evidence_cannot_regress BEFORE UPDATE ON deliveries
WHEN (OLD.delivered_at IS NOT NULL AND (NEW.delivered_at IS NULL OR NEW.delivered_at < OLD.delivered_at))
  OR (OLD.acknowledged_at IS NOT NULL AND NEW.acknowledged_at IS NOT OLD.acknowledged_at)
BEGIN SELECT RAISE(ABORT, 'delivery evidence cannot regress or change acknowledgment'); END;

CREATE TRIGGER event_reference_requires_final_artifact BEFORE INSERT ON event_artifacts
WHEN NOT EXISTS (SELECT 1 FROM artifacts WHERE team_id = NEW.team_id AND artifact_id = NEW.artifact_id AND finalization = 'finalized')
BEGIN SELECT RAISE(ABORT, 'event artifact must be finalized'); END;

CREATE TRIGGER result_reference_requires_final_artifact BEFORE INSERT ON result_artifacts
WHEN NOT EXISTS (SELECT 1 FROM artifacts WHERE team_id = NEW.team_id AND artifact_id = NEW.artifact_id AND finalization = 'finalized')
BEGIN SELECT RAISE(ABORT, 'result artifact must be finalized'); END;

CREATE TRIGGER finalized_content_is_immutable BEFORE UPDATE ON artifacts
WHEN OLD.finalization = 'finalized' AND (
    NEW.finalization <> OLD.finalization OR NEW.sha256 IS NOT OLD.sha256
    OR NEW.byte_count IS NOT OLD.byte_count OR NEW.uri <> OLD.uri
    OR NEW.logical_name <> OLD.logical_name OR NEW.artifact_version <> OLD.artifact_version
    OR NEW.media_type <> OLD.media_type OR NEW.team_id <> OLD.team_id OR NEW.artifact_id <> OLD.artifact_id)
BEGIN SELECT RAISE(ABORT, 'finalized artifact content is immutable'); END;

CREATE TRIGGER review_requires_current_coordinator BEFORE INSERT ON reviews
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM events e JOIN command_requests c USING (team_id, request_id)
        JOIN teams t USING (team_id)
        JOIN ownership_epochs o ON o.team_id = t.team_id AND o.epoch = t.current_epoch
        WHERE e.team_id = NEW.team_id AND e.event_id = NEW.event_id
          AND c.kind = 'coordinator_command' AND c.authority_epoch = t.current_epoch
          AND c.actor_session_id = o.coordinator_session_id AND t.authority_state = 'owned'
    ) THEN RAISE(ABORT, 'review requires current coordinator authority') END;
END;

CREATE TRIGGER assessment_requires_current_coordinator BEFORE INSERT ON compatibility_assessments
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM events e JOIN command_requests c USING (team_id, request_id)
        JOIN teams t USING (team_id)
        JOIN ownership_epochs o ON o.team_id = t.team_id AND o.epoch = t.current_epoch
        WHERE e.team_id = NEW.team_id AND e.event_id = NEW.event_id
          AND c.kind = 'coordinator_command' AND c.authority_epoch = t.current_epoch
          AND c.actor_session_id = o.coordinator_session_id AND t.authority_state = 'owned'
    ) THEN RAISE(ABORT, 'compatibility assessment requires current coordinator authority') END;
    SELECT CASE WHEN NEW.assessment_number <> COALESCE((SELECT MAX(assessment_number) FROM compatibility_assessments
        WHERE team_id = NEW.team_id AND result_id = NEW.result_id AND revision = NEW.revision), 0) + 1
        THEN RAISE(ABORT, 'assessment number must increase monotonically') END;
END;

CREATE TRIGGER review_matches_compatibility_assessment BEFORE INSERT ON reviews
WHEN NEW.compatibility IN ('compatible', 'incompatible')
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM compatibility_assessments a WHERE a.team_id = NEW.team_id
          AND a.assessment_id = NEW.assessment_id AND a.state = NEW.compatibility
          AND a.assessment_number = (SELECT MAX(a2.assessment_number) FROM compatibility_assessments a2
              WHERE a2.team_id = a.team_id AND a2.result_id = a.result_id AND a2.revision = a.revision)
    ) THEN RAISE(ABORT, 'review must use latest matching compatibility assessment') END;
END;

CREATE TRIGGER acceptance_requires_evidence BEFORE INSERT ON reviews
WHEN NEW.decision = 'accepted'
BEGIN
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tasks WHERE team_id = NEW.team_id
        AND task_id = NEW.task_id AND state = 'awaiting_review')
        THEN RAISE(ABORT, 'task is not awaiting review') END;
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM plan_revisions WHERE team_id = NEW.team_id
        AND revision = NEW.revision AND state = 'current')
        THEN RAISE(ABORT, 'acceptance must evaluate the current plan') END;
    SELECT CASE WHEN NEW.compatibility = 'current' AND NEW.revision <> (
        SELECT a.revision FROM results r JOIN assignments a USING (team_id, assignment_id)
        WHERE r.team_id = NEW.team_id AND r.result_id = NEW.result_id)
        THEN RAISE(ABORT, 'old assignment needs explicit compatibility review') END;
    SELECT CASE WHEN EXISTS (SELECT 1 FROM runs WHERE team_id = NEW.team_id
        AND task_id = NEW.task_id AND released_at IS NULL)
        THEN RAISE(ABORT, 'acceptance requires execution slot release') END;
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM result_artifacts WHERE team_id = NEW.team_id
        AND result_id = NEW.result_id AND purpose = 'output')
        THEN RAISE(ABORT, 'acceptance requires an output artifact') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM result_artifacts r JOIN artifacts a USING (team_id, artifact_id)
        WHERE r.team_id = NEW.team_id AND r.result_id = NEW.result_id
          AND (a.finalization <> 'finalized' OR a.integrity <> 'valid')
    ) THEN RAISE(ABORT, 'acceptance requires valid artifacts') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM issues WHERE team_id = NEW.team_id AND state = 'open' AND blocks_acceptance = 1
          AND (task_id = NEW.task_id OR task_id IS NULL)
    ) THEN RAISE(ABORT, 'acceptance has unresolved blockers') END;
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM acceptance_criteria c WHERE c.team_id = NEW.team_id AND c.task_id = NEW.task_id
          AND c.revision = NEW.revision AND c.required = 1 AND NOT EXISTS (
              SELECT 1 FROM acceptance_checks k WHERE k.team_id = c.team_id AND k.task_id = c.task_id
                AND k.revision = c.revision AND k.criterion_id = c.criterion_id AND k.result_id = NEW.result_id
                AND k.state = 'passed' AND k.attempt_number = (
                    SELECT MAX(k2.attempt_number) FROM acceptance_checks k2 WHERE k2.team_id = k.team_id
                      AND k2.result_id = k.result_id AND k2.revision = k.revision AND k2.criterion_id = k.criterion_id)
          )
    ) THEN RAISE(ABORT, 'required acceptance checks have not passed') END;
END;

CREATE TRIGGER review_number_increases BEFORE INSERT ON reviews
WHEN NEW.review_number <> COALESCE((SELECT MAX(review_number) FROM reviews
    WHERE team_id = NEW.team_id AND result_id = NEW.result_id), 0) + 1
BEGIN SELECT RAISE(ABORT, 'review number must increase monotonically'); END;

CREATE TRIGGER apply_accepted_review AFTER INSERT ON reviews
WHEN NEW.decision = 'accepted'
BEGIN
    UPDATE tasks SET state = 'accepted', accepted_review_id = NEW.review_id, version = version + 1
    WHERE team_id = NEW.team_id AND task_id = NEW.task_id;
END;

CREATE TRIGGER accepted_result_cannot_gain_artifacts BEFORE INSERT ON result_artifacts
WHEN EXISTS (SELECT 1 FROM reviews WHERE team_id = NEW.team_id AND result_id = NEW.result_id AND decision = 'accepted')
BEGIN SELECT RAISE(ABORT, 'accepted result artifact set is immutable'); END;

CREATE TRIGGER completed_check_is_immutable BEFORE UPDATE ON acceptance_checks
WHEN OLD.state <> 'pending'
BEGIN SELECT RAISE(ABORT, 'record a new check attempt'); END;

CREATE TRIGGER task_acceptance_matches_review BEFORE UPDATE ON tasks
WHEN NEW.state = 'accepted'
BEGIN
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM reviews WHERE team_id = NEW.team_id
        AND task_id = NEW.task_id AND review_id = NEW.accepted_review_id AND decision = 'accepted')
        THEN RAISE(ABORT, 'task acceptance requires accepted review') END;
END;

CREATE TRIGGER terminal_task_cannot_reopen BEFORE UPDATE OF state ON tasks
WHEN OLD.state IN ('accepted', 'cancelled') AND NEW.state <> OLD.state
BEGIN SELECT RAISE(ABORT, 'accepted and cancelled tasks cannot reopen'); END;

CREATE TRIGGER integration_requires_accepted_review BEFORE INSERT ON integration_changes
WHEN NOT EXISTS (SELECT 1 FROM reviews WHERE team_id = NEW.team_id AND review_id = NEW.source_review_id AND decision = 'accepted')
BEGIN SELECT RAISE(ABORT, 'integration requires an accepted source review'); END;

-- READ MODELS: no duplicated alive/dead dictionaries or separate inbox stores. --

CREATE VIEW coordinator_status AS
SELECT t.team_id, t.authority_state, t.current_epoch, o.coordinator_session_id,
    s.agent_id, s.activity, s.availability, s.profile_id
FROM teams t LEFT JOIN ownership_epochs o ON o.team_id = t.team_id AND o.epoch = t.current_epoch
LEFT JOIN sessions s ON s.team_id = o.team_id AND s.session_id = o.coordinator_session_id;

CREATE VIEW current_controls AS
SELECT r.team_id, r.run_id, COALESCE(c.generation, 0) AS generation,
    COALESCE(c.desired_execution, 'run') AS desired_execution,
    c.outcome AS control_outcome, r.observed_execution
FROM runs r LEFT JOIN control_requests c ON c.team_id = r.team_id AND c.run_id = r.run_id
  AND c.generation = (SELECT MAX(c2.generation) FROM control_requests c2 WHERE c2.team_id = r.team_id AND c2.run_id = r.run_id);

CREATE VIEW agent_registry AS
SELECT a.team_id, a.agent_id, a.name, a.role, a.registration, r.task_id, r.run_id,
    CASE WHEN a.role <> 'worker' THEN NULL WHEN r.run_id IS NULL THEN 'idle'
        WHEN r.observed_execution = 'not_started' THEN 'reserved' ELSE 'assigned' END AS allocation,
    r.health AS run_health, r.outcome AS run_outcome, r.observed_execution,
    r.last_heartbeat_at, r.last_substantive_event_at, s.session_id, p.provider, p.model, p.adapter
FROM agents a LEFT JOIN runs r ON r.team_id = a.team_id AND r.agent_id = a.agent_id AND r.released_at IS NULL
LEFT JOIN sessions s ON s.team_id = a.team_id AND s.session_id = COALESCE(r.session_id,
    (SELECT o.coordinator_session_id FROM teams t JOIN ownership_epochs o
        ON o.team_id = t.team_id AND o.epoch = t.current_epoch
        JOIN sessions cs ON cs.team_id = o.team_id AND cs.session_id = o.coordinator_session_id
        WHERE t.team_id = a.team_id AND cs.agent_id = a.agent_id),
    (SELECT s2.session_id FROM sessions s2 WHERE s2.team_id = a.team_id AND s2.agent_id = a.agent_id
        ORDER BY s2.created_at DESC, s2.session_id DESC LIMIT 1))
LEFT JOIN execution_profiles p ON p.team_id = s.team_id AND p.profile_id = s.profile_id;

CREATE VIEW result_review_status AS
SELECT r.*, COALESCE(v.decision, 'pending') AS review_state,
    v.review_id, v.revision AS reviewed_revision, v.compatibility AS reviewed_compatibility,
    a.revision AS assignment_revision, p.revision AS current_revision,
    CASE WHEN a.revision = p.revision THEN 'current'
        ELSE COALESCE(c.state, 'unchecked') END AS current_compatibility
FROM results r JOIN assignments a USING (team_id, assignment_id)
LEFT JOIN plan_revisions p ON p.team_id = r.team_id AND p.state = 'current'
LEFT JOIN compatibility_assessments c ON c.team_id = r.team_id AND c.result_id = r.result_id AND c.revision = p.revision
  AND c.assessment_number = (SELECT MAX(c2.assessment_number) FROM compatibility_assessments c2
      WHERE c2.team_id = c.team_id AND c2.result_id = c.result_id AND c2.revision = c.revision)
LEFT JOIN reviews v ON v.team_id = r.team_id AND v.result_id = r.result_id
  AND v.review_number = (SELECT MAX(v2.review_number) FROM reviews v2 WHERE v2.team_id = r.team_id AND v2.result_id = r.result_id);

CREATE VIEW inbox_items AS
SELECT d.team_id, d.recipient_agent_id, e.event_id, e.sequence, e.type,
    COALESCE(i.priority, e.priority) AS priority, e.body, e.task_id, e.run_id,
    d.state AS delivery_state, d.acknowledged_at, i.issue_id,
    (d.acknowledged_at IS NULL AND d.state <> 'closed') AS needs_acknowledgment,
    (COALESCE(i.state = 'open', 0) OR COALESCE(r.review_state = 'pending', 0)
        OR COALESCE(p.state = 'pending', 0) OR COALESCE(c.outcome IN ('pending', 'uncertain'), 0)) AS needs_resolution
FROM deliveries d JOIN events e USING (team_id, event_id)
LEFT JOIN issues i ON i.team_id = e.team_id AND i.source_event_id = e.event_id
LEFT JOIN result_review_status r ON r.team_id = e.team_id AND r.event_id = e.event_id
LEFT JOIN proposals p ON p.team_id = e.team_id AND p.source_event_id = e.event_id
LEFT JOIN control_requests c ON c.team_id = e.team_id AND c.request_event_id = e.event_id
WHERE (d.acknowledged_at IS NULL AND d.state <> 'closed') OR i.state = 'open'
    OR r.review_state = 'pending' OR p.state = 'pending' OR c.outcome IN ('pending', 'uncertain');

-- Team-level coordinator backlog survives session replacement. Actual delivery
-- attempts still target an exact session; reassignment of obligations is a runtime transaction.
CREATE VIEW normal_inbox AS
SELECT i.* FROM inbox_items i JOIN agents a ON a.team_id = i.team_id AND a.agent_id = i.recipient_agent_id
WHERE a.role = 'coordinator' AND i.priority = 'normal';

CREATE VIEW override_inbox AS
SELECT i.* FROM inbox_items i JOIN agents a ON a.team_id = i.team_id AND a.agent_id = i.recipient_agent_id
WHERE a.role = 'coordinator' AND i.priority = 'urgent';

CREATE VIEW worker_inbox AS
SELECT i.* FROM inbox_items i JOIN agents a ON a.team_id = i.team_id AND a.agent_id = i.recipient_agent_id
WHERE a.role = 'worker';

CREATE VIEW bulletin AS
SELECT p.team_id, p.publication_id, p.proposal_id, p.state, p.actionable, e.body, e.sequence,
    r.recipient_agent_id, d.state AS delivery_state, d.acknowledged_at
FROM publications p JOIN events e USING (team_id, event_id)
LEFT JOIN publication_recipients r USING (team_id, publication_id, event_id)
LEFT JOIN deliveries d ON d.team_id = r.team_id AND d.event_id = r.event_id AND d.recipient_agent_id = r.recipient_agent_id;

CREATE VIEW work_history AS
SELECT e.*, c.kind AS source_kind, s.agent_id AS sender_agent_id, c.actor_session_id, c.authority_epoch
FROM events e JOIN command_requests c USING (team_id, request_id)
JOIN sessions s ON s.team_id = c.team_id AND s.session_id = c.actor_session_id;

CREATE VIEW scope_ownership AS
SELECT s.*, COALESCE(c.state, 'unclaimed') AS state, c.run_id, c.epoch, c.claim_id
FROM write_scopes s LEFT JOIN scope_claims c ON c.team_id = s.team_id AND c.scope_id = s.scope_id AND c.state <> 'released';

CREATE VIEW current_ci_checks AS
SELECT c.* FROM ci_checks c JOIN pull_requests p USING (team_id, pr_id)
WHERE c.head_commit = p.head_commit AND c.attempt_number = (
    SELECT MAX(c2.attempt_number) FROM ci_checks c2 WHERE c2.team_id = c.team_id AND c2.pr_id = c.pr_id
      AND c2.head_commit = c.head_commit AND c2.name = c.name);

-- Append-only guards for evidence and versioned identity. Mutable projections
-- still require command-handler transactions, documented in README.md.
CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER requests_no_update BEFORE UPDATE ON command_requests BEGIN SELECT RAISE(ABORT, 'request receipts are immutable'); END;
CREATE TRIGGER requests_no_delete BEFORE DELETE ON command_requests BEGIN SELECT RAISE(ABORT, 'request receipts are immutable'); END;
CREATE TRIGGER epochs_no_update BEFORE UPDATE ON ownership_epochs BEGIN SELECT RAISE(ABORT, 'epochs are immutable'); END;
CREATE TRIGGER epochs_no_delete BEFORE DELETE ON ownership_epochs BEGIN SELECT RAISE(ABORT, 'epochs are immutable'); END;
CREATE TRIGGER profiles_no_update BEFORE UPDATE ON execution_profiles BEGIN SELECT RAISE(ABORT, 'create a new execution profile'); END;
CREATE TRIGGER profiles_no_delete BEFORE DELETE ON execution_profiles BEGIN SELECT RAISE(ABORT, 'execution profiles are historical'); END;
CREATE TRIGGER specs_no_update BEFORE UPDATE ON task_specs BEGIN SELECT RAISE(ABORT, 'create a new task spec revision'); END;
CREATE TRIGGER specs_no_delete BEFORE DELETE ON task_specs BEGIN SELECT RAISE(ABORT, 'task specs are historical'); END;
CREATE TRIGGER dependencies_no_update BEFORE UPDATE ON task_dependencies BEGIN SELECT RAISE(ABORT, 'dependencies are immutable'); END;
CREATE TRIGGER dependencies_no_delete BEFORE DELETE ON task_dependencies BEGIN SELECT RAISE(ABORT, 'dependencies are historical'); END;
CREATE TRIGGER criteria_no_update BEFORE UPDATE ON acceptance_criteria BEGIN SELECT RAISE(ABORT, 'criteria are immutable'); END;
CREATE TRIGGER criteria_no_delete BEFORE DELETE ON acceptance_criteria BEGIN SELECT RAISE(ABORT, 'criteria are historical'); END;
CREATE TRIGGER assignments_no_update BEFORE UPDATE ON assignments BEGIN SELECT RAISE(ABORT, 'assignments are immutable'); END;
CREATE TRIGGER assignments_no_delete BEFORE DELETE ON assignments BEGIN SELECT RAISE(ABORT, 'assignments are historical'); END;
CREATE TRIGGER receipts_no_update BEFORE UPDATE ON recipient_receipts BEGIN SELECT RAISE(ABORT, 'recipient receipts are immutable'); END;
CREATE TRIGGER receipts_no_delete BEFORE DELETE ON recipient_receipts BEGIN SELECT RAISE(ABORT, 'recipient receipts are historical'); END;
CREATE TRIGGER results_no_update BEFORE UPDATE ON results BEGIN SELECT RAISE(ABORT, 'results are immutable'); END;
CREATE TRIGGER results_no_delete BEFORE DELETE ON results BEGIN SELECT RAISE(ABORT, 'results are historical'); END;
CREATE TRIGGER reviews_no_update BEFORE UPDATE ON reviews BEGIN SELECT RAISE(ABORT, 'reviews are immutable'); END;
CREATE TRIGGER reviews_no_delete BEFORE DELETE ON reviews BEGIN SELECT RAISE(ABORT, 'reviews are historical'); END;
CREATE TRIGGER assessments_no_update BEFORE UPDATE ON compatibility_assessments BEGIN SELECT RAISE(ABORT, 'compatibility assessments are immutable'); END;
CREATE TRIGGER assessments_no_delete BEFORE DELETE ON compatibility_assessments BEGIN SELECT RAISE(ABORT, 'compatibility assessments are historical'); END;
CREATE TRIGGER result_artifacts_no_update BEFORE UPDATE ON result_artifacts BEGIN SELECT RAISE(ABORT, 'result artifact links are immutable'); END;
CREATE TRIGGER result_artifacts_no_delete BEFORE DELETE ON result_artifacts BEGIN SELECT RAISE(ABORT, 'result artifact links are historical'); END;
CREATE TRIGGER event_artifacts_no_update BEFORE UPDATE ON event_artifacts BEGIN SELECT RAISE(ABORT, 'event artifact links are immutable'); END;
CREATE TRIGGER event_artifacts_no_delete BEFORE DELETE ON event_artifacts BEGIN SELECT RAISE(ABORT, 'event artifact links are historical'); END;
CREATE TRIGGER checks_no_delete BEFORE DELETE ON acceptance_checks BEGIN SELECT RAISE(ABORT, 'check attempts are historical'); END;

COMMIT;
