# Worker protocol

Use this assignment template; replace every bracketed field before sending through create_thread. Do not send the coordinator's full history.

```text
You are an explicitly user-requested separate worker task, not a subagent.
Coordinator task ID: [verified threadId]. Host: [hostId].
Role: [role]. Goal: [bounded outcome].
Model policy: gpt-6-astra, [low or medium]. Do not create workers or subagents.
Inputs: [exact paths, relevant URLs, requirements, dependencies].
Exclusive write scope: [absolute directory/files or isolated checkout].
Shared artifact root: [absolute path]. Manifest owner: [worker ID or pending].
Deliverables: [exact files, editable sources, format].
Acceptance criteria: [observable outcomes and required checks].
Authorization: [permitted work and existing approvals; explicit exclusions].
Read applicable AGENTS.md and relevant skills. Preserve unrelated changes.
For research, retain a claim/source ledger with direct URLs, publication date
when available, access date, and the precise supporting section. Label
fact, inference, proposal, and unknown. Paraphrase; do not reproduce articles.
For performance claims, distinguish measurements from hypotheses and record
workload, environment, method, and limitations. Never invent benchmark results.
Send WORKER_UPDATE via send_message_to_thread to the coordinator upon scope
acceptance, material progress/blocker, review readiness, and completion.
Keep status.md in your directory. Do not send periodic unchanged updates.
Final report: exact artifact paths, checks and evidence, unresolved risks.
Stop after completing this scope unless a follow-up arrives.
```

Standard update (use `none` when a field is empty):

```text
WORKER_UPDATE | role=[role] | status=working|blocked|review_ready|complete | artifacts=[absolute paths] | findings=[concise evidence] | risks=[limitations] | next=[remaining step or none] | request=[none or precise needed decision]
```

Choose one status value. `review_ready` means deliverables and checks are available for review; `complete` means the assigned scope is finished, not that the entire project is accepted. Workers retain real thread/host IDs for peers; no title-based routing.

The manifest owner maintains `manifest.md` with goal, acceptance criteria, authorization boundaries, coordinator ID, worker IDs/hosts, roles, model/effort requested, owned paths, dependencies, state, outputs, and evidence links. Distinguish requested model from verified active model. Do not put secrets into the manifest.

Maintain `checkpoint.md` at meaningful transitions: accepted decisions, completed criteria, rejected claims, pending fixes, current artifact versions or hashes, remaining steps, exact task IDs, wait cursors when useful, and any authorized monitor ID/stop condition. Worker `status.md` records current scope, progress, blockers, deliverables, and verification. The coordinator delegates these writes.

Review gates:

1. Scope: files exist in owned paths; all acceptance criteria addressed; editable sources retained.
2. Evidence: important factual claims map to primary sources and dates; inference and proposal stay labeled; unknowns remain visible. Measurements include reproducible method and raw evidence.
3. Quality: relevant tests/checks pass. Visual artifacts have rendered inspection evidence; CI is required for each submitted atomic PR where applicable.
4. Integration: a named owner incorporates accepted results and fixes, checks cross-artifact consistency, updates manifest/checkpoint, and reports exact final paths.

A failed gate produces a bounded follow-up to the owning worker. Do not accept a confident summary as a substitute for the artifact or verification.
