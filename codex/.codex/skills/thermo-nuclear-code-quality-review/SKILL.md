---
name: thermo-nuclear-code-quality-review
description: Run an extremely strict maintainability audit of abstractions, file growth, branching, types, and architectural boundaries. Use for a thermo-nuclear code quality review, thermonuclear review, deep code quality audit, or especially harsh maintainability review.
---

# Thermo-nuclear code quality review

Audit the requested changes for implementation quality and codebase health. Be ambitious about restructurings that preserve behavior while deleting branches, helpers, modes, and layers. Look beyond local cleanup for a simpler way to model the problem.

This is a review. Report concrete recommendations; apply changes only when the user requests implementation or fixes. Return findings in chat unless the user explicitly requests GitHub comments. Do not submit an approval review merely because the audit passes.

## Establish scope

Read the repository's `AGENTS.md`, applicable nested instructions, and relevant architectural guidance. Honor the requested PR, branch, files, or whole-repository scope. Default to the current branch's changes against its actual base, using a PR's base or a stacked branch's parent when applicable. Include staged, unstaged, and relevant untracked source changes in a local branch audit unless the user requests committed changes only.

Resolve the target before reviewing. Do not review a different checkout when a specific PR was requested, or stash or overwrite local changes to switch targets. Inspect the diff, surrounding modules, callers, and existing canonical helpers. Separate complexity introduced by the change from pre-existing debt. Expand inspection to understand ownership and propose a sound restructuring, while keeping recommendations tied to the requested scope.

## Review standards

1. **Delete complexity.** Search for a reframing that removes concepts or control flow entirely. A refactor that spreads the same complexity across files is not an improvement. Prefer a simpler state model, ownership boundary, or default flow over polishing special cases.
2. **Challenge files crossing 1000 lines.** Compare base and head line counts. A change that takes a file from below 1000 lines to above 1000 lines is a presumptive blocker. Ask for decomposition and name the cohesive modules that could be extracted. Waive this only for a compelling structural reason when the resulting file remains clearly organized. Flag unjustified growth in already-large files too.
3. **Reject tangled branching.** New ad-hoc conditionals, scattered feature checks, one-off booleans, nullable modes, and temporary exceptions are design problems when they make existing flows harder to reason about. Prefer a typed model, dedicated policy, state machine, or existing owner when it removes that complexity.
4. **Demand useful abstractions.** Flag thin wrappers, identity helpers, pass-through layers, and generic mechanisms that hide a simple data shape. Prefer direct code. An abstraction earns its place by clarifying ownership, invariants, or repeated behavior.
5. **Clean up type boundaries.** Question unnecessary optionality, `any`, `unknown`, casts, loosely shaped objects, and silent fallbacks that obscure an invariant. Respect legitimate validation at external boundaries. Propose a typed contract that makes downstream control flow simpler.
6. **Keep logic with its canonical owner.** Find existing utilities before recommending new ones. Flag duplicate helpers, feature-specific logic in shared paths, APIs leaking implementation details, and logic placed in the wrong package, service, or module.
7. **Simplify orchestration and updates.** Flag unnecessary sequential execution when independent work could run concurrently and the result would be clearer. Flag related updates that can leave state half-applied when an atomic design is available. Account for ordering, shared state, and failure semantics before suggesting parallelism or transactions.

For every meaningful change, ask whether fewer concepts, branches, or layers could implement the same behavior. Check whether a cohesive module became more coupled or stateful. Explain what the reader now has to track and how the proposed design removes that burden.

## Recommendations

Offer a concrete alternative for each structural finding. Name the existing helper to reuse, the canonical owner to extend, the state model to simplify, or the responsibility to extract. Trace callers and contracts before claiming a restructuring preserves behavior. Describe any validation needed to establish equivalence.

Prefer deleting indirection, collapsing duplicate branches, and changing the model so special cases disappear. Extract helpers or split files when responsibilities are actually distinct. Separate orchestration from business logic when that clarifies both. Do not invent abstractions just to satisfy the audit, or substitute renaming suggestions for a structural fix.

## Findings and approval bar

Order findings by:

1. Structural regressions.
2. Demonstrated opportunities for substantial simplification.
3. Branching growth.
4. Boundary, abstraction, and type-contract problems.
5. File-size and decomposition concerns.
6. Remaining modularity and legibility problems.

Give each finding a precise file and line reference, the maintainability cost, a concrete behavior-preserving remedy, and the reason it should block or remain advisory. For size findings, include measured before and after line counts. Distinguish maintainability findings from verified runtime bugs; do not invent correctness severity for a design concern.

Treat unjustified threshold crossings, tangled feature checks, unnecessary wrappers or cast-heavy contracts, canonical-helper duplication, and clear missed opportunities to delete substantial complexity as presumptive blockers. Require evidence for both the problem and the alternative. A speculative rewrite or personal style preference is not a blocker.

Be direct and demanding without being rude. Prefer a few high-conviction structural findings over cosmetic nits. Correct behavior alone does not meet this review's bar. The implementation also needs justified file growth, clear ownership and types, and no obvious avoidable structural complexity.

If no findings survive verification, say that the change meets this maintainability bar and note material coverage limitations. Do not manufacture findings to sound strict.
