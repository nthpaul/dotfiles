# Debugging (Inductive + Deductive)

A repeatable, end-to-end debugging approach that blends evidence-driven discovery (induction) with hypothesis-driven proof (deduction). Optimized for high-stress situations.

## TL;DR

- Stabilize first; keep changes reversible.
- Reproduce or treat it as a data collection problem.
- Gather evidence fast; keep one shared log.
- If it's a regression, find good vs bad and bisect.
- Form 3-5 hypotheses; falsify them quickly.
- Fix minimally; verify with the original repro.
- Add a guard (test/alert) to prevent recurrence.

## Operating Rules

- Assume the system is doing exactly what it was told to do.
- Prefer reversible actions while investigating.
- Separate symptoms from causes; never fix a guess without proof.
- If you cannot reproduce, treat it as a data collection problem.
- Keep a single evidence log with timestamps and decisions.

## Core Principle: Two Loops

- Inductive loop (discover): collect evidence, spot patterns, narrow suspects.
- Deductive loop (prove): form hypotheses and run targeted experiments to falsify them.

If you cannot falsify a hypothesis, you do not truly know the cause.

## End-to-End Workflow (Front -> Back)

1) Define the symptom precisely
- What is wrong? When? For whom? Since when?
- Capture a baseline (expected behavior + metrics).

2) Reproduce deterministically
- Same input, same environment, same output.
- If flaky: capture rate, conditions, and timing.

2b) If regression, isolate good vs bad
- Identify the last known good state (commit, build, config).
- Identify the first known bad state.
- Use git bisect when code changes are the likely cause.

3) Client-side observation (inductive)
- Network panel + waterfall: slow requests, failed calls, cache status.
- Disable cache, hard reload.
- Performance panel: CPU hot spots, long tasks, layout/paint.
- React DevTools profiler: wasted renders, expensive components.
- Lighthouse: performance hints (TTFB, LCP, CLS).
- Memory snapshots: leaks, detached nodes, heap growth.

4) Backend-side observation (inductive)
- Logs: correlate request IDs, error bursts, timeouts.
- Metrics: latency percentiles, error rates, saturation.
- Tracing: request spans, downstream bottlenecks.
- Flamegraphs / profilers: CPU hotspots, lock contention.
- DB: slow queries, missing indexes, N+1 patterns.

5) Hypothesis matrix (deductive)
- Write 3-5 plausible causes that explain the evidence.
- For each, design a minimal experiment that would disprove it.

6) Run controlled experiments (deductive)
- Change one variable at a time.
- Use feature flags, mocks, or isolates.
- Prefer experiments that can falsify a hypothesis quickly.

7) Fix minimally, then validate
- Apply the smallest fix that resolves the observed failure.
- Re-run the exact reproduction, then regression tests.

8) Post-fix validation
- Compare before/after metrics.
- Add a test or guard to prevent regressions.

## Quick Frontend Checklist

- Network waterfall and status codes
- Disable cache and hard reload
- Service worker unregistered (if present)
- React profiler (renders and commits)
- Performance panel (long tasks)
- Lighthouse (LCP, CLS, TTFB)
- Memory snapshot (leaks, detached nodes)
- CSP/CORS errors in console
- CDN version and cache headers

## Quick Backend Checklist

- Logs with correlation/request IDs
- p50/p95/p99 latency and error rates
- Tracing spans and slow edges
- Flamegraph/profile hotspots
- DB slow queries, locks, connection pool
- Retry storms or cascading failures
- CPU/mem/IO saturation and queue depth

## Stress-Proof Additions (Critical Under Pressure)

- Stop-the-bleed first: feature flag off, rollback, reduce blast radius.
- One-pager incident checklist: repro -> snapshot -> isolate -> fix -> verify -> cleanup.
- Freeze the timeline: note start time, deploy SHA, config changes, traffic spikes.
- Single source of truth: one issue log with hypotheses + experiments + results.
- Timebox loops: 20-30 minutes per hypothesis before switching.
- Change vector scan: deploys, config, data, traffic, dependencies, infra events.
- Reversibility first: prefer mitigations that can be undone quickly.
- Single driver: one person coordinates changes; avoid conflicting fixes.

## Environment Sanity Checks

- Confirm running version: commit/branch/build hash/container tag.
- Confirm config: env vars, feature flags, rate limits, secrets.
- Confirm data: schema/migrations, data shape changes, flags.
- Confirm dependency state: upstream availability, timeouts, rate limits.

## Repro & Isolation Discipline

- Min-case repro (smallest input + smallest surface).
- Disable variables: extensions, cache, service workers, ad blockers.
- Run in clean environment: incognito, fresh profile, no cached SW.

## Regression Isolation (Git Bisect)

Use this when you have a reproducible regression and a known good state.

When to use:
- The bug appeared after a code change.
- You can run a deterministic test or repro script.

How to use:
```
git bisect start
git bisect bad <bad_sha_or_tag>
git bisect good <good_sha_or_tag>
# Run the smallest deterministic test here
git bisect good   # if the test passes
git bisect bad    # if the test fails
# Repeat until git identifies the first bad commit
git bisect reset
```

Notes:
- Keep the working tree clean while bisecting.
- Use the smallest, fastest test possible.
- If the bug is config- or data-driven, bisect configs/flags instead of code.
- You can automate the bisect with a script:
```
git bisect run ./your-test.sh
```

## Observability Hygiene

- Ensure correlation IDs propagate end-to-end.
- Temporarily increase log level with a plan to revert.
- Avoid logging PII; redact or sample.
- Triangulate: confirm signals across logs, metrics, and traces.

## Fix Discipline

- Smallest fix first, especially in production.
- Test the fix in the same reproduction path.
- Remove temporary logs and flags post-fix.
- Add a guard to prevent recurrence (test, alert, or invariant).

## Hypothesis Matrix Template

| Hypothesis | Evidence | Experiment (Falsify) | Result | Next Action |
|-----------|----------|----------------------|--------|-------------|
|           |          |                      |        |             |

## Incident Log Template

- Symptom:
- Start time:
- Detection time:
- Mitigation time:
- Deploy SHA / build tag:
- Scope / impacted users:
- Repro steps:
- Evidence gathered:
- Hypotheses + experiments:
- Fix:
- Tests run:
- Post-fix metrics:
- Follow-ups:

## First Response Runbook (Agnostic)

Use this when under pressure and you need a fast, repeatable path without stack-specific assumptions.

1) Stabilize
- Reduce blast radius (feature flag off, rollback, rate-limit, or disable the hot path).

2) Reproduce
- Capture exact steps, input, environment, and time.
- Confirm it happens twice with the same conditions.

3) Snapshot evidence
- Client: network waterfall, console errors, cache state.
- Server: logs, error rate, latency percentiles, saturation.
- Data: recent migrations or schema changes.

4) Correlate
- Find request or correlation IDs end-to-end.
- Align timestamps with deploys and config changes.

5) Form hypotheses
- Write 3-5 plausible causes from the evidence.
- Pick the fastest falsification experiment first.

6) Execute a minimal experiment
- Change one variable and measure the effect.
- If falsified, move to the next hypothesis.

7) Fix and verify
- Apply the smallest safe fix.
- Re-run the original repro and a minimal regression check.

8) Cleanup
- Remove temporary logs, flags, or debug code.
- Document the cause and prevention step.

## Tool Quickstarts (Beginner)

### Browser / Frontend

- DevTools Network: open DevTools, go to Network, enable "Disable cache" and "Preserve log," reload, click a request, open Timing to see TTFB vs download.
- DevTools Performance: Record, reproduce the issue, Stop, inspect long tasks and layout/paint events.
- DevTools Coverage: Command Palette -> "Coverage," Start, reload, then review unused JS/CSS.
- Rendering/Layers: More Tools -> Rendering, enable paint flashing/layout shift regions; use Layers for compositing issues.
- Lighthouse: run a report, focus on LCP/CLS/TBT/TTFB; compare before/after.
- React DevTools Profiler: Record, interact, Stop; find components with high render time or repeated renders.
- why-did-you-render (dev only): install and enable; mark components to log wasted renders.
  - Example: set `whyDidYouRender = true` on components and watch console.
- Bundle analyzer: run build with analyzer enabled, open the report, inspect large modules.
  - Example (if available):
```
npx source-map-explorer 'dist/*.js'
npx webpack-bundle-analyzer path/to/stats.json
```
- Playwright trace: run tests with tracing enabled, open trace viewer, step through DOM/network/console.
  - Example:
```
npx playwright test --trace on
npx playwright show-trace trace.zip
```
- Cypress open mode: run interactively, inspect time-travel snapshots, screenshots, and videos.
  - Example:
```
npx cypress open
```

### Network / API

- Proxy tools (Charles/Proxyman/Fiddler/mitmproxy): set system proxy, install root cert, reproduce, filter by host/path, inspect or edit requests/responses.
- curl: send a raw request and read headers/status.
```
curl -v -H "Authorization: Bearer TOKEN" https://example.test/api
```
- httpie: friendly syntax for quick checks.
```
http GET https://example.test/api Authorization:"Bearer TOKEN"
```
- tcpdump/Wireshark: capture packets and inspect low-level traffic.
```
sudo tcpdump -i any -nn -s0 -w capture.pcap
```

### Backend Observability

- APM (Datadog/New Relic/Elastic): install agent, set service name/env, view traces to find slow spans and errors.
- OpenTelemetry + Jaeger/Tempo/Zipkin: add SDK, configure exporter, open tracing UI, inspect spans and timing.
- Logs (ELK/Splunk/Loki): emit structured logs with request IDs; query by ID or error signature.
- Metrics (Prometheus + Grafana): expose /metrics, scrape with Prometheus, graph p95/p99 and error rates.

### Profilers

- Node --inspect: start node with --inspect, open chrome://inspect, record CPU profile or heap snapshot.
  - Example:
```
node --inspect ./server.js
```
- Clinic.js / 0x: run app through profiler wrapper, open flamegraph report for hot stacks.
  - Example:
```
npx clinic doctor -- node ./server.js
npx 0x ./server.js
```
- py-spy: attach to a running Python process and record a profile.
```
py-spy top --pid 1234
py-spy record -o profile.svg --pid 1234
```
- cProfile (Python): run with profiler and inspect hot functions.
```
python -m cProfile -o prof.out app.py
```
- JVM JFR / async-profiler: start a recording, run workload, stop and inspect CPU/alloc/locks.
- OS tools: perf for CPU sampling, strace for syscalls, lsof for open files/sockets.
  - Examples:
```
sudo perf record -F 99 -p <PID> -g -- sleep 10
sudo perf report
strace -p <PID> -f -tt -o trace.log
lsof -p <PID>
```

### Database

- Postgres: EXPLAIN ANALYZE for real query costs; pg_stat_statements for top slow queries.
- MySQL: EXPLAIN and slow query log for plan and timing.
  - Examples:
```
EXPLAIN ANALYZE SELECT ...;
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```
```
EXPLAIN SELECT ...;
SHOW VARIABLES LIKE 'slow_query_log';
```

### Cache (Redis)

- MONITOR: stream all commands (heavy; use briefly).
- SLOWLOG: inspect slow commands.
- INFO: check memory, evictions, hit rate.
  - Examples:
```
redis-cli MONITOR
redis-cli SLOWLOG GET 10
redis-cli INFO
```

### Load / Regression

- k6/Locust/Artillery/JMeter: define a scenario, run load, review latency/error rates.
  - Examples:
```
k6 run script.js
locust -f locustfile.py
npx artillery run scenario.yml
```
