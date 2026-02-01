# Projects (Agnostic)

A practical, end-to-end guide for planning, scoping, executing, and validating projects. Designed to reduce risk and ambiguity while keeping delivery atomic and testable.

## TL;DR

- Start with outcomes and constraints, not solutions.
- Make assumptions explicit and validate early.
- Frame 2-3 options, decide, and record the tradeoffs.
- Decompose into atomic, CI-safe tasks with clear DoD.
- Build observability and guardrails before launch.
- Close the loop post-launch with metrics and follow-ups.

## Principles

- Start with outcomes, not solutions.
- Make assumptions explicit; validate early.
- Keep scope tight and reversible.
- Prefer small, atomic deliverables that pass CI.
- Build observability and safety into the plan.
- Decide once, document decisions, move forward.
- Make constraints visible: budget, latency, reliability, legal, and time.
- Favor reversible decisions until evidence is strong.

## Phase 1: Problem, Outcome, and Success

### 1) Problem statement
- What is broken or missing?
- Who is affected?
- Why now?

### 2) Desired outcome
- What changes in the world if this succeeds?
- What user or business behavior changes?

### 3) Success metrics
- Leading indicators (early signal of progress)
- Lagging indicators (business impact)
- Baseline values (current state)

### 4) Non-goals
- Explicitly exclude scope to avoid drift.

### 5) Constraints and invariants
- Performance, reliability, security, compliance
- Backward compatibility and data integrity
- Cost and capacity limits

## Phase 2: Stakeholders and Ownership

### Identify stakeholders
Common roles to consider:
- Sponsor (budget/priority)
- Product (requirements)
- Engineering (implementation)
- QA (validation)
- SRE/Infra (reliability)
- Support/Success (user feedback)
- Security/Legal/Privacy (risk)
- Data/Analytics (measurement)
- Sales/Marketing (go-to-market)

### RACI (roles-and-responsibilities map)
RACI clarifies who does what:
- Responsible: does the work
- Accountable: owns the outcome and final decisions
- Consulted: provides input before decisions
- Informed: kept updated after decisions

Rule: only one Accountable per decision or task.

### DRI (Directly Responsible Individual)
The DRI is a single owner who drives a project or task to completion. This is usually the same person as the Accountable in RACI, but explicitly named as the execution owner.

## Phase 3: Discovery and Insights

### Gather inputs
- Interviews and stakeholder feedback
- Support tickets and incident history
- Logs, analytics, and metrics
- Shadowing the team closest to the action

### Capture assumptions and unknowns
- Track assumptions explicitly
- List unknowns and how you will resolve them

## Phase 4: Scope Radius

### Impacted surfaces
- UI, API, data, infra, analytics, docs

### Dependency radius
- Upstream/downstream services
- External vendors and integrations

### Data and contract changes
- Schema changes
- API contracts and compatibility

### Blast radius
- Worst-case impact if something fails
- Rollback and mitigation plan

### Scope cuts and MVP
- Define the smallest slice that proves the core hypothesis.
- Separate must-have from nice-to-have; keep a cutline list.
- Do not cut quality bars: security, data integrity, and reliability are non-negotiable.
- Prefer thinner depth over wider scope when timeboxed.

## Phase 5: Risk Register

### Risk types
- Technical (performance, correctness)
- Product (adoption, usability)
- Timeline (dependencies, staffing)
- Compliance (security, privacy)

### For each risk
- Severity and likelihood
- Mitigation plan
- Monitor or alert that detects it
- Kill criteria (when to stop or rollback)

### Pre-mortem
- List the top 3-5 ways this fails.
- For each: early signal, mitigation, and rollback/stop trigger.

## Phase 6: Decision Framing

- List 2-3 viable options (including "do nothing").
- Document tradeoffs and why a choice was made.
- Record the decision and its owner in the decision log.

## Phase 7: Design Sketch

- High-level architecture and data flow
- Alternatives considered and tradeoffs
- Migration path (if needed)
- Backward compatibility plan

## Phase 8: Data and Migration Plan

- Schema changes, backfills, and reversibility
- Data validation and integrity checks
- Rollout steps for data changes

## Phase 9: Experiment Plan

### Before building (validate hypotheses)
- Define the hypothesis
- Run a low-cost experiment (prototype, mock, manual test)
- Define success thresholds

### After building (validate efficacy)
- Measure impact against baseline
- Confirm no regression in core metrics
- Decide go/stop/iterate

## Phase 10: Observability and Guardrails

### Observability
- Metrics (p50/p95/p99, error rate)
- Logs (structured, request IDs)
- Traces (critical paths)

### Guardrails
- Alerts and thresholds
- Feature flags and kill switch
- Canary or staged rollout

## Phase 11: Delivery Plan

### Task decomposition
- Break work into atomic, CI-safe tasks
- Each task should be independently testable
- Prefer one PR per atomic unit

### Definition of Done
- Tests written and passing
- CI gates green
- Docs updated
- Monitoring in place
- Rollback plan verified
- Runbooks or support notes prepared
- Ownership for post-launch monitoring defined

### Readiness gate
- Observability and alerts configured
- Rollback or kill switch verified
- Data migration validated (if applicable)
- On-call/support briefed and ready

## Phase 12: Launch and Post-Launch

### Rollout
- Canary, staged, or gradual ramp
- Manual verification steps

### Post-launch
- Monitor impact against metrics
- Run a retro and document lessons
- Close the loop on decisions, risks, and follow-ups

---

# Templates

## Project Brief

- Title:
- Problem statement:
- Desired outcome:
- Success metrics:
- Non-goals:
- Constraints/invariants:

## Stakeholder Map

- Sponsor:
- Product:
- Engineering:
- QA:
- SRE/Infra:
- Support/Success:
- Security/Legal/Privacy:
- Data/Analytics:
- Sales/Marketing:

## RACI Matrix (Example)

| Task/Decision | Responsible | Accountable | Consulted | Informed |
|--------------|-------------|-------------|-----------|----------|
|              |             |             |           |          |

## DRI List

- Project DRI:
- Design DRI:
- Delivery DRI:
- Launch DRI:

## Assumptions and Unknowns

- Assumptions:
- Unknowns:
- Validation plan:

## Risk Register

| Risk | Severity | Likelihood | Mitigation | Monitor/Alert | Kill Criteria |
|------|----------|------------|------------|---------------|---------------|
|      |          |            |            |               |               |

## Pre-mortem

| Failure Mode | Early Signal | Mitigation | Rollback/Stop Trigger |
|--------------|--------------|------------|------------------------|
|              |              |            |                        |

## Cutlines and Kill Criteria

- Cutlines (scope that can be dropped):
- Kill criteria (when to stop or rollback):
- Rollback plan summary:

## Decision Log

| Date | Decision | Rationale | Alternatives | Owner |
|------|----------|-----------|--------------|-------|
|      |          |           |              |       |

## Options and Tradeoffs

- Option A:
  - Pros:
  - Cons:
- Option B:
  - Pros:
  - Cons:
- Option C (optional):
  - Pros:
  - Cons:
- Decision and rationale:

## Experiment Plan

- Hypothesis:
- Experiment type:
- Success threshold:
- Minimum data required:
- Result:
- Decision:

## MVP Scope

- Core hypothesis:
- Must-have slice:
- Nice-to-have cutlines:
- Quality bars (non-negotiable):

## Readiness Gate

- Observability and alerts configured:
- Rollback/kill switch verified:
- Data migration validated (if applicable):
- On-call/support briefed:

## Observability Checklist

- Metrics defined (p50/p95/p99, error rate)
- Logs include correlation/request IDs
- Traces cover critical path
- Alerts configured with thresholds
- Dashboard created

## Launch Checklist

- Feature flag/kill switch ready
- Rollout plan documented
- Manual verification steps prepared
- Support and on-call briefed
- Post-launch monitoring dashboard ready
