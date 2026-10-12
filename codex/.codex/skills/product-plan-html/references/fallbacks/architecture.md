# Architecture guidance when pstack is unavailable

Use this reference only when capability discovery cannot find the applicable pstack
skills, or the user requests a standalone package. Installed skills take precedence.

Read requirements and relevant source before proposing tables, services or screens.
Record repository revisions and exact evidence for load-bearing reuse claims.
Distinguish requirements, verified existing behavior, design decisions and open policy
questions. A source checkout does not establish what is deployed.

Choose ownership and data structures first. Give each table a purpose, every field a
type and nullability, each foreign key a target and cardinality, and each important
invariant an enforcement boundary. Match existing physical ID types and time conventions.
Keep local dates separate from instants. Derive state when it follows from authoritative
records rather than creating independently mutable flags.

For stateful features, define legal states, transitions, commands, actor permissions,
concurrent-update behavior and what users see at each state. State the return path from
rejection and failure. Trace input, reads/decisions, transaction writes, execution and
observable results. Keep committed intent distinct from completed external effects.

Reuse existing authoritative services for mutations, eligibility, notification delivery,
scheduling and authorization. Make retries converge: stable request IDs, atomic writes,
current-state checks, bounded retries and visible failures. Where external delivery can
be ambiguous, reconcile it instead of blindly resending. Use a durable effect record
only when the requirement needs it; do not add a generic workflow engine by default.

Build the reusable mechanism that produces and checks the artifact. Generate repeated
schema and diagram representations from common structured inputs. Keep feature-specific
prototype actions explicit and label their illustrative behavior. Compare plausible
alternatives when ownership is uncertain, then record the chosen boundary and tradeoff.

Verify the actual outputs: fields and relationships agree, flows use the same state
names, browser interactions update the relevant surfaces, downloads work and the final
bundle renders. A successful build alone is insufficient. Do not claim backend behavior
was tested by an in-memory prototype.
