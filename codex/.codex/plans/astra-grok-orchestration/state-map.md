# Astra / Grok orchestration state map

This expands the [architecture plan](sources/brief.tex) into proposed state machines. It describes the intended runtime, not verified Codex or Grok capabilities. **Plan** means the original explicitly names the states or distinction; **Extension** means this document proposes the missing details. All transition rules below are design proposals subject to the plan's implementation gates.

[The SQLite data model](sqlite/README.md) maps these states to provider-neutral tables and views. Astra/Grok below name the original deployment; the schema separates coordinator/worker roles from model and adapter configuration.

“All states” means the application-visible states within the plan's scope, including failure and uncertainty. Provider-specific errors remain reason codes until the transport spike establishes which require distinct behavior.

The system has several independent state machines. A task can be `blocked`, its run `unresponsive`, its pause request `uncertain`, and its last report `acknowledged` at the same time. Do not collapse these into one agent status or enumerate their full Cartesian product.

## 1. Team, runtime, and coordinator

| Dimension | States | Transitions and meaning | Basis |
| --- | --- | --- | --- |
| Team lifecycle | `created`, `active`, `completed`, `cancelled` | Activate after initialization. Complete only after required tasks are accepted and required actions resolved. Cancel only after executing work is accounted for and termination is confirmed where necessary. | Extension |
| Runtime lifecycle | `starting`, `reconciling`, `ready`, `draining`, `stopped` | Startup enters reconciliation before dispatch. Graceful shutdown stops new dispatch and records the disposition of existing work. A crash can occur from any live state; the next start reconciles persisted facts. | Extension |
| Runtime health | `healthy`, `degraded`, `unavailable`, `unknown` | Health is observed separately from lifecycle. Include reasons such as storage failure or provider outage. Unknown means the observer lacks current evidence. | Extension |
| Coordinator authority | `unowned`, `owned`, `recovering` | Acquire ownership with a new epoch; reconcile before becoming ready to coordinate. A takeover replaces the owner and increments the epoch atomically. | Plan ownership; Extension labels |
| Coordinator session authority | `current`, `stale` | A replaced session becomes stale permanently for that epoch. Its mutating commands are rejected. Session liveness alone never grants authority. | Plan distinction |
| Coordinator availability | `available`, `busy`, `unresponsive`, `disconnected`, `unknown` | Busy may include a model turn, tool call, or context restoration. It does not imply dead or interruptible. Restore context and process actionable inbox items when available. | Extension |

Runtime health controls capabilities: if a durable write cannot commit, no receipt or new external effect may follow that failed write. Loss of a provider can hold only that provider's dispatch while other durable operations continue.

Team cancellation is requested through a control operation; the team remains active with dispatch held until the completion conditions are established. Pending task cancellation is not final team cancellation.

## 2. Plan revisions and dispatch

| Dimension | States | Transitions and meaning | Basis |
| --- | --- | --- | --- |
| Revision lifecycle | `draft`, `current`, `superseded`, `abandoned` | Commit a draft atomically as current and supersede the previous revision. Discard an unused draft as abandoned. Keep historical revisions immutable. | Extension around Plan revision IDs |
| Dispatch gate, per scope | `open`, `held` | Hold new execution for a team, task, or affected group during recovery, replanning, cancellation, or resource contention. Open only when every applicable hold is cleared. | Plan distinction; Extension representation |
| Hold reasons | Set of active reasons | Dependency, unresolved conflict, capacity, ownership recovery, pause, cancellation, unavailable provider, or uncertain previous execution. Clearing one reason must not clear the others. | Extension |
| Run revision compatibility | `current`, `unchecked`, `compatible`, `incompatible` | Equal revision IDs are current. An older result starts unchecked; Astra evaluates changed scope and dependencies to mark compatible or incompatible. Re-evaluate after another relevant revision. | Plan requirement; Extension labels |

Committing a new revision does not prove that workers received it. Each affected assignment needs its own delivery, acknowledgment, and, where paused, confirmed explicit resume. A new plan also cannot retroactively undo old side effects.

## 3. Task lifecycle

The seven task states are explicitly named in the plan. Transition details below fill gaps in that plan.

| State | Meaning | Allowed next states and guards |
| --- | --- | --- |
| `queued` | Accepted into the plan; not yet confirmed executing. Includes dependency and capacity waits. | `running` when execution is confirmed; `blocked` for an issue requiring intervention; `failed` for an unrecoverable setup failure; `cancelled` if withdrawn before execution. |
| `running` | The current attempt has begun task execution. | `awaiting_review` on a valid result; `blocked` on a work-stopping issue; `failed` after failure is established; `cancelled` only after cancellation is confirmed. |
| `blocked` | Progress requires a dependency, answer, replan, or recovery decision. Store the reason and any active attempt. | `running` when the same attempt can safely continue; `queued` when a new attempt is needed and the old one cannot still execute; `awaiting_review` if a valid result arrives; `failed` or `cancelled` after the relevant decision and execution accounting. |
| `awaiting_review` | A result exists; Astra has not accepted it. | `accepted` after evidence and compatibility checks; `running` for confirmed revision work in the same attempt; `queued` for a new revision attempt after the old attempt is closed; `blocked` for unresolved review issues; `failed` or `cancelled` by explicit decision. |
| `accepted` | Astra accepted the result against recorded criteria and revision. | Terminal for this task record under the proposed v1 policy. Follow-up work creates a linked task. |
| `failed` | Task-level failure has been established, with evidence or a reason. | Terminal by default. Explicit retry may reopen to `queued`, retaining the failure event and creating a new run when dispatched. |
| `cancelled` | Cancellation took effect; no current attempt can continue task execution. | Terminal under the proposed v1 policy. Restarted work creates a linked task. |

An assignment acknowledgment alone does not necessarily prove execution began. If the adapter cannot distinguish the two, define that limitation in the transport contract rather than silently treating them as identical.

`ready`, `waiting_for_dependencies`, and `waiting_for_capacity` are derived queue views. `retrying` is queued/running with a previous attempt. `revising` is a review decision followed by further execution. `paused` belongs to execution control. These do not need extra task enum values.

Acceptance is historical evidence, not a promise that every future plan can reuse the result. A later incompatible change holds affected downstream dispatch and creates corrective work; it does not silently rewrite the old acceptance.

## 4. Worker identity, process health, and attempts

| Dimension | States | Transitions and meaning | Basis |
| --- | --- | --- | --- |
| Worker registration | `registered`, `retired` | Stable worker identity outlives panes and processes. Retirement removes eligibility for new work after existing work is accounted for. | Extension |
| Worker allocation | `idle`, `reserved`, `assigned` | Reserve atomically before launch. Assign to an active run. Return to idle only after task execution has ended or been safely relinquished. | Extension |
| Run process health | `starting`, `running`, `unresponsive`, `exited`, plus `unknown` | The first four are in the plan. Starting becomes running on verified launch, or exited on definitive failure. Running and unresponsive can alternate. Exited is terminal for that process identity; unknown covers startup/recovery observation gaps. | Plan + Extension `unknown` |
| Attempt outcome | `open`, `result_reported`, `failed`, `cancelled`, `superseded` | An open attempt closes when it produces its final result, definitively fails, is cancelled, or safely yields to a replacement. Same-attempt revision work can reopen `result_reported` by explicit instruction. A retry always creates a new run ID. | Extension |
| Provider session availability | `available`, `unavailable`, `unknown` | Availability is observed independently of run identity. Resume a related session only when supported and verified; otherwise create a new session associated with the next run. | Extension |

An idle runner or reusable provider session may remain alive after a result. Whether the adapter uses one process per attempt or a persistent host session is an implementation choice; record process/session associations rather than redefining a run ID to mean a PID.

`unresponsive` does not establish `failed`; `exited` does not establish `accepted`. If a process disappears without a trustworthy outcome, the task is held for reconciliation. A `result_reported` attempt may still be rejected by Astra.

There is at most one executing attempt per task. Marking an old attempt superseded is not enough to satisfy that rule: verify it has stopped or enforce a boundary that prevents further execution before launching its replacement.

## 5. Pause, resume, and cancel

Desired behavior and observed behavior are separate fields. A model cannot confirm that an executing tool stopped merely by acknowledging a message.

| Dimension | States | Meaning | Basis |
| --- | --- | --- | --- |
| Desired execution | `run`, `pause`, `cancel` | Astra's durable instruction. A newer control generation supersedes an older desired instruction. Cancel is irreversible for that attempt. | Extension |
| Observed execution | `not_started`, `executing`, `paused`, `finished`, `unknown` | Runner-confirmed activity. Finished includes successful or unsuccessful cessation; inspect attempt outcome separately. Unknown never authorizes conflicting replacement work. | Extension |
| Control request outcome | `pending`, `applied`, `rejected`, `uncertain`, `superseded` | Pending waits for actual confirmation. Applied means the requested effect was established. Rejected includes unsupported operations. Uncertain means an attempted effect cannot be verified. Superseded requests retain their history. | Plan separation; Extension labels |

| Request | Required behavior |
| --- | --- |
| Pause before execution | Hold dispatch; confirm that task execution has not begun. |
| Pause during execution | Hold further task work immediately at the runtime boundary. Request adapter pause and wait for confirmation of the defined safe boundary. A running tool may have to finish first. |
| Resume | Require the active control generation, compatible assignment revision, cleared blockers, and confirmed transition to execution. Resuming does not override another hold. |
| Cancel | Hold dispatch, request cessation, account for child tools and external actions, then confirm the task/attempt cancellation. An acknowledgment or signal receipt is insufficient. |
| Control target already finished | Report that fact. A pause/resume can be rejected as no longer applicable. A cancellation decision must account for any existing result rather than pretend execution was interrupted. |
| Timeout or disconnect | Preserve `uncertain` until actual state can be determined. Reject stale confirmations as updates to current control state, but retain their observations as evidence. |

Keep only one current desired control generation per run. Late effects from an older generation still require reconciliation: ignoring the old acknowledgment cannot undo an old pause or external tool action.

## 6. Durable mutations and immutable events

| Situation | Outcome | Basis |
| --- | --- | --- |
| New valid request ID | Atomically commit the event, state changes, delivery rows, and idempotency record; return a durable receipt. | Plan |
| Same request ID and same canonical content | Return the original receipt without repeating the mutation. | Plan |
| Same request ID and different content | Reject the conflict without applying the new content. | Plan |
| Invalid sender, stale epoch, bad transition, or invalid artifact reference | Reject before mutation. Record diagnostic evidence separately if appropriate. | Plan constraints; Extension handling |
| Transaction fails before commit | No partial event, state, or delivery mutation survives. | Plan |
| Caller loses connection around commit | Caller has an unknown outcome. Retry/query using the same request ID to discover whether it committed. | Extension |

Persisted events have no mutable “read” or “resolved” state. They remain append-only. Delivery, issue resolution, and acceptance belong to separate records. Request rejection reasons are outcomes, not extra event lifecycle states.

## 7. Delivery, acknowledgment, and inboxes

Delivery is tracked per `(event_id, recipient_id)`. A publication to three workers can have three different delivery outcomes.

| Delivery state | Meaning | Next states | Basis |
| --- | --- | --- | --- |
| `pending` | Durably queued, no current attempt to send. | `sending`, `closed`. | Plan pending; Extension transitions |
| `sending` | A send intent is recorded; adapter invocation is in flight. | `delivered`, `retry_wait`, `uncertain`, `failed`, or directly `acknowledged` if acknowledgment races with send completion. | Extension |
| `delivered` | Adapter confirms submission to the intended session. | `acknowledged`; `retry_wait` when deduplicated retry is safe; `uncertain` if receipt cannot be established; `closed` by explicit disposition. | Plan distinction; Extension transitions |
| `acknowledged` | Protocol or recipient confirms this message ID was accepted. | Final delivery success; resolution may still be pending. | Plan |
| `retry_wait` | Retryable failure or acknowledgment timeout; next attempt is scheduled. | `sending`, `acknowledged` on late confirmation, `failed` after policy exhaustion, or `closed`. | Extension |
| `uncertain` | Submission or recipient acceptance may have happened, but available evidence is insufficient. | `acknowledged`, `delivered`, `retry_wait`, `failed`, or `closed`, depending on reconciliation evidence. | Plan requirement; Extension transitions |
| `failed` | Automated delivery has stopped after a definitive error or retry exhaustion. This does not prove the recipient never saw it. | Explicit retry to `pending`, late valid acknowledgment to `acknowledged`, or `closed`. | Extension |
| `closed` | Astra explicitly abandoned or superseded the obligation to deliver. Preserve a reason and any unresolved uncertainty. | No automated retry. Record late observations without restoring obsolete commands. | Extension |

Do not regress a known delivery fact because a later retry fails. Keep attempt history and monotonic `delivered_at` / `acknowledged_at` evidence; the current scheduling state is a projection over those facts.

Safe retry requires verified recipient deduplication using the same message ID. If the adapter cannot provide this, leave ambiguous sends uncertain and reconcile; the plan cannot promise duplicate-free execution from transport retries alone.

Inbox membership is derived:

| View | Includes |
| --- | --- |
| Normal inbox | Normal-priority items still requiring acknowledgment, review, or resolution. |
| Override inbox | Urgent actionable or unresolved items; coalesced by issue identity without deleting their events. |
| Worker inbox | Commands explicitly authorized by Astra for that worker/run. |
| History | All events, including acknowledged, resolved, failed, and superseded work. |

An acknowledgment removes the acknowledgment obligation only. An unanswered acknowledged question stays visible as unresolved. Reading a newer urgent event must not mark older normal events handled.

## 8. Questions, conflicts, proposals, and the bulletin

| Dimension | States | Transitions and meaning | Basis |
| --- | --- | --- | --- |
| Issue resolution | `open`, `resolved`, `dismissed`, `superseded` | Open until there is a recorded answer/action outcome. Dismissal requires a decision; supersession links the replacement issue. Recurrence can explicitly reopen an issue while retaining prior resolutions. | Plan resolution; Extension labels |
| Priority | `normal`, `urgent` | Scheduling attribute. Escalation/de-escalation is recorded; it does not alter commit sequence or grant interruption capability. | Plan |
| Proposal decision | `pending`, `approved`, `rejected`, `superseded` | Only Astra approves recipients and publication. Approval creates the publication and actionable recipient deliveries atomically. | Plan mediation; Extension labels |
| Publication validity | `current`, `superseded`, `withdrawn` | Derived from immutable publication and subsequent decisions. Replacing or withdrawing a publication must notify affected recipients when they need to act. | Extension |

Partial fan-out success is a summary of recipient deliveries, not an extra publication state. Routing failure after approval does not undo the approved publication. Workers cannot turn suggested recipients into authorized recipients.

## 9. Results, artifacts, and acceptance

| Dimension | States | Transitions and meaning | Basis |
| --- | --- | --- | --- |
| Artifact finalization | `staging`, `finalized` | Write and finalize the content, then hash it before committing a reference. A finalized version is immutable; edits produce a new version. | Plan contract; Extension labels |
| Artifact observed integrity | `unchecked`, `valid`, `missing`, `mismatch`, `unreadable` | Validate referenced content and its hash. Missing, mismatched, unreadable, or unchecked evidence cannot satisfy acceptance. Temporary read failure does not prove corruption. | Extension |
| Result review | `pending`, `accepted`, `changes_requested`, `rejected`, `superseded` | Astra records a decision against a particular result and assignment revision. A revised result creates new evidence and a new review record. | Plan acceptance; Extension labels |
| Acceptance checks | Per check: `pending`, `passed`, `failed`, `inconclusive` | Bind evidence to the artifact/commit that was actually checked. Changed content invalidates reuse of checks unless equivalence is established. | Extension |

Artifact registration and integrity are separate: a once-valid finalized artifact can later be missing. Finalization without a committed reference leaves an orphan file eligible for later cleanup, not an accepted result.

Acceptance requires the authorized coordinator, a valid result identity, checked revision compatibility, all required evidence, no unresolved acceptance blockers, and satisfaction of the task's execution-control contract. A worker's assertion, process exit code, or delivery acknowledgment cannot grant acceptance.

## 10. Launches, tools, and external effects

Use an operation record for process launches and other effects that cross the database boundary. This is an **Extension** implementing the plan's intent/reconciliation requirement.

| Operation state | Meaning | Allowed progression |
| --- | --- | --- |
| `intended` | Durable intent exists; effect is not yet known to have begun. | `in_flight`, `cancelled`. |
| `in_flight` | Invocation has been attempted; its result is not yet known. | `succeeded`, `failed`, `uncertain`. |
| `succeeded` | The operation's specific effect was confirmed. Launch success does not mean task success. | Terminal for that operation. |
| `failed` | Definitive operation failure, with any partial effects recorded. | A retry requires an explicit safe decision and linked attempt. |
| `uncertain` | Crash, timeout, or disconnection obscures whether/how the effect occurred. | Reconcile to `succeeded` or `failed`; retry only after absence of the effect or safe idempotency is established. |
| `cancelled` | Invocation was prevented before it began. | Terminal. An already invoked operation needs observed cessation and effect reconciliation, not this shortcut. |

Cancellation of an external operation is itself a control request. Some completed effects cannot be undone; any compensating action is a new authorized operation with its own outcome.

Record target identity and operation-specific idempotency/correlation IDs. Deduplicating the orchestration message does not guarantee exactly-once filesystem changes, PR creation, or external API effects.

## 11. Panes, worktrees, and exclusive write scopes

| Resource | States | Transitions and meaning | Basis |
| --- | --- | --- | --- |
| Team-owned pane | `reserved`, `idle`, `occupied`, `releasing`, `missing`, `uncertain` | Reserve before create/claim; observe the pane before use; release only after verifying ownership and associated execution. Reconcile disappearance or ambiguous creation before replacement/cleanup. | Plan ownership; Extension labels |
| Worktree | `provisioning`, `ready`, `in_use`, `releasing`, `released`, `failed`, `uncertain` | Verify branch/path before use. Release only after work is preserved and execution has ended. A provisioning/removal error can be failed or uncertain depending on observed effects. | Extension |
| Write-scope ownership | `unclaimed`, `held`, `quarantined` | Acquire exclusively for the executing attempt. Quarantine when the previous writer may still execute. Return to unclaimed only after execution has stopped or enforceable fencing exists. | Plan isolation; Extension labels |

Pane ownership records exact server, window, and pane IDs. Signal a process only after checking PID plus process start identity. An idle-looking screen is insufficient evidence of release. A missing pane does not prove its process or child tools exited.

Capacity exhaustion leaves tasks queued with a capacity hold. Unrelated sessions and panes are outside the managed resource state machine and must not be claimed or cleaned up implicitly.

## 12. Integration and PR validation

These are **Extensions** for stage 4; they do not add worker messaging permissions.

| Dimension | States | Meaning |
| --- | --- | --- |
| Integration task | Reuse the task lifecycle | One named integration worker assembles accepted changes. Merge conflicts block that task; they do not need another orchestration task state. |
| Change assembly | `pending`, `applying`, `conflicted`, `assembled`, `abandoned` | Applying may finish assembled or require conflict resolution. Reconcile interrupted git operations before retrying. |
| PR publication | `local`, `submitting`, `published`, `uncertain`, `failed` | Submit through Graphite within task authorization. Inspect an ambiguous submission before attempting another. |
| CI, per PR head | `not_run`, `pending`, `passed`, `failed`, `cancelled`, `unavailable` | Every PR must independently satisfy required checks. New commits/restacks require evidence for the resulting head. |
| PR disposition | `open`, `merged`, `closed` | Observed repository state. Merge is not automatically authorized by having a published PR or passing CI. |

Team completion is checked against the requested milestone. A published stack alone does not establish that every PR passed CI or that the combined result was accepted.

## 13. Recovery and race map

| Trigger / boundary | Observable state | Required next action |
| --- | --- | --- |
| Crash before a transaction commits | No durable mutation, or caller cannot tell | Retry/query the original request ID. Never reconstruct partial state from agent memory. |
| Commit succeeds but receipt is lost | Durable event exists; caller uncertain | Return the stored receipt on identical retry. |
| Launch intent committed, process not yet invoked | Operation intended | Establish whether launch occurred; launch once if absence is confirmed. |
| Process launched, handle registration not committed | Operation uncertain | Discover by durable correlation and process identity before considering another launch. |
| Send committed, process crashes before send | Delivery pending/sending | Reconcile and retry the same message ID according to deduplication guarantees. |
| Send succeeds, crash occurs before recording it | Delivery uncertain | Inspect recipient/session evidence; deduplicated retry only if supported. |
| Recipient acts, acknowledgment is lost | Delivery unacknowledged; action may exist | Reconcile action and receipt separately. Do not repeat the external effect blindly. |
| Urgent conflict arrives during a tool call | Issue open/urgent; run possibly executing | Hold affected new work; request pause; expose pending/uncertain control until the safe boundary is confirmed. |
| Old-revision result arrives | Result pending; compatibility unchecked | Preserve it, assess relevant dependency changes, then accept, request changes, or reject. |
| Result arrives after cancellation or supersession | Historical result event; terminal/current task state must not be overwritten | Retain evidence; reconcile any effects; require an explicit decision before reuse. |
| Result and cancellation race | Two valid events with a definite commit order | Re-evaluate guards transactionally. A stored result may remain reviewable; an accepted terminal task cannot silently become cancelled. |
| Pause and resume confirmations arrive out of order | Observation may refer to an old control generation | Retain observations, inspect actual activity, and apply only the current desired control. |
| Worker heartbeat stops | Health unresponsive/unknown | Inspect process, session, artifacts, and pending tools before failure or retry. |
| PID or pane ID is reused | Handle exists but identity/ownership differs | Refuse signaling/cleanup; reconcile the original run as missing or uncertain. |
| Coordinator takeover while old worker executes | New epoch owns control; old work may remain live | Reject stale coordinator commands and hold conflicting replacements until old execution is quiescent or effectively fenced. |
| Runtime restarts with an active worker | Runtime reconciling; run observation unknown | Restore identities, reconcile effects and controls, then reopen eligible dispatch. |
| Storage is full, unavailable, or transaction fails | Runtime degraded/unavailable for durable writes | Do not claim receipts or dispatch effects based on uncommitted intent. Preserve observable worker output for later reconciliation where possible. |
| Provider authentication, rate limit, or outage | Affected delivery/launch fails or waits | Record a reason; retry transient cases, surface persistent blockers, and avoid treating transport failure as task rejection. |
| Artifact disappears after result publication | Artifact missing; result still exists | Block acceptance, restore/replace verified evidence, or request revision. |
| Fan-out partly succeeds | Different delivery states per recipient | Retry only unresolved recipients; retain one publication and all recipient histories. |
| Screen is full or worktree setup fails | Task queued/blocked; resource unavailable | Keep the task durable, surface the reason, and dispatch after capacity or setup is resolved. |
| PR submission times out | Publication uncertain | Inspect the branch/PR before retrying; validate each resulting PR head. |

An ownership epoch fences commands to the runtime. It does **not** by itself stop an old worker from writing files or completing an already dispatched external action. Enforce the write boundary, isolate/quarantine the old worktree, or establish cessation before replacement execution. This must be demonstrated by the takeover fault test.

## 14. Forbidden combinations and transition rules

1. Two executing attempts may not hold the same task or conflicting write scope.
2. No dispatch while an applicable hold is active, ownership is recovering, or durable intent cannot be recorded.
3. Stale coordinator epochs cannot mutate current team state.
4. Pause/cancel acknowledgment without observed effect cannot produce confirmed paused/cancelled state.
5. A task cannot be accepted solely because its process exited, its message was delivered, or its result was acknowledged.
6. Acceptance cannot rely on missing/unverified artifacts, unchecked old-revision results, or validation for different content.
7. A known acknowledgment cannot be erased by a failed retry or a late send-completion event.
8. A task's terminal status cannot be overwritten by a late worker event; reopening requires an explicit allowed transition.
9. A worker cannot authorize routing, publication, result acceptance, or replacement coordinator ownership.
10. Completing/cancelling a team cannot silently abandon active tools, required unresolved issues, or uncertain external effects.
11. A retry cannot reuse an old run ID; a delivery retry must reuse the original message ID.
12. Cleanup cannot act on an unverified process, pane, worktree, or ownership claim.

Validate transitions in one transaction against current epoch, record version, task/run identity, plan revision, and control generation as applicable. On a race, retain the incoming evidence and reject or re-evaluate the stale state mutation; never apply it unconditionally.

## 15. Implementation gates and remaining choices

| Stage | States and boundaries to prove |
| --- | --- |
| 1. Transport spike | Actual launch, execution start, delivered versus acknowledged, session resume, pause/cancel safe boundaries, unsupported operations, exact coordinator wake-up, recipient deduplication. |
| 2. Store + pane lifecycle | Atomic state/event/delivery writes, idempotent requests, launch intents, resource reservations, identity-safe signaling, concurrent events, capacity queues. |
| 3. Routing + recovery | Every delivery crash boundary, urgent versus normal handling, fan-out, stale revisions, takeover fencing, ambiguous external effects, out-of-order control confirmation. |
| 4. Skill + integration | Bounded worker permissions, isolated writes, revision/retry decisions, acceptance, integration conflicts, submission reconciliation, required CI per PR. |

Before implementation, settle the adapter's process/session model, precise pause boundary, execution-start signal, retry/time-out policies, issue coalescing keys, and enforcement of stale-worker isolation. The failed-task reopen and terminal accepted/cancelled policies above are proposed defaults, not decisions already made by the original plan.
