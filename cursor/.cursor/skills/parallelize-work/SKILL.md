---
name: parallelize-work
description: Orchestrate multiple independent implementation tasks in parallel by creating one `wt` worktree and one detached worker session per task. Use when an implementation document, task breakdown, or Linear project link explicitly identifies which Linear issues can be worked on concurrently.
---

# Parallelize Work

Use this skill to fan out explicitly independent Linear implementation tasks into separate worktrees and detached worker sessions.

Treat this as an orchestration skill, not an implementation skill. Each child worker should own exactly one Linear issue and should use the `linear-ticket-work` workflow to do the actual work.

## Required inputs

Provide:

- one required source of truth that explicitly lists the tasks and identifies which ones are parallelizable
- one optional TRD or spec for additional guidance or clarification

The required source can be:

- a local implementation document path
- pasted plan text
- a Linear project link, but only when the project or linked doc clearly marks the parallelizable tasks

Do not infer concurrency from vague project organization, issue titles, or guesswork. If the source does not clearly identify the independent tasks, stop and ask for a clearer task breakdown.

## Workflow

1. Read the required source and optional TRD or spec.
2. Extract only the tasks explicitly marked safe to execute in parallel.
3. For each task, resolve:
   - Linear issue id
   - repo or project name accepted by `wt`
   - worktree name
   - short task summary
   - optional extra guidance specific to that task
4. Stop and escalate if any task is missing a repo mapping, missing a Linear issue id, or appears non-atomic.
5. Write a JSON execution plan that matches the launcher schema below.
6. Run `scripts/launch_parallel_ticket_work.py <plan.json>`.
7. Report the created worktrees, tmux session names, log paths, and any skipped tasks.

## Launcher plan schema

```json
{
  "source": "/absolute/path/to/implementation-doc.md or https://linear.app/...",
  "spec": "/absolute/path/to/spec.md",
  "tasks": [
    {
      "issue_id": "ENG-123",
      "project": "traba",
      "worktree": "eng-123",
      "task_summary": "Implement candidate-side loading state for shift actions.",
      "extra_prompt": "Limit changes to mobile app surfaces covered by the ticket."
    }
  ]
}
```

Rules:

- `source` is required
- `spec` is optional
- each task must include `issue_id` and `project`
- `worktree` is optional; if omitted, default to the lowercase Linear issue id
- `project` must match the repo name used with `wt`

## Execution behavior

The launcher script will:

1. Use `source ~/.zshrc && wt <project> <worktree> pwd` to create or resolve the worktree and discover its path.
2. Create a detached tmux session named `wt/<project>/<worktree>`.
3. Start a full-access interactive child worker in that worktree. In this migrated version, the bundled script still uses the `codex` CLI by default for those detached child workers.
4. Start it inside a detached tmux session so the user can attach later and continue prompting it directly.
5. Feed the child worker an initial prompt that tells it to follow the `linear-ticket-work` workflow for the assigned Linear issue.
6. Save prompt files and pane logs under `~/.cursor/tmp/parallelize-work/<timestamp>/`.

The child prompt should:

- name the exact Linear issue
- point to the orchestration source doc or project link
- include the optional TRD or spec when provided
- include the per-task summary and any extra task guidance
- instruct the child to keep scope limited to that one issue

## Linear project links

If the input is a Linear project link:

- inspect the project and linked issues with the `linear` CLI
- continue only when the project or linked documentation explicitly identifies the parallelizable tasks
- stop if the project link alone does not provide enough structure to build a reliable per-task plan

## Safety rules

- One task maps to one Linear issue, one worktree, and one child worker run.
- Do not put multiple issues in the same worktree.
- Do not launch a child run for tasks that are blocked on unclear dependencies.
- Prefer short, stable worktree names. Default to the lowercase issue id unless the source already defines a better name.
- Do not assume the launched child runs finished successfully. Check tmux sessions and logs.
- Prefer interactive child sessions over one-shot runs so the user can attach and steer any child worker directly.
