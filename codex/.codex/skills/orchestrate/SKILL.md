---
name: orchestrate
description: Coordinate explicitly requested separate Codex worker tasks while the coordinator only plans, delegates, guides, and reviews. Use for $orchestrate or an explicit request for this orchestration mode; ordinary work and subagent requests do not select this workflow.
---

# Orchestrate

Invoke as `$orchestrate <goal>`. Explicit invocation authorizes creating separate Codex tasks for bounded work toward that goal and using the model policy below. It does not authorize unrelated projects, external messages, purchases, publication, or recurring background runs. Preserve previously granted authorization and the user's constraints without asking again.

## Coordinator boundary

Only plan, delegate, guide, review worker evidence, and synthesize high-level conclusions in conversation. Do not implement, conduct original subject research, run experiments/tests, or generate deliverables. Delegate those activities, including publishing artifacts and maintaining the shared manifest, to workers. Reading skills, app metadata, worker reports, and finished artifacts to coordinate or review is allowed. Delegate concrete fixes after review. Never call spawn_agent or other subagent creation APIs. Workers are separate user-visible Codex tasks, created with create_thread. If that capability is unavailable, disclose the blocker; do not silently replace sessions with subagents or hands-on work.

## Model policy and identity

The requested coordinator policy is `gpt-6-astra` with `high` effort; workers use `gpt-6-astra` with `low` for bounded execution or `medium` for research, design, and review. Pass explicit `model` and `thinking` to create_thread, as authorized by this invocation. Check the live tool schema for availability; report an unsupported model instead of silently substituting. This skill cannot change the already-running coordinator's model. Verify only from exposed session metadata; report unknown if unavailable. Never edit global model defaults or use a self-message to claim the active turn switched models.

Acquire the coordinator's actual task ID before dispatch: prefer explicit current-task metadata; in a local session read only `CODEX_THREAD_ID` if present. A goal tool result is usable only if it actually contains a current thread ID; null or a goal ID is insufficient. Confirm uncertain candidates with read_thread and current task context. Do not assume the most recent task, a title, a source/delegating task ID, a UUID in a path, or a queued clientThreadId is the coordinator. If no reliable ID is available, request it before dispatch. Never hardcode an earlier run's ID.

## Dispatch and ownership

Read [references/worker-protocol.md](references/worker-protocol.md) before assigning work. Define outcomes, acceptance criteria, dependencies, authorization, and exclusive write scopes. Choose enough workers for useful independent work, within user budget and host limits. Use bounded assignments and exact artifact paths rather than copying full coordinator history. Workers must not create more workers.

Use list_projects before selecting a saved project. Choose the user's current project; do not inherit a project from an example or prior run. Follow the live create_thread schema: default Git project tasks to worktrees and non-Git tasks to local; use projectless for work without a repository. Honor explicit checkout/worktree choices. Shared filesystem paths only work on the same accessible host; arrange an authorized transfer worker otherwise.

Record returned threadId and hostId. If creation returns only clientThreadId, keep it as pending setup and resolve the real threadId through supported app metadata before messaging or waiting. Emit the required created-thread directive in the user-facing response. Reuse an existing worker for related follow-ups; create a new task for independent scope. After uncertain creation, inspect task metadata before retrying to avoid duplicates.

Assign one worker to maintain shared manifest/checkpoints. Each worker owns its status and deliverables; shared integration has one named owner. Prevent concurrent writes to the same files. For code work, require applicable AGENTS.md, isolated worktrees, and atomic CI-passing PR stacks; use gt create and gt submit --no-interactive instead of git commit/push when PR work is authorized.

## Review and persistence

Wait explicitly after dispatch. Prefer wait_threads with compact cursor snapshots (up to eight targets, their exact hostId/threadId, and afterCursor). Use bounded waits consistent with the host's communication requirements, then back off; read_thread is for focused detail or missed context. Do not narrate unchanged polls. Idle, a finished turn, and a status report are not proof of completion.

Review deliverables against acceptance criteria and provenance; return gaps to their owner. Use a separate review task when material risk warrants it. Summarize decisions in chat; have a worker integrate final files. Keep work active until required artifacts and verification exist. Do not mark a goal complete because time or tokens are low, or create a goal/budget without explicit authorization. Preserve checkpointed scope across compaction.

Only create native heartbeat automation when the user authorizes background monitoring, scheduled continuation, or equivalent future work. Inspect existing automation first; prefer updating it. Save exact task IDs, remaining scope, stopping conditions, and notification intent. Stay quiet for unchanged/non-actionable states; notify meaningful change, completion, failure, or needed user action. Use native automation tools, not shell sleep loops or invented scheduling directives. End or pause the authorized monitor once its purpose is complete. Without scheduling authorization, report remaining work honestly and never promise an automatic wakeup.

Finish only after required worker outputs have been reviewed, necessary fixes verified, and the final artifact owner confirms integration. State exact deliverable paths, validation evidence, unresolved limitations, and which tasks remain active, if any.
