---
name: mobile-feature-e2e
description: >-
  Emulate feature-branch mobile clients end to end on simulators/emulators,
  drive UI flows, record video evidence, and assert backend state. Use when
  testing a mobile feature branch against a local or patched backend, when
  the user asks for simulator/emulator QA, Maestro flows, Mobile MCP
  automation, screen recordings of opt-in/decline or other UI paths, or
  attaching mobile video evidence to a PR description.
---

# Mobile feature-branch e2e

Run a patched mobile client (and its matching backend when needed) on a
simulator or emulator. Drive the product flows autonomously. Capture video
and stills. Assert API/DB outcomes. Attach evidence to the PR description —
never as a product release.

## Tooling stack

Use these together. Prefer the cheapest tool that can fail when the flow is wrong.

| Layer | Tool | Role |
|-------|------|------|
| Device | iOS Simulator / Android emulator | Host the app |
| Device control | `xcrun simctl` / `adb` | Boot, install, launch, deep-link, terminate |
| Packager | Metro / Expo dev client / native run | Serve the feature-branch JS |
| UI automation | **Maestro** | Deterministic flows (preferred for multi-step UI) |
| Device MCP | **Mobile MCP** (`user-mobile-mcp`) | Screenshots, recording, element dump, ad-hoc taps |
| Backend | Local API + local data store | Feature-branch server under test |
| Secrets | Project secret runner or `.env` | Boot client/server with local config |
| Evidence host | `gh image` → `user-attachments` | Inline videos/images on a PR description |

Full Mobile MCP tool list: [mobile-mcp-tools.md](mobile-mcp-tools.md).

## Preconditions

1. **Feature branches checked out** for every repo that must change together (client, server, shared packages).
2. **Native binary matches JS.** If the packager reports a React Native / Expo SDK mismatch, rebuild the native app (`expo run:ios` / `expo run:android` or the project’s equivalent) before debugging UI.
3. **Backend reachable from the device/simulator.** Prefer localhost / LAN IP the simulator can hit. Confirm health before login.
4. **Seeded account + domain state** that makes the feature visible (flags, prefs, fixtures). Do not rely on prod data.
5. **Maestro + JDK** installed if using Maestro (`JAVA_HOME` set). Mobile MCP authenticated if required (`mcp_auth`).

## End-to-end procedure

### 1. Bring up the stack

1. Start local infra (DB, cache, emulators) if the project needs it.
2. Start the **feature-branch** API. Confirm health.
3. Start the **feature-branch** packager (Metro / Expo). Confirm `/status` or equivalent.
4. Boot a named simulator/emulator. Prefer one device UDID and stick to it for the session.
5. Launch the app; open the packager URL in the dev client if needed (deep link or “recently opened”).

### 2. Seed the scenario

- Create or reuse a QA user with known credentials (store outside the product repo if secrets).
- Write the domain rows / prefs / flags that put the UI into the starting state (e.g. “blocked”, “eligible”, “empty”).
- Fix missing related rows that cause noisy error toasts (metrics, profiles) when cheap — they distract recordings.

### 3. Reach a stable Home (or target screen)

1. Dismiss first-run noise: ATT prompts, Expo/dev menus, LogBox, ToS, push-permission “Not now”.
2. Prefer Maestro `optional: true` taps for flaky overlays; Expo “Continue” often starts unwanted flows — close with **X** when the goal is just dismissing the menu.
3. Wait on a durable signal (banner text, greeting, `testID`) before recording.

### 4. Record distinct workloads

One recording per path. Do not mash paths into one long video.

For each path:

1. `mobile_start_screen_recording` (Mobile MCP) with an explicit `.mp4` output path under a durable scratch/docs folder — not `/tmp` alone if evidence must survive.
2. Run the Maestro flow (or MCP taps if the flow is tiny).
3. `mobile_stop_screen_recording`.
4. Assert UI (banner gone / still present) **and** backend/DB state.
5. Reseed between paths when a path mutates shared state.

Maestro flows should use **testIDs** when available; fall back to text regexes. Keep flows next to the evidence folder so they are reproducible.

### 5. Prefer Maestro over MCP for scripted UI

| Use Maestro when… | Use Mobile MCP when… |
|--------------------|----------------------|
| Multi-step happy/sad paths | One-off tap / dismiss |
| Assertions mid-flow | Screenshot / element dump |
| Re-runs after reseed | Screen recording start/stop |
| Flaky overlays with `optional: true` | Reading what’s on screen now |

If MCP clicks miss (LogBox, animated toasts), Maestro `tapOn: "Dismiss"` or a text match is usually more reliable.

### 6. Temporary backend stubs

If an external vendor API blocks the success path in local/dev (404, missing product feature):

- Stub **only** behind an explicit env flag (e.g. `QA_STUB_*=1`).
- Record the success path with the stub on.
- **Revert the stub in source before finishing.** Do not leave it on the PR branch.
- Note in the PR that the stub was local-only and why the real vendor call fails today.

Fail-closed behavior without the stub is still worth proving (error toast + state unchanged).

### 7. Evidence and PR attachment

1. Keep videos + stills + Maestro YAMLs in a durable folder (project scratch or personal work-docs style home — never as the only copy in `/tmp`).
2. Attach to the **mobile app PR description** as inline media:
   - Upload with `gh image <file> --repo <owner/app-repo>` (uses browser session → `user-attachments` URLs).
   - Put bare video URLs (or markdown) under Screenshots in `gh pr edit`.
3. **Do not** create GitHub Releases / tags to host QA videos.
4. **Do not** run OTA / store publish / production deploy as part of this skill unless the user explicitly asks.
5. Backend-only PRs: link to the app PR evidence; do not dump mobile videos on the wrong PR.

### 8. Teardown

- Stop recordings; terminate the app if needed.
- Revert local stubs and confirm `git diff` is clean of them.
- Leave packager/API running only if the user still needs them.

## Parallel path template

When the feature has an explicit decline vs confirm (or similar):

1. **Decline / cancel path** — starting state → open CTA → dismiss → UI unchanged → DB unchanged.
2. **Confirm / success path** — reseed → same entry → confirm → UI updated → DB updated.

Record each as its own `.mp4`.

## Failure triage (short)

| Symptom | Check |
|---------|--------|
| Packager unreachable from sim | LAN IP vs localhost; firewall; Metro actually listening |
| RN version mismatch | Rebuild native for the branch’s RN/Expo SDK |
| Banner/feature never appears | Seed prefs/flags; API health; auth claims; feature gate |
| Tap does nothing | Dump elements; prefer Maestro + testID; dismiss LogBox first |
| Success API fails locally | Vendor account capability; messaging SIDs; consider flagged stub then revert |
| Video won’t embed on PR | Use `gh image` user-attachments, not release assets |

## Done when

- [ ] Each requested path has its own recording
- [ ] UI assertions and DB/API assertions agree
- [ ] Stubs reverted; no OTA/release side effects
- [ ] Evidence attached to the correct PR description (or saved for the user to attach)
