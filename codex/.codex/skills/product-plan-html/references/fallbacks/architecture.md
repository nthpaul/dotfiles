# Architecture guidance when pstack is unavailable

Use this reference only when capability discovery cannot find the applicable pstack
skills, or the user requests a standalone package. Installed skills take precedence.

Choose content that helps the audience understand the decision and the work required.
Read requirements and relevant source, record revisions and exact evidence for reuse
claims, and distinguish verified behavior from proposals and open questions. A source
checkout does not establish what is deployed. Include schemas, flows and diagrams only
when they explain the work or the user requests them; their absence needs no placeholder.

For data changes, choose ownership and authoritative records before proposing storage.
Document the fields and relationships needed to explain or implement the change. When
a full physical schema is requested, specify types, nullability, foreign-key targets,
cardinality and enforcement of important invariants. Match existing ID and time
conventions, distinguish local dates from instants, and derive redundant state.

For stateful features, define legal transitions, actor permissions, concurrent-update
behavior and what users see after rejection or failure. Trace the inputs, decisions and
observable results relevant to the feature. Include transaction writes and external
effects when they occur, keeping committed intent distinct from completed delivery.

Reuse authoritative services for the responsibilities they already own. For operations
that can be retried, make retries converge through stable request IDs, atomic writes,
current-state checks and bounded retries. Reconcile ambiguous external delivery. Add
durable effect records only when the operation needs them.

Use common structured inputs when repeated representations need to stay consistent.
Borrow and adapt layouts to the document's purpose. Label illustrative prototype
behavior, and record ownership tradeoffs when they affect the proposed work.

Verify the actual artifact and the claims it makes. Check included relationships,
state names, interactions and downloads for consistency, and inspect the rendered
document. A successful build alone is insufficient. An in-memory prototype verifies
its illustrative interactions, not backend behavior.
