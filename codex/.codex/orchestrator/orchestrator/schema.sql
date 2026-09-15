PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=FULL;
CREATE TABLE IF NOT EXISTS teams (
 id TEXT PRIMARY KEY, objective TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 epoch INTEGER NOT NULL DEFAULT 1, coordinator_session TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'active' CHECK(state IN ('active','completed','cancelled')),
 max_workers INTEGER NOT NULL DEFAULT 2 CHECK(max_workers>0), config TEXT NOT NULL CHECK(json_valid(config))
) STRICT;
CREATE TABLE IF NOT EXISTS agents (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id), role TEXT NOT NULL CHECK(role IN ('coordinator','worker')),
 name TEXT NOT NULL, config TEXT NOT NULL CHECK(json_valid(config)), retired INTEGER NOT NULL DEFAULT 0 CHECK(retired IN (0,1))
) STRICT;
CREATE TABLE IF NOT EXISTS sessions (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), token_hash TEXT NOT NULL UNIQUE,
 external_id TEXT, config TEXT NOT NULL CHECK(json_valid(config)), state TEXT NOT NULL DEFAULT 'idle', heartbeat INTEGER NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS tasks (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id), revision INTEGER NOT NULL,
 spec TEXT NOT NULL CHECK(json_valid(spec)), state TEXT NOT NULL DEFAULT 'queued'
 CHECK(state IN ('queued','running','blocked','awaiting_review','accepted','failed','cancelled')),
 holds TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(holds)), accepted_event TEXT,
 version INTEGER NOT NULL DEFAULT 1
) STRICT;
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), session_id TEXT NOT NULL REFERENCES sessions(id),
 assignment_event TEXT NOT NULL, revision INTEGER NOT NULL, health TEXT NOT NULL DEFAULT 'starting',
 desired TEXT NOT NULL DEFAULT 'running', observed TEXT NOT NULL DEFAULT 'starting',
 control_generation INTEGER NOT NULL DEFAULT 0, confirmed_generation INTEGER NOT NULL DEFAULT 0,
 outcome TEXT, released INTEGER NOT NULL DEFAULT 0 CHECK(released IN (0,1)),
 runner_pid INTEGER, runner_identity TEXT, heartbeat INTEGER NOT NULL, result_event TEXT
) STRICT;
CREATE UNIQUE INDEX IF NOT EXISTS task_slot ON runs(task_id) WHERE released=0;
CREATE UNIQUE INDEX IF NOT EXISTS session_slot ON runs(session_id) WHERE released=0;
CREATE TABLE IF NOT EXISTS command_requests (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), payload TEXT NOT NULL,
 response TEXT NOT NULL CHECK(json_valid(response)), created INTEGER NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id), sequence INTEGER NOT NULL,
 type TEXT NOT NULL, sender_session TEXT REFERENCES sessions(id), source TEXT NOT NULL DEFAULT 'session' CHECK(source IN ('session','runtime')), task_id TEXT REFERENCES tasks(id),
 run_id TEXT REFERENCES runs(id) DEFERRABLE INITIALLY DEFERRED, revision INTEGER NOT NULL,
 priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('normal','urgent')),
 body TEXT NOT NULL CHECK(json_valid(body)), reply_to TEXT REFERENCES events(id), created INTEGER NOT NULL,
 UNIQUE(team_id,sequence)
) STRICT;
CREATE TABLE IF NOT EXISTS deliveries (
 id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES events(id), recipient TEXT NOT NULL REFERENCES agents(id),
 target_session TEXT REFERENCES sessions(id), state TEXT NOT NULL DEFAULT 'pending'
 CHECK(state IN ('pending','sending','delivered','uncertain','acknowledged','cancelled')),
 attempts INTEGER NOT NULL DEFAULT 0, delivered_at INTEGER, acknowledged_at INTEGER,
 retry_at INTEGER NOT NULL DEFAULT 0, last_error TEXT, UNIQUE(event_id,recipient)
) STRICT;
CREATE TABLE IF NOT EXISTS issues (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id), task_id TEXT REFERENCES tasks(id),
 coalescing_key TEXT NOT NULL, event_id TEXT NOT NULL REFERENCES events(id),
 priority TEXT NOT NULL, blocks_acceptance INTEGER NOT NULL CHECK(blocks_acceptance IN (0,1)),
 state TEXT NOT NULL DEFAULT 'open' CHECK(state IN ('open','resolved')), resolution_event TEXT REFERENCES events(id)
) STRICT;
CREATE UNIQUE INDEX IF NOT EXISTS open_issue ON issues(team_id,task_id,coalescing_key) WHERE state='open';
CREATE TABLE IF NOT EXISTS operations (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id), run_id TEXT REFERENCES runs(id),
 kind TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','running','succeeded','failed','uncertain')),
 intent TEXT NOT NULL CHECK(json_valid(intent)), outcome TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(outcome)),
 created INTEGER NOT NULL, updated INTEGER NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS resources (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id), kind TEXT NOT NULL CHECK(kind IN ('pane','process','worktree')),
 identity TEXT NOT NULL, detail TEXT NOT NULL CHECK(json_valid(detail)), owner_run TEXT REFERENCES runs(id),
 state TEXT NOT NULL DEFAULT 'idle' CHECK(state IN ('idle','held','quarantined','released')), UNIQUE(kind,identity)
) STRICT;
CREATE UNIQUE INDEX IF NOT EXISTS worktree_owner ON resources(owner_run) WHERE kind='worktree' AND state='held';
CREATE TABLE IF NOT EXISTS artifacts (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id), path TEXT NOT NULL UNIQUE,
 sha256 TEXT NOT NULL, size INTEGER NOT NULL CHECK(size>=0), created INTEGER NOT NULL
) STRICT;
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
CREATE TRIGGER IF NOT EXISTS receipts_no_update BEFORE UPDATE ON command_requests BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
CREATE TRIGGER IF NOT EXISTS receipts_no_delete BEFORE DELETE ON command_requests BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
PRAGMA user_version=1;
