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
