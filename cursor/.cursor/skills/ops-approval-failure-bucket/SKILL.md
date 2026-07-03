---
name: ops-approval-failure-bucket
description: >-
  Classify Neutron OPS action_proposals execution failures into preventable bad
  proposals, valid execution guards, and true bugs before planning fixes. Use when
  investigating ops approval success rate, FAILED proposals, or 80/20 improvement
  planning for Neutron Slack ops cards.
---

# Ops approval failure bucketing

Reframe "execution success rate" **before** writing code. Raw `FAILED` rows mix correct rejections with preventable bad proposals.

## Data source

Neutron Postgres: `action_proposals` where `proposal_kind = 'OPS'`.

Query recent window (e.g. 3–7 days) for executed proposals:

```sql
SELECT
  status,
  error_message,
  COUNT(*) AS n
FROM action_proposals
WHERE proposal_kind = 'OPS'
  AND status IN ('COMPLETED', 'FAILED', 'EXECUTED')  -- adjust to your schema
  AND executed_at >= NOW() - INTERVAL '3 days'
GROUP BY 1, 2
ORDER BY n DESC;
```

Use `user-traba-db` MCP or read-only prod access per team norms.

## Three buckets

| Bucket | Meaning | Fix layer |
|--------|---------|-----------|
| **Preventable bad proposal** | Ops should never have seen an approval card | **Propose-time preflight** (server) + agent guidelines |
| **Valid execution guard** | Backend correctly rejected stale/invalid state | Not a bug — improve **agent preflight** or ops messaging; don't count as regression |
| **True bug / infra** | Version mismatch, null error, wrong attribution, retryable conflict | **Backend fix** or idempotent retry |

## Classify by error_message patterns

### Valid execution guards (do not chase as bugs)

- Shift ended / already complete
- Worker not on roster / not booked on shift
- Already clocked in / out / wrong jobStatus (not TODO)
- ALL_IN_REQUEST / use schedule-level action instead
- No slots / shift full (when not bypassed)
- "Added 0 of N" / "Accepted 0 of N" (often eligibility or state)
- Eligibility failures that ops didn't explicitly bypass

### Preventable bad proposals (highest ROI — block at propose)

Same patterns as above, but caught **before** the approval card persists:

- Server-side preflight via `callTrabaAsOperator` (shift state, roster, eligibility)
- Agent should not propose; server returns tool error instead

### True bugs / infra (fix backend or retry)

- Publish **version mismatch** on `PUBLISH_SHIFT_DRAFT` → re-read + retry once
- **Null `error_message`** on FAILED (historical spikes — check if still happening)
- Wrong **cancellationSource** default when ops intent was business-initiated
- Transient API errors without surfaced message

## Report template

```markdown
## Ops approval failure analysis (<date range>)

**Executed proposals:** N  
**Completed:** X (Y%)  
**Failed:** Z

### Bucket summary
| Bucket | Count | % of failures | Recommended fix |
|--------|-------|---------------|-----------------|
| Preventable bad proposal | | | Propose preflight (stack 1) |
| Valid execution guard | | | Guidelines / accept as healthy guard |
| True bug / infra | | | Targeted backend PR |

### Top error_message rows
(paste top 10 with counts)

### 80/20 recommendation
1. <highest-count preventable bucket> → server preflight
2. <next infra bug> → backend retry/fix
3. Skip: new terminal status / observability until proposal quality improves
```

## 80/20 stack template (after bucketing)

| Priority | Repo | Scope |
|----------|------|-------|
| 1 | the-matrix | Server propose preflight for top failure actions |
| 2 | the-matrix | Eval + guidelines enforcing preflight |
| 3 | traba | Retry/fix for infra failures (e.g. publish version) |
| 4 | both | Cross-repo param (propose schema + executor) |
| Skip | — | New FAILED sub-status, dashboards until metrics are clean |

## Pair with

- `ops-propose-preflight` (the-matrix project pattern — when implemented)
- `graph-stack-merge-order` when shipping cross-repo fixes
- `parallelize-work-cursor` only for independent stacks (preflight vs publish retry)
