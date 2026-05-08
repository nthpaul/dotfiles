---
name: linear-create-ticket
description: Create or update Linear engineering issues with workspace-standard defaults and structure. Use when creating, backfilling, or correcting Linear tickets so they are assigned to `ple`, set to `Todo`, and written with the standard sections `Summary`, `Scope`, `Acceptance Criteria`, `Dependencies`, `Tests`, and `Notes`.
---

# Linear Create Ticket

Create or repair Linear issues so they match the workspace ticket contract.

## Defaults

Always apply these defaults unless the user explicitly asks otherwise:

- Assignee: `ple`
- State: `Todo`
- Body sections:
  - `## Summary`
  - `## Scope`
  - `## Acceptance Criteria`
  - `## Dependencies`
  - `## Tests`
  - `## Notes`

Treat each issue as one atomic PR. Keep scope narrow enough that one PR can pass CI independently.

## Create workflow

1. Build a concise title that matches one implementation slice.
2. Write the issue body using the standard sections.
3. Create the issue with explicit state and assignee.
4. Verify the created issue.

Preferred command shape:

```bash
linear issue create \
  --team <TEAM> \
  --project "<PROJECT>" \
  --title "<TITLE>" \
  --description-file <BODY_FILE> \
  --state "Todo" \
  --assignee "ple" \
  --no-use-default-template \
  --no-interactive
```

If the body is short, `--description` is acceptable. Prefer `--description-file` for multi-section markdown.

## Repair workflow

If an issue already exists but does not match the standard:

1. Update the assignee to `ple`.
2. Update the state to `Todo`.
3. Replace or correct the body so the standard sections are present.
4. Verify the final issue state and assignee.

Preferred command shape:

```bash
linear issue update <ISSUE_ID> \
  --assignee "ple" \
  --state "Todo" \
  --description-file <BODY_FILE>
```

## Body contract

Use this shape:

```md
## Summary

One paragraph describing the behavior slice and why it exists.

## Scope

- Concrete implementation changes included in this issue.
- Keep this list limited to one PR-sized slice.

## Acceptance Criteria

- Observable outcomes required for completion.
- Keep criteria testable and specific.

## Dependencies

- Upstream tickets or `None`.

## Tests

- Required unit, integration, migration, or manual validation coverage.

## Notes

- Atomic PR only.
- Repo name if relevant.
- Source-of-truth docs or rollout notes if relevant.
```

## Quality bar

- One issue maps to one atomic PR.
- Dependencies must be explicit when ordering matters.
- Do not combine contract work, migrations, runtime behavior, and rollout changes in one issue unless they are inseparable.
- Do not leave assignee blank.
- Do not leave the issue in `Triage`, `Backlog`, or another non-`Todo` state unless the user explicitly asks for that.

## Verification

After create or update:

1. Run `linear issue view <ISSUE_ID> --json` to inspect the body and state.
2. Split the identifier into team key and issue number if you need a machine-check for assignee.
3. Run a GraphQL check for assignee and state when needed.

Template:

```bash
linear api 'query {
  issues(filter: { team: { key: { eq: "<TEAM_KEY>" } }, number: { eq: <ISSUE_NUMBER> } }) {
    nodes {
      identifier
      state { name }
      assignee { name displayName }
    }
  }
}'
```

Replace `<TEAM_KEY>` and `<ISSUE_NUMBER>` with values from the real issue identifier. For example, `ENG-18171` becomes `ENG` and `18171`.

Check:

- `state.name == "Todo"`
- assignee resolves to `ple` or `Paul`
- description contains all six required sections

If verification fails, fix the issue immediately instead of leaving partial state behind.
