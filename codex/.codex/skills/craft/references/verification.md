# Choose checks that match the work

Read the section relevant to the current task. The examples guide check selection; they are not mandatory suites. Preserve repository and domain requirements. Use existing checks where possible.

## Code and behavior

Establish the expected behavior from the request and actual callers or contracts. Exercise the changed behavior and the consequential exception paths. Check state transitions, retries, interruption, cleanup, and recovery only where the change makes them relevant.

Unit checks can verify a rule. Integration checks can verify a connection. Running the feature can verify what the user encounters. Choose the combination needed for this change. A compiler checks types and syntax; it does not establish that the feature does the requested job.

**Example:** after an inspection detects a fault, Back followed by Next must not erase the fault and permit delivery. Exercise that sequence through the actual controls and verify that repair is still required. A test of the normal completion path alone misses this failure.

## Writing and research

Check material claims against their actual sources. Preserve the distinction between evidence, inference, and recommendation. Recompute numbers where a conclusion depends on them, and check whether the cited source directly supports the associated claim.

Read the whole argument for a decision or understanding the audience can reach. Inspect the paragraphs for missing premises, unsupported certainty, inconsistent terms, or unnecessary detail. Open the delivered document when formatting or navigation affects its use.

**Example:** a memo says a trial caused a retention increase, but its data compares different cohorts without a causal design. Repair the claim and recommendation. Correct arithmetic alone cannot establish causation.

## Analysis and data

Inspect the inputs, definitions, units, denominators, time ranges, and missing values. Reconcile totals and independently recompute the calculations that drive the conclusion. Check whether a chart, table, and prose report the same calculation.

Probe the assumptions that could reverse the recommendation. Distinguish measured values from estimates, and state uncertainty where it affects the decision. Choose a few informative cases over a broad set of arbitrary scenarios.

**Example:** a dashboard and memo show different conversion rates because one denominator excludes incomplete sessions. Establish the intended definition, derive both views from it, and check the delivered values.

## Design and visual artifacts

Inspect the whole composition and the details that explain the subject. Check hierarchy, legibility, purpose, consistency, and interactions in the relevant sizes or modes. Use rendered artifacts and inspect every capture used as evidence.

Numerical geometry checks and automated accessibility checks establish specific properties. Viewing the result establishes whether it communicates the intended idea and has the required finish. Use magnification when small details matter; use motion samples when transitions matter.

Physical metaphors, isometric cameras, fixed part counts, and drawing-specific line rules belong to Anatomy. Carry over their purpose: clear structure, meaningful detail, sound connections, and observed behavior.

## Plans and operations

Check that steps have the necessary inputs, responsible owners, achievable outcomes, and compatible ordering. Inspect handoffs and material dependencies. Verify environment, authority, or recipient identity when a real operation depends on them.

For authorized changes, inspect the actual resulting state. Rehearse or verify recovery where failure would justify it. A proposed plan cannot establish that an operation has completed. Preserve uncertainty in estimates and dependencies that have not been confirmed.

**Example:** a deployment command exits successfully but targets the wrong environment. Compare the requested destination with the actual destination and resulting version. Command success alone does not verify the desired outcome.
