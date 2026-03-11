# Planning

- IMPORTANT: The code in each PR of a stack must be atomic and must pass CI.

# Putting up pull requests for review

- Unless explicitly asked otherwise, use the `gt` CLI for interacting with PRs and create stacks. Stacks are easier to review because each PR is smaller and logically focused.
- Each PR of a stack is atomic and must past CI.
- Instead of `git commit`, use `gt create`. This will create a commit and a branch with the current changes.
- Instead of `git push`. use `gt submit --no-interactive`. This will submit the current branch and all downstack branches to Graphite.

## Command Permissions (Graphite / gt)

The assistant may run these without asking:

- `gt init`
- `gt create`
- `gt modify`
- `gt restack`
- `gt sync`
- `gt submit --no-interactive`
- `gt submit --stack --no-interactive`
- `gt checkout`
- `gt log`
- `gt up`
- `gt down`

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
