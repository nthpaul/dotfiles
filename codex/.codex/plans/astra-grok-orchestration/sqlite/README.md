# Model-agnostic SQLite data model

The coordination model is model agnostic. **Coordinator** and **worker** are responsibilities; **provider**, **model**, and **adapter** are execution configuration. Astra and Grok are one possible deployment of this schema. Either role can use any configured model, and different workers can use different providers.

The complete DDL is in [schema.sql](schema.sql). [example.sqlite3](example.sqlite3) is a generated, populated database covering every table. This is a proposed executable data design, not an installed runtime or a verified adapter implementation.

## Inspect it

From this directory:

```sh
sqlite3 -readonly example.sqlite3
```

Inside SQLite:

```sql
.headers on
.mode box
.tables
.schema execution_profiles
.schema runs
.schema deliveries
.schema

SELECT agent_id, role, allocation, provider, model, session_id
FROM agent_registry WHERE team_id = 'demo';

SELECT task_id, state FROM tasks WHERE team_id = 'demo';
SELECT * FROM current_controls WHERE team_id = 'demo';
SELECT * FROM override_inbox WHERE team_id = 'demo';
SELECT * FROM result_review_status WHERE team_id = 'demo';
SELECT * FROM bulletin WHERE team_id = 'demo';
SELECT * FROM work_history WHERE team_id = 'demo' ORDER BY sequence;
```

Generate a new example or run the schema checks:

```sh
python3 example.py /tmp/orchestration-example.sqlite3
python3 test_schema.py
```

The builder refuses to overwrite an existing database. The checked-in SQL and example builder are the reproducible sources; generated databases and Python caches are ignored by Git. There are no external dependencies beyond Python and a SQLite build supporting this DDL.

To inspect an empty database without creating a file:

```sh
sqlite3 :memory:
```

```sql
.read schema.sql
.schema
```

## Model and process identities

| Identity | Represents | Relationship |
| --- | --- | --- |
| `agent_id` | Stable team member with a role and display name | One agent has many sessions and historical runs. |
| `profile_id` | Immutable provider/model/adapter/settings configuration | Many agents and sessions can use the same profile. |
| `session_id` | A concrete model conversation or runtime session | Binds an agent to an execution profile; one model session can host successive related runs. |
| `external_session_id` | Adapter-specific conversation handle | Opaque reference used to reach/resume the actual conversation. |
| `run_id` | One attempt at one task | Binds the task, worker, and session. A retry receives a new run ID. |
| `assignment_id` | An immutable task specification delivered to a run | A related follow-up can create a new assignment generation within an unreleased run. |
| `process_id` | A registered operating-system process | Optional for remote/API adapters; a session/run can have multiple associated processes and child tools. |

`agents.default_profile_id` controls future choices. A run's actual profile is obtained through its session, so changing the default cannot rewrite history. A new model or adapter version requires a new profile and session; a provider/model change is never hidden inside an existing session row.

The synthetic example uses two invented providers. The coordinator and one worker deliberately share the same model; another worker uses the other provider. No real provider capabilities are asserted by the fixture.

The runtime is represented as an agent with role `runtime` so durable observations have a validated sender identity. Its session has no model profile. It is bookkeeping code, not another model role.

## Complete table inventory

There are **43 tables**. The inventory below covers all of them; [schema.sql](schema.sql) specifies every column, type, default, enum, key, foreign key, index, and trigger. Relationship tables keep recipients, dependencies, and evidence references individually addressable.

| Area | Table | Record and ownership |
| --- | --- | --- |
| Team | `teams` | Objective, lifecycle, current ownership epoch, authority state, optimistic version. Runtime maintains state under authorized commands. |
| Execution | `execution_profiles` | Immutable provider, model, adapter/version, endpoint, credential reference, and provider settings. |
| Execution | `profile_capabilities` | Per-profile capability support, precise semantics, verification evidence, and observation time. |
| Identity | `agents` | Stable role, name, registration status, and default profile. |
| Identity | `sessions` | Agent/profile binding, opaque external session handle, availability/activity, and heartbeat observations. |
| Runtime | `runtime_instances` | Runtime process association, lifecycle, health, and heartbeat. |
| Authority | `ownership_epochs` | Immutable coordinator-session ownership acquisitions with monotonically increasing epoch numbers. |
| Commands | `command_requests` | Idempotency key, actor/session, authority epoch, canonical request content, and durable receipt event. |
| History | `events` | Append-only team sequence, event identity/type, task/run/revision context, priority, body, and reply reference. Sender is derived from the request. |
| Plan | `plan_revisions` | Draft/current/superseded/abandoned revisions and decisions. At most one current revision per team. |
| Work | `tasks` | Stable task identity, lifecycle, owner, follow-up link, required flag, accepted-review link, and optimistic version. |
| Work | `task_specs` | Objective, relevant context, write contract, and expected output for a task at a specific revision. |
| Work | `task_dependencies` | Acyclic dependency edges within a plan revision. |
| Work | `acceptance_criteria` | Individually identifiable required/optional criteria for each task specification. |
| Execution | `runs` | Attempt identity, task/worker/session binding, health, observed execution, outcome, and exclusive-slot release. |
| Execution | `assignments` | Versioned instructions linking a run to a task specification and its coordinator event. |
| Scheduling | `dispatch_holds` | Independent team/task/profile holds; reason, originating event, and explicit clearance evidence. Groups are represented by one task hold per affected member. |
| Control | `control_requests` | Ordered desired-execution generations and separately confirmed outcomes. |
| Transport | `deliveries` | Per-event/per-recipient scheduling state and monotonic delivery/acknowledgment evidence. |
| Transport | `delivery_attempts` | Each concrete send attempt, its exact target session/epoch, adapter receipt, and error/outcome. |
| Transport | `recipient_receipts` | Immutable recipient acceptance keyed by event ID and agent ID; deduplicates acknowledgment records. |
| Issues | `issues` | Question/conflict/blocker, coalescing identity, urgency, acceptance-blocking flag, and resolution. |
| Issues | `issue_events` | All reports attached to a coalesced issue without losing original events. |
| Routing | `proposals` | A source report and the coordinator's publication decision. A conflict can also have a proposal record for its suggested routing. |
| Routing | `proposal_recipients` | Suggested recipients; no forwarding authority. |
| Routing | `publications` | Coordinator publication with optional originating proposal and current/superseded/withdrawn status. |
| Routing | `publication_recipients` | Approved recipient set, each linked to its delivery. Informational publications may have no targeted recipients. |
| Evidence | `artifacts` | Versioned file/URI, content hash, size, finalization state, and independently observed integrity. |
| Evidence | `event_artifacts` | Original artifact references attached to reports, assignments, and publications. |
| Results | `results` | Immutable result tied to its original task, run, assignment, and report event. |
| Results | `result_artifacts` | Output, validation, and context artifacts making up a result. |
| Validation | `acceptance_checks` | Individual attempts at revision-specific criteria, tied to a result and its evidence. Latest attempt governs the criterion. |
| Compatibility | `compatibility_assessments` | Immutable judgments about reusing a result under a particular plan revision, independent of its historical acceptance. |
| Review | `reviews` | Immutable coordinator decisions, evaluated plan revision, compatibility judgment, and rationale. No review means pending. |
| Effects | `operations` | Durable intent and observed outcome for launches, tools, resource changes, and external actions; parent/retry links and correlation keys. |
| Resources | `panes` | Exact host/tmux-server/window/pane identity, purpose, owning session, and lifecycle. |
| Resources | `processes` | Host/boot/PID/start identity, parent/session/run/pane relationships, launch intent, and observed exit/health. |
| Resources | `worktrees` | Repository/path/branch/base commit and provisioning/use/release lifecycle. |
| Resources | `write_scopes` | Canonical write resource. V1 uses one whole-worktree scope, avoiding ambiguous overlapping path locks. |
| Resources | `scope_claims` | Historical exclusive claims with epoch, owner run, quarantine status, and release evidence. |
| Integration | `integration_changes` | Accepted source review/commit being assembled by the named integration task in its worktree. |
| Publication | `pull_requests` | Repository/branch/head, downstack parent, submission operation/state, URL, and external disposition. |
| CI | `ci_checks` | Required/optional check attempts keyed to the exact PR head commit. |

No core ownership, lifecycle, delivery, or acceptance field is hidden in JSON. JSON is limited to provider configuration, canonical request payloads, extensible event metadata, and operation-specific external responses. Large content belongs in artifacts. Credentials belong outside the database; profiles store references only.

## State-map coverage and derived views

| State-map dimension | Stored or derived representation |
| --- | --- |
| Team lifecycle and authority | `teams.state`, `teams.authority_state`, `teams.current_epoch` |
| Current/stale coordinator session | Compare ownership epoch/session with the current team pointer; `coordinator_status` shows the current owner. |
| Runtime lifecycle/health | `runtime_instances.lifecycle`, `runtime_instances.health` |
| Coordinator availability | Current coordinator's `sessions.activity` and `availability` |
| Revision lifecycle | `plan_revisions.state` |
| Open/held dispatch | Existence of uncleared applicable `dispatch_holds`; do not store a duplicate gate boolean. |
| Task lifecycle | `tasks.state` |
| Worker registration/allocation | `agents.registration`; `agent_registry.allocation` derives idle/reserved/assigned from an unreleased run. |
| Process/run health | `processes.health` is an OS observation; `runs.health` is the adapter's run observation, including remote execution. They are not required to move in lockstep. |
| Attempt outcome | `runs.outcome` |
| Desired versus observed execution | `current_controls` selects the latest control generation; `runs.observed_execution` remains independent. Generation zero means the assignment's initial run intent, not a confirmed control response. |
| Control outcome | `control_requests.outcome` |
| Receipt versus delivery versus acknowledgment | `command_requests`, `deliveries`, and `recipient_receipts` respectively |
| Issue resolution | `issues.state`; receipt acknowledgment does not change it. |
| Normal/urgent/worker inbox | `normal_inbox`, `override_inbox`, `worker_inbox`, derived from `inbox_items` |
| Coalesced urgent conflicts | One open `issues` row per team/coalescing key, plus `issue_events`. The original issue event anchors its unresolved inbox item. Later reports retain separate delivery obligations where necessary. |
| Bulletin | `bulletin` joins publications and per-recipient delivery outcomes. |
| Artifact finalization/integrity | `artifacts.finalization`, `artifacts.integrity` |
| Review and compatibility | `result_review_status` distinguishes historical reviewed revision/compatibility from the latest `compatibility_assessments` judgment for the current plan. No assessment for an old result means unchecked. |
| Operation outcome/uncertainty | `operations.state`; uncertainty is not silently converted to failure. |
| Pane/worktree lifecycle | `panes.state`, `worktrees.state` |
| Scope ownership | `scope_ownership` derives unclaimed/held/quarantined from live claims. Released claim rows preserve history. |
| Integration/publication/CI | `integration_changes.state`, `pull_requests.publication_state`, `pull_requests.disposition`, `current_ci_checks` |
| Ordered history | `work_history`, always queried with `ORDER BY sequence` within one team |

There are **12 views**. Views do not imply row ordering. Coordinator inbox views include unresolved obligations addressed to historical coordinator identities; a takeover reconciles that backlog and targets delivery attempts to the exact current session. A coalescing key and an inbox query do not themselves wake or interrupt that session.

## What SQLite enforces

The schema uses [STRICT tables](https://www.sqlite.org/stricttables.html), checked enums, and composite foreign keys. Each reference to a team-owned entity carries `team_id`, preventing cross-team relationships. [Foreign-key enforcement must be enabled on every connection](https://www.sqlite.org/foreignkeys.html), before beginning a transaction. The schema includes that setup, but a runtime connection must repeat it.

[Partial unique indexes](https://www.sqlite.org/partialindex.html) exclude multiple unreleased runs for a task, worker, or session, multiple live write-scope claims, duplicate active worktree paths, and multiple current plan revisions. Missing, unresponsive, and uncertain runs retain their slot until explicitly reconciled.

Additional guards cover immutable history/configuration, dependency cycles, legal task transitions, monotonically increasing epochs/event sequences/control generations, coordinator role and epoch checks for new commands, coordinator-only worker delivery, and preservation of acknowledgment evidence.

Accepted reviews require current coordinator authority, the current plan revision, explicit compatibility for older assignments, a reviewable task, released execution slots, verified artifact records, no open acceptance blockers, and the latest required checks passing. Inserting an accepted review atomically updates the task's acceptance state. Filesystem integrity and actual check truth remain runtime observations; SQLite cannot independently read and validate those external effects.

## What still requires the runtime

This schema is a complete storage proposal for the state map, not a substitute for command handlers or adapter tests. Workers use the authenticated CLI/API; SQLite does not authenticate a caller merely because it supplies a session ID.

The sole writer must implement these transaction and external-effect rules:

1. Start `BEGIN IMMEDIATE`. Look up `(team_id, request_id)` first. For an existing receipt, compare actor, command kind, and canonical request content; return the original receipt only for an identical authorized retry. Changed content is an error. Never use `INSERT OR REPLACE` or ignore a uniqueness failure and repeat effects.
2. For new commands, authenticate the actor, verify current ownership, validate event payloads and referenced task/run/assignment identities, and check allowed transitions. Coordinator takeover and the new epoch pointer change belong in the same transaction. Retrying a historical request is a receipt lookup, not permission for a new stale-epoch mutation.
3. Apply state updates with expected `version` predicates where provided; a row-count mismatch aborts the command. On other projections, read/check/write under the same write transaction. Atomically add the request receipt, ordered event(s), delivery rows, and all affected state. Commit before returning the receipt.
4. Before dispatch, verify team/runtime readiness, current ownership, task dependencies and revision compatibility, every applicable hold, adapter capabilities, available resources, and exclusive claims. A reserved run is not permission to launch yet.
5. Record a durable operation/send intent and exact target before crossing the database boundary. Perform the effect outside the write transaction, then record the observed outcome in a new transaction. Reconcile crashes between those steps; never hold a write transaction open during a model/tool call.
6. Apply actual recipient deduplication before worker execution. `recipient_receipts` deduplicates stored acceptance records; it cannot prevent a provider from executing the same prompt twice. Keep ambiguous deliveries uncertain if the adapter lacks a verified safe retry protocol.
7. Verify real process start identities, tool cessation, artifact content hashes, and acceptance evidence. Preserve uncertain results of external actions. A recorded epoch or a unique slot does not stop an old process from writing; takeover needs enforced isolation or confirmed cessation.
8. Maintain remaining transition rules and monotonic observation generations, including request/outcome consistency, exact-run confirmation matching, late worker reports, retired-agent eligibility, terminal team completion, and stale-result policy. SQL's selected guards are not a complete implementation of these protocols.
9. Keep all state mutations and evidence associations auditable through events. Populate proposal approval, publication, and the entire authorized fan-out in one transaction. Closing a delivery does not resolve an associated question; clear each obligation explicitly.
10. Discover required CI checks for every new PR head and create their pending rows. `current_ci_checks` deliberately returns no old-head evidence after a restack. Zero known required checks must not be interpreted as CI passing.

Use the `schema.sql` connection pragmas, including `recursive_triggers=ON`, on every writer. Recursive triggers preserve delete guards even if an accidental `REPLACE` would otherwise silently replace a row. The design intentionally has no cascading history deletion.

The DDL is a **fresh-database schema**, with `user_version=1`, not an upgrade migration. WAL and full synchronization are requested for a local file database; physical durability still depends on the filesystem/storage. The example is constructed in memory and backed up to a standalone SQLite file for inspection.

## Example and validation scope

The fixture contains an accepted contract task, an implementation task blocked during a running tool, an acknowledged but unresolved urgent conflict, a pending pause despite message acknowledgment, a mediated publication, revision history, resource claims, and an unsubmitted integration PR with CI not yet run. Every table has at least one row.

All process IDs, session handles, repository paths, provider/model names, PR data, and execution outcomes are synthetic. Only the small [artifact files](demo-artifacts/) and their recorded hashes are real local fixture data. The fixture illustrates a database snapshot; it does not execute an orchestration timeline.

The tests exercise schema creation, all read views, foreign-key/integrity checks, role/model independence, exclusive runs/scopes, stale ownership, durable receipt boundaries, immutable history, cycles, late acknowledgments, cancellation, unresolved control/effects, artifact/check acceptance gates, and CI tied to the current commit. They do not claim live transport, cancellation, concurrent daemon recovery, or provider deduplication has been validated.
