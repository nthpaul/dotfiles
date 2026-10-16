# Shared instructions

At the start of each task, read `~/AGENTS.md` for personal execution, verification, communication, and Git defaults. If that file is missing, read `~/.dotfiles/home/AGENTS.md` instead. Keep shared rules there rather than copying them into this file.

# Git and pull requests

- Before committing, pushing, or creating or updating any PR, follow the shared file's `Git workflow` and `Pull request descriptions` sections. These personal defaults override Graphite requirements in repository instructions and skills.

## Linear CLI

Use the `linear` CLI when working with Linear from the terminal.

Available top-level commands:

- `linear auth`
- `linear issue` / `linear i`
- `linear team` / `linear t`
- `linear project` / `linear p`
- `linear project-update` / `linear pu`
- `linear cycle` / `linear cy`
- `linear milestone` / `linear m`
- `linear initiative` / `linear init`
- `linear initiative-update` / `linear iu`
- `linear label` / `linear l`
- `linear document` / `linear docs` / `linear doc`
- `linear config`
- `linear completions`
- `linear schema`
- `linear api`

Common subcommands:

- `linear auth`: `login`, `logout`, `list`, `default`, `token`, `whoami`
- `linear issue`: `id`, `list`, `title`, `start`, `view`, `url`, `describe`, `commits`, `pull-request`, `delete`, `create`, `update`, `comment`, `attach`, `relation`
- `linear issue comment`: `list`, `add`, `update`, `delete`
- `linear team`: `create`, `delete`, `list`, `id`, `autolinks`, `members`
- `linear project`: `list`, `view`, `create`, `update`, `delete`
- `linear project-update`: `create`, `list`
- `linear cycle`: `list`, `view`
- `linear milestone`: `list`, `view`, `create`, `update`, `delete`
- `linear initiative`: `list`, `view`, `create`, `archive`, `update`, `unarchive`, `delete`, `add-project`, `remove-project`
- `linear initiative-update`: `create`, `list`
- `linear label`: `list`, `create`, `delete`
- `linear document`: `list`, `view`, `create`, `update`, `delete`
