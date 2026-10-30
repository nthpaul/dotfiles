# Background

pstack uses Cursor tool names. In Codex, read this adapter once per chat and apply these mappings to every pstack skill, playbook, and agent definition. `<pstack>` is the directory containing `skills/`, `docs/`, and `agents/`. Resolve this file's symlinks before deriving that directory.

# Behavior

## Instruction scope

These mappings replace Cursor-specific mechanics. Follow the chat's system, developer, user, and applicable repository instructions when they constrain a pstack workflow. Installing or invoking pstack does not authorize extra external writes, messages, spending, merges, or deployments.

## Tools and delegation

| Cursor instruction | Codex equivalent |
| --- | --- |
| `Task` | `collaboration.spawn_agent`. Use the active tool schema and concurrency limit. |
| `poteto-agent` | Include absolute paths to `<pstack>/agents/poteto-agent.md` and `<pstack>/skills/poteto-mode/SKILL.md` in the worker brief and require it to read them first. The parent owns the playbook. |
| `comment-sicko` | Require the worker to read `<pstack>/agents/comment-sicko.md`; retain the requested read-only scope and applicable repository comment rules. |
| `generalPurpose`, `readonly`, `file_attachments` | Use an ordinary worker with explicit scope, read-only constraints when requested, and absolute file paths in its brief. |
| `run_in_background`, `environment`, `cloud_base_branch` | Omit unsupported fields. Workers run asynchronously. For code isolation, create a separate local worktree and put its path and base commit in the brief. A local worker is not a remote cloud agent. |
| Resume, steer, wait, stop | Use the matching native collaboration tools under the active chat's delegation rules. |
| Open a todolist | Use a native plan tool if available; otherwise maintain a compact checklist in the chat. |
| `AskQuestion` | Use an available native user-input tool only where its schema permits; otherwise ask in chat. |
| `/name` or another pstack skill | Read `<pstack>/skills/<name>/SKILL.md` and its relevant references. |
| `Read`, `Grep`, `Glob`, shell | Use native file tools or `exec_command` with `rg` and `rg --files`. |

Use inherited parent model and reasoning settings by default. Omit Cursor's Claude/Grok slugs, speed suffixes, and unsupported spawn fields. Apply explicit user model choices only when the active collaboration tool supports them. Preserve a panel's requested number of independent reviewers within concurrency limits; describe it as same-model review when the models are inherited.

## Configuration and setup

Read `~/.codex/pstack-models.md` when it exists. Its per-role choices replace the Cursor model rule; the absence of a file or role means `inherit-parent`.

When the user invokes `setup-pstack`, use its role list with these changes. Discover models and reasoning levels from the current collaboration schema. Default every role to `inherit-parent`; for list roles, preserve the upstream entry count with repeated `inherit-parent` entries. Express budget choices with native reasoning levels instead of rewriting Cursor model slugs. Ask for preferences only as part of that requested setup. Write the confirmed roles and budget to `~/.codex/pstack-models.md`. Read that file explicitly on subsequent pstack runs; Codex does not load Cursor `.mdc` rules. Keep setup scoped to this file and any additional verification skill the user requests.

## Other workflows

| Cursor dependency | Codex equivalent |
| --- | --- |
| Built-in `create-skill` | Read the installed `skill-creator` skill and applicable `grade-agent-context` guidance. Use `~/.codex/skills` for personal skills. |
| `cursor-team-kit` `deslop` | Read an installed cleanup skill when available and appropriate, or perform the requested cleanup directly. |
| `control-ui`, `control-cli` | Prefer the project's verification harness; otherwise use available native browser/app controls or shell execution for the actual surface. |
| PR tools and Bugbot | Use `gh` for PR operations and ordinary GitHub review threads. Follow repository CI rules and watch every PR check. A missing Bugbot service does not count as a passed review. |
| Cursor Automations, routine wakes, `/loop`, `drive` | For a requested recurring task or wakeup, discover native Codex automation tools and follow their schema. For work within this chat, use the normal execution loop. Report any required Cursor-only capability that has no equivalent. |
| Cursor chat history and transcript paths | Discover native Codex chat tools and restrict reads to chats relevant to the request. Use collaboration for delegates; create a user-owned chat only when the user requests one. |
| Cursor skill and plugin paths | Resolve bundled files under `<pstack>` and personal skills under `~/.codex/skills`. Keep project-specific assets in the repository's existing supported location. |

Use bundled scripts only for their actual supported service. A script that calls Cursor APIs still requires those APIs; translating a tool name does not make it a Codex script. Report an unmet requirement when it prevents the requested outcome.

# Output

Codex discovers this bundle with the `pstack:` namespace. Tell users to invoke `$pstack:poteto-mode <task>` or `$pstack:<skill-name>`. This installation supplies skill workflows, without Cursor's Custom Mode selector or Option+Enter activation. Apply the selected workflow while working on its task; a new chat must select it again.

Report the native substitute or an unavailable capability when it materially changes the result. Distinguish independent same-model checks from a multi-model panel, and report verification that actually ran.
