---
name: watch-parallel-stacks-cursor
description: Coordinate multi-ticket implementation with one long-running watcher agent and one worker agent per active lane. Use when a project has dependency chains, some tasks can run in parallel, blocked tasks should wait, dependent tickets should share a worktree as a PR stack, and the coordinator must keep monitoring until every task is complete.
---

# Watch Parallel Stacks (Cursor Agent)

Use this skill when the user wants one agent to stay alive as the coordinator while other agents do the implementation work.

This is an orchestration skill, not an implementation skill.

## Operating model

- One detached tmux watcher session owns coordination for the whole project.
- One detached tmux worker session exists per active lane.
- A lane is one repo worktree plus an ordered stack of one or more Linear issues.
- Independent lanes run in parallel.
- Dependent tickets that should land as stacked PRs stay in the same lane and the same worktree.
- The watcher does not stop until every task in the plan is complete.

## Required inputs

Provide:

- one required source of truth that lists the tasks for the project
- one optional TRD or spec for deeper implementation guidance
- enough repo context to map each task to the repo name used by `wt`

Good inputs:

- an implementation checklist or breakdown doc
- a Linear project plus linked tickets and docs
- pasted task breakdown text with explicit issue ids

Stop and ask for clarification when:

- the source does not identify the actual tickets
- dependency order is unclear
- it is unclear which tasks can run in parallel
- a proposed lane would mix unrelated work that should land as separate PRs

## Lane planning rules

Before launching anything:

1. Read the source doc, optional spec, and relevant Linear issues.
2. Build a dependency graph for the tasks in scope.
3. Partition tasks into lanes.

Use these rules:

- Put independent tasks in different lanes so they can run in parallel.
- Put directly dependent tasks in the same lane when they should become a logical PR stack.
- Reuse the same worktree for every task in the same lane.
- Do not start a blocked task early just because its lane already exists.
- Do not put multiple unrelated issues in the same lane just to reduce session count.

## Plan schema

Write a JSON execution plan with this shape:

```json
{
  "source": "/absolute/path/to/implementation-doc.md or https://linear.app/...",
  "spec": "/absolute/path/to/spec.md",
  "watcher_workspace": "/absolute/path/to/repo-or-workspace",
  "lanes": [
    {
      "id": "resolution-runtime",
      "project": "traba-server-node",
      "worktree": "resolution-runtime",
      "tasks": [
        {
          "issue_id": "ENG-18178",
          "task_summary": "Wire create_support_case into the runtime.",
          "depends_on": [],
          "extra_prompt": "Keep scope limited to runtime wiring."
        },
        {
          "issue_id": "ENG-18190",
          "task_summary": "Persist support-case metadata after runtime wiring lands.",
          "depends_on": ["ENG-18178"],
          "extra_prompt": "Build on the existing lane branch as the next PR in the stack."
        }
      ]
    },
    {
      "id": "config-contract",
      "project": "traba-server-node",
      "worktree": "config-contract",
      "tasks": [
        {
          "issue_id": "ENG-18177",
          "task_summary": "Implement Statsig config contracts and defaults.",
          "depends_on": [],
          "extra_prompt": "Keep the PR atomic to config parsing and tests."
        }
      ]
    }
  ]
}
```

Rules:

- `source` is required
- `spec` is optional
- `watcher_workspace` is optional and defaults to the current working directory
- each lane must include `id`, `project`, `worktree`, and `tasks`
- each task must include `issue_id`
- `depends_on` is optional but should be included whenever the dependency is known
- dependencies may point to tasks in the same lane or another lane

## Launch the watcher

After writing the plan, run:

```bash
python ~/.cursor/skills/watch-parallel-stacks-cursor/scripts/launch_watcher_parallel_stacks.py <plan.json>
```

That launcher will:

1. Resolve every lane worktree path with `wt`
2. Create a durable watcher tmux session
3. Write watcher prompt, metadata, logs, and state files under `~/.cursor/tmp/watch-parallel-stacks-cursor/<timestamp>/`
4. Restart the watcher agent automatically if it exits before the project is finished

Report back:

- watcher session name
- run root
- lane ids
- lane session names
- resolved worktree paths

## Watcher responsibilities

The watcher must:

1. Read the generated plan, metadata, and state files first.
2. Keep `state.json` current after every notable transition.
3. Launch only the lanes whose current task is unblocked.
4. Use `python ~/.cursor/skills/watch-parallel-stacks-cursor/scripts/launch_lane_worker.py ...` to start a lane session when needed.
5. Keep one worker session per lane for the whole lane lifetime.
6. When a lane finishes its current issue, assess the next issue in that same lane:
   - if dependencies are satisfied, prompt the same worker session to continue with the next issue in the stack
   - if dependencies are not satisfied, leave the lane idle and keep monitoring
7. Continue monitoring even after some lanes finish, until all lanes finish.
8. Touch the generated `watcher.done` file only when every task in the plan is complete.

## Worker prompt rules

Each lane worker prompt should:

- identify the current Linear issue
- mention the lane id and that the lane reuses one worktree for a PR stack
- point to the source doc and optional spec
- state whether this issue is the first PR in the lane or stacked on a previous issue
- instruct the worker to stop after finishing the current issue and wait for the next lane instruction
- instruct the worker to preserve stackability and use the repo's standard Graphite flow

## Monitoring loop

The watcher should poll regularly and steer lightly:

- inspect each lane tmux session output
- inspect branch and worktree status
- verify whether validation is still running or the worker is idle
- nudge only when the worker is stuck, drifting scope, or needs dependency clarification
- keep a concise state note for each intervention

Prefer calm supervision over constant interruption.

## Auto-compress rule

When any watcher or worker session shows context usage above 50 percent:

- compress at the next natural pause, not in the middle of a long-running command
- send `/compress` to that tmux session and submit it with `Enter`
- record the compression in `state.json`
- prefer compressing before handing a lane its next issue in the stack

## Durability rules

- The watcher session must be treated as durable infrastructure, not a best-effort helper.
- If the watcher exits before completion, the launcher wrapper should restart it and the watcher should recover from `state.json`.
- Never declare the project complete while any task is still pending, active, blocked on an in-plan dependency, or awaiting PR creation.
- If a worker exits unexpectedly, the watcher should relaunch or resume that lane instead of abandoning it.

## Safety rules

- One lane maps to one worktree and one worker session.
- Multiple tasks may share a lane only when they are an intentional stack.
- One task still maps to one Linear issue and one atomic PR.
- Do not start blocked work just to keep every lane busy.
- Do not silently skip failed validation or scope conflicts.
- If the dependency graph or repo mapping becomes unclear, stop and surface the ambiguity.
