---
name: new-launch-mm-checks
description: >-
  Pre-launch readiness check for a Match Maker region. Use for "run the new launch checks for
  <region>", "is <region> ready to launch", "check the MM build for Denver", "what's missing before
  we launch Tulsa", "are the role configs and onboarding sessions set up in <region>", or any ask to
  compare a region's role requirements against what Match Maker actually gates on.
version: 2.2.0
---

# New launch MM checks

Answer one question for an operator: **can this region launch, and if not, what has to change.**

Output is five short sections, each naming roles and ending in an action. Never a column dump.

## Inputs

One region slug. Live slugs:

```
charlotte-nc  chicago-il  denver-co  elpaso-tx  greaterchicago-il  louisville-ky
minneapolis-mn  portland-or  reno-nv  swedesboro-nj  tulsa-ok
```

`chicago-il` and `greaterchicago-il` are separate live regions. Never merge them without asking.

Prod reads go through the local CLI. Write every flag out literally — an unquoted multi-word
shell variable reads as a missing command and gets misdiagnosed as auth expiry.

```
/Users/nitish/Documents/google-cloud-sdk/bin/bq --project_id=traba-app query --use_legacy_sql=false --format=csv '<sql>'
```

All prod tables live in `traba-app.pg_export_prod_public`. Repo root for the local half:
`/Users/nitish/Documents/shift-matching/shift-matching/match-making/charlotte`.

On `Reauthentication failed`, stop and ask the operator to run `! gcloud auth login`. Do not guess
table contents.

## 1. Is the region built

```sql
SELECT regionId, COUNT(*) builds,
       MAX(createdAt) latest_attempt,
       MAX(IF(finishedAt IS NOT NULL, createdAt, NULL)) latest_finished,
       COUNTIF(finishedAt IS NULL) unfinished
FROM `traba-app.pg_export_prod_public.placement_matrix_builds`
WHERE regionId = '<region>' GROUP BY 1
```

No rows means the region has never built and nothing below applies. Report that and stop.
A `latest_finished` over 48 hours old means the daily run is broken; say so before reporting anything
derived from it, because every later section reads that build.

**Always pin to the latest build with `finishedAt IS NOT NULL`.** An in-flight or failed build has
a null `demandSnapshot` and no pairs, so ordering by `createdAt` alone silently returns an empty
section 5 that reads as "no demand" rather than "no build". When `latest_attempt` is newer than
`latest_finished`, say a build is in flight or failed and report on the finished one.

Pin that build id once and reuse it. Aggregating across builds multiplies the same demand by the
number of daily runs.

## 2. Role config completeness

```sql
SELECT roleId, isActive, workerFacingRoleName, bgcRequired, drugTestRequired,
       experienceMinMonths, onboardingSessionLocation, onboardingSessionDays,
       onboardingSessionTime, onboardingContactName, transitNote
FROM `traba-app.pg_export_prod_public.placement_matrix_role_configs`
WHERE regionId = '<region>' ORDER BY isActive DESC, roleId
```

Grain is (regionId, roleId) and the table is hand-curated, so every gap is a person's unfinished
work rather than a pipeline failure. Report as gaps:

- `isActive = false` on a role ops expect to be live.
- `workerFacingRoleName` unset. Workers see the raw role name in texts. Unset on almost every
  config in every region, so report it as a launch checklist item, not an anomaly.
- Any `onboardingSession*` field unset. These populate only in mature regions; a new region with
  them empty cannot book anyone.

The `onboardingSession*` columns here are the standing details a role advertises (where, which
weekday, who to ask for). The dated sessions people actually book onto are separate rows in
section 3. A region can have one and not the other, so check both.

## 3. Onboarding sessions

```sql
SELECT s.id, s.capacity, TO_JSON_STRING(s.roleIds) roleIds,
       COUNT(DISTINCT c.id) booked
FROM `traba-app.pg_export_prod_public.placement_matrix_onboarding_sessions` s
LEFT JOIN `traba-app.pg_export_prod_public.conversations` c
  ON JSON_VALUE(c.metadata, '$.recruiting.onboardingBooking.sessionId') = s.id
WHERE s.regionId = '<region>' GROUP BY 1,2,3 ORDER BY booked DESC
```

**No rows is the most common real gap.** A region can build daily and have no session configured
at all, which means nobody in it can be booked. Report that as a blocker before anything else in
this section, and name it as ops work rather than a pipeline fault.

State two limits in the output every time, because an operator will otherwise read `booked` as
attendance:

- **Bookings are not attendance.** No table records who showed up. The nearest proxy is the
  in-person I-9 reaching `SECTION_2_COMPLETED` in `i9_status`, and that is a model, not a column.
- **`capacity` is NULL on every session**, so there is no fill-rate denominator. Never compute one.

Declines live at `conversations.metadata.recruiting.declinedOnboardingSessionIds`; people who said
no are the TENTATIVE AVAILABILITY follow-up list, not lost.

## 4. Required attributes

**The build reads shift-level MUST_HAVE rows and unions them across every shift in a group.** From
`placement-matrix-recruiting.source.ts`:

```ts
await this.prisma.client.shiftRequiredAttribute.findMany({
  where: { requirement: AttributeRequirement.MUST_HAVE, shiftId: { in: shiftIds } },
})
// then, per group:
[...new Set(demand.shiftIds.flatMap((id) => mustHaveNamesByShiftId.get(id) ?? []))]
```

So the only source that matters is `_shift_required_attributes` filtered to `MUST_HAVE`.
**Do not read `role_attributes_v3`** — the build never looks at it, and the role page will disagree
with what workers are actually gated on. **Do not read
`shift_request_required_attribute_levels`** — that is the V2 table and its `level` values are
proficiency grades (`HIGH`, `FIVE_STAR`, `REPORTED`), not requirement flags. The V3 tables are
underscore-prefixed: `_shift_required_attributes` and `_shift_request_required_attributes`.

### The check: one stray shift gates a whole group

Because the group takes the union, an attribute set as MUST_HAVE on a single shift applies to every
worker scored against that group. Find attributes set on only a minority of a role's shifts.

```sql
WITH b AS (
  SELECT id, demandSnapshot FROM `traba-app.pg_export_prod_public.placement_matrix_builds`
  WHERE regionId = '<region>' AND finishedAt IS NOT NULL ORDER BY createdAt DESC LIMIT 1
),
grp AS (
  SELECT JSON_VALUE(d, '$.seedRoleId') roleId,
         JSON_VALUE(d, '$.payRate') pay,
         JSON_VALUE(d, '$.daysOfWeek') days,
         SAFE_CAST(JSON_VALUE(d, '$.openSlots') AS INT64) slots,
         COALESCE(NULLIF(JSON_VALUE(d, '$.requiredAttributes'), ''), '') gate
  FROM b, UNNEST(JSON_QUERY_ARRAY(b.demandSnapshot)) d
),
sh AS (
  SELECT roleId, COUNT(DISTINCT id) total FROM `traba-app.pg_export_prod_public.shifts`
  WHERE startTime > CURRENT_TIMESTAMP() GROUP BY 1
),
seton AS (
  SELECT s.roleId, a.name attr, COUNT(DISTINCT s.id) w
  FROM `traba-app.pg_export_prod_public.shifts` s
  JOIN `traba-app.pg_export_prod_public._shift_required_attributes` x ON x.shiftId = s.id
  JOIN `traba-app.pg_export_prod_public.attributes` a ON a.id = x.attributeId
  WHERE x.requirement = 'MUST_HAVE' AND s.startTime > CURRENT_TIMESTAMP()
  GROUP BY 1, 2
)
SELECT r.roleName, g.pay, g.days, g.slots, attr,
       se.w, sh.total, ROUND(100 * se.w / sh.total) pct_of_shifts
FROM grp g
LEFT JOIN UNNEST(SPLIT(g.gate, ',')) attr
LEFT JOIN sh ON sh.roleId = g.roleId
LEFT JOIN seton se ON se.roleId = g.roleId AND se.attr = attr
LEFT JOIN `traba-app.pg_export_prod_public.roles` r ON r.id = g.roleId
ORDER BY r.roleName, g.slots DESC, pct_of_shifts
```

**Report at GROUP grain, not role grain.** Match Maker splits a role by pay, days and requirement
set, and ranks each split as its own card. A role with two pay bands produces two suggestions. A
table with one row per role will not reconcile against what the board shows, and that mismatch is
the first thing a reader notices.

Groups come from `demandSnapshot[]` on the pinned build: `payRate`, `daysOfWeek`, `openSlots` and
`requiredAttributes` (the union the scorer used). Join the shift-level counts in as evidence.

**Always emit this table for every region, even one that gates on nothing.** A region with no
requirements gets a row per group reading `no gate`, never a sentence saying the table was skipped.
A missing table reads as an oversight and cannot be told apart from a region nobody checked.

| Column | Source |
|---|---|
| Role | `roles.roleName` |
| Group | `$<payRate>` and abbreviated `daysOfWeek` |
| Slots | `openSlots`; flag `0 open` — fully booked groups stay ranked by design |
| MM gates on | `requiredAttributes` from the group |
| Set on | `n of N (pct%)` — how many of the role's upcoming shifts carry each attribute |
| Check | The verdict below |

Truncate attribute names past 22 characters with the full name on hover.

| Verdict | When | Action |
|---|---|---|
| `likely mis-set` | Any gated attribute on under 20% of the role's shifts | Ops. Open the shift in the ATS and remove it. |
| `partial` | Backed by some shifts, not all | Check the split is deliberate. |
| `all shifts` | Every shift carries it | Intentional. Confirm it suits the role. |
| `no gate` | Group requires nothing | Filters nobody. Cross-check section 5. |

**The union is what makes a 1% attribute dangerous.** One shift carrying a must-have gives the whole
group that gate, so a single stray shift spawns an extra card and rejects everyone who lacks it.
Quote the ratio, not just the attribute name: `1 of 101 (1%)` makes the case on its own.

**Shifts starting within 18 hours cannot be edited.** Expect at least one locked shift per cleanup.
Say which ones are locked and that they clear themselves once the shift starts, so nobody waits on
an edit that cannot be made.

Report anything under about 20% as a likely mis-set requirement. The lower the share, the more
certain: an attribute on 4 of 430 shifts was almost certainly not meant to gate the role, and it is
gating every worker scored against any group containing that shift.

Give the operator the shift link so they can fix it:
`https://ops-console.traba.tech/shifts/details/<shiftId>` (the ATS). Field monitor is the same id
at `/field-monitor/<shiftId>`.

A high share is not automatically correct either. An equipment attribute on 100% of a skilled
role's shifts is right; the same attribute on 100% of a general-labour role's shifts is worth
questioning with ops.

### What the group actually gated on

`demandSnapshot[].requiredAttributes` on the build records the union the scorer used. Compare it to
the per-shift picture above when a group's gate looks wrong, and quote the group's `scheduleId`,
whose third segment is a hash of the requirement set and is shared by any group with the same set.

Also check whether experience reaches the score. `experienceState` can read `insufficient` while
`qualScore` is identical to a role with no experience requirement.

## 5. Top roles — demand against where supply concentrates

Demand is `openSlots` inside the build's `demandSnapshot`. Supply concentration is the count of
workers ranking a role first.

```sql
WITH b AS (
  SELECT id, demandSnapshot FROM `traba-app.pg_export_prod_public.placement_matrix_builds`
  WHERE regionId = '<region>' AND finishedAt IS NOT NULL ORDER BY createdAt DESC LIMIT 1
),
demand AS (
  SELECT JSON_VALUE(d, '$.seedRoleId') roleId,
         JSON_VALUE(d, '$.companyName') company,
         SAFE_CAST(JSON_VALUE(d, '$.openSlots') AS INT64) openSlots
  FROM b, UNNEST(JSON_QUERY_ARRAY(b.demandSnapshot)) d
),
top1 AS (
  SELECT SPLIT(p.scheduleId, '::')[OFFSET(0)] roleId, COUNT(*) ranked_first
  FROM `traba-app.pg_export_prod_public.placement_matrix_pairs` p
  JOIN b ON b.id = p.buildId
  WHERE p.rank = 1 GROUP BY 1
)
SELECT r.roleName, d.company, d.openSlots, COALESCE(t.ranked_first, 0) ranked_first,
       IF(d.openSlots = 0, 'NO DEMAND',
          CAST(ROUND(COALESCE(t.ranked_first, 0) / d.openSlots, 1) AS STRING)) supply_per_slot
FROM demand d
LEFT JOIN top1 t USING (roleId)
LEFT JOIN `traba-app.pg_export_prod_public.roles` r ON r.id = d.roleId
ORDER BY IF(d.openSlots = 0, 1e9, COALESCE(t.ranked_first, 0) / d.openSlots) DESC
```

`demandSnapshot.seedRoleId` holds a platform role UUID, not the seed's readable `role_id`. Join
`roles` for `roleName` so the operator sees a job title. To tie a row back to the seed, map through
`platform_role_id` in the region's seed file.

Read it as a ratio, not two columns. A role with few slots and thousands ranking it first is a
**sink**: it is absorbing workers because it gates nothing, not because it fits them. `NO DEMAND`
with a high `ranked_first` is the severest form and sorts first — zero open slots and the whole
region pointing at it. Cross-check every high-ratio role against section 4's no-gate list; when
they are the same roles, the ranking is driven by absence of a filter and the operator's action is
to add the gate, not to recruit less.

`workers_matched` is near-flat across roles because nearly every pool worker is scored against
nearly every role. It is not a demand signal. Do not report it.

### Why each role sits where it does

A high count is not demand and not worker preference. Report the driver beside every row, or the
operator will read the ranking as a popularity signal and recruit against an artefact.

```sql
WITH b AS (
  SELECT id, demandSnapshot FROM `traba-app.pg_export_prod_public.placement_matrix_builds`
  WHERE regionId = '<region>' AND finishedAt IS NOT NULL ORDER BY createdAt DESC LIMIT 1
),
scored AS (
  SELECT p.matrixWorkerId, p.scheduleId, p.rank,
         CAST(ROUND(p.matchScore, 6) AS STRING) score_key,
         JSON_VALUE(p.trace, '$.notes.req') req_note
  FROM `traba-app.pg_export_prod_public.placement_matrix_pairs` p JOIN b ON b.id = p.buildId
),
withties AS (
  SELECT *, COUNT(*) OVER (PARTITION BY matrixWorkerId, score_key) tie_n FROM scored
),
agg AS (
  SELECT scheduleId, COUNTIF(rank = 1) ranked_first,
         COUNTIF(rank = 1 AND tie_n > 1) won_on_tie,
         COUNTIF(rank = 1 AND req_note = 'role has no required attributes') first_nogate,
         COUNTIF(rank = 1 AND REGEXP_CONTAINS(req_note, r'^holds [1-9]')) first_holds
  FROM withties GROUP BY 1
),
dem AS (
  SELECT JSON_VALUE(d, '$.seedRoleId') roleId,
         SUM(SAFE_CAST(JSON_VALUE(d, '$.openSlots') AS INT64)) slots
  FROM b, UNNEST(JSON_QUERY_ARRAY(b.demandSnapshot)) d GROUP BY 1
)
SELECT r.roleName, SPLIT(a.scheduleId, '::')[OFFSET(1)] period,
       COALESCE(dm.slots, 0) slots, a.ranked_first,
       ROUND(100 * a.ranked_first / SUM(a.ranked_first) OVER (), 1) pct_region,
       ROUND(100 * SAFE_DIVIDE(a.won_on_tie, a.ranked_first), 0) pct_tie,
       ROUND(100 * SAFE_DIVIDE(a.first_nogate, a.ranked_first), 0) pct_nogate,
       ROUND(100 * SAFE_DIVIDE(a.first_holds, a.ranked_first), 0) pct_holds
FROM agg a
LEFT JOIN dem dm ON dm.roleId = SPLIT(a.scheduleId, '::')[OFFSET(0)]
LEFT JOIN `traba-app.pg_export_prod_public.roles` r ON r.id = SPLIT(a.scheduleId, '::')[OFFSET(0)]
WHERE a.ranked_first > 0 ORDER BY a.ranked_first DESC
```

Turn the three percentages into one plain-English driver per row:

| Reading | Say | Trust the count? |
|---|---|---|
| `pct_nogate` >= 80 | gates nobody | No. Add a gate. |
| `pct_tie` >= 70 | won on a tie | No. The ranking did not discriminate. |
| `pct_holds` >= 80 and low tie | ranked by people who hold the gate | Yes. |
| `slots` = 0 | no open slots | Supply pointing at it is wasted. |

Ties are the dominant effect and are worth stating once per region as a headline: most workers'
top two listings score identically, and the attribute tie rule that would fix it is not live in any
region. Where a split between two near-identical listings looks like preference, check the tie rate
before recommending anyone recruit against it.

Separately, check the period tag. A listing named second, third or night shift that carries `DAY`
in its schedule id cannot be matched to a night-available worker, and the resulting shift imbalance
is a tagging fault rather than a supply fault.

## Joins that silently return nothing

- `placement_matrix_*.regionId` is a slug and joins `regions.regionId`, never `regions.id`.
- `pairs.scheduleId` is synthetic, `<roleId>::<PERIOD>`. It joins `roles.id` on the prefix and
  matches no row in `schedules.id`.
- `pairs.rank` is per (buildId, matrixWorkerId), capped near 17. `rank <= 100` is a no-op; use
  `rank = 1`.
- `roles` has no region column. Region comes through `roles.locationId` to `locations.regionId`,
  but `locationId` is NULL on some ACTIVE roles (both of Louisville's), and an inner join then drops
  them silently. Reach roles through `placement_matrix_role_configs.regionId` instead whenever the
  question is "which roles does MM run here".
  Role titles routinely name other cities, so a title is never a region signal.
- `onboarding_sessions.roleIds` is a JSON column. Grouping on it errors; wrap in `TO_JSON_STRING`.
- Company name is `companies.employerName`.
- `roles.activeRoleId` is never NULL and ACTIVE rows self-point, but 210 archived rows point to
  another archived role, so one hop does not always reach an active successor.
- Most Traba datasets are in `us-central1`. `region-us.INFORMATION_SCHEMA` returns nothing.
- `bq query` caps output at 100 rows by default and truncates silently. Pass `--max_rows=100000`
  on every export and check the row count against what you expect before using the result.

## Output

Five sections, each two to four sentences, each ending in an action with the role named. Lead
with the verdict: ready, ready with named gaps, or not ready. Put counts in a short table only when
the number changes what the operator does. State the attendance and capacity limits from section 3
whenever an onboarding number appears.
