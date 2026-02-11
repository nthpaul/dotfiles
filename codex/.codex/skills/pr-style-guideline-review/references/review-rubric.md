# PR Style/Guildeline Review Rubric

Use this rubric only after loading local repo rules.

## Severity guidance
- high: likely bug/regression, broken contract, or clear architecture violation.
- medium: maintainability risk, partial guideline drift, missing test coverage for changed behavior.
- low: style inconsistency or minor clean-up with low risk.

## What to cite
- `AGENTS.md` instructions
- lint/type/format rules from local config
- established nearby patterns in touched modules

## Findings template
- severity
- file:line
- guideline violated
- impact
- concrete fix suggestion

## Non-goals
- do not enforce personal preferences without a source
- do not expand scope beyond PR intent unless risk is clear
