# Fugitive Cheat Sheet

## Diff views

- `:Gvdiffsplit` vertical side-by-side diff
- `:Gdiffsplit` horizontal diff
- `:Gvdiffsplit <ref>` compare current file with a ref (e.g. `HEAD~1`)

## Merge conflicts (3-way)

1) Open conflicted file
2) `:Gvdiffsplit` to open 3-way diff
3) Use diffget to pick a side

- `:diffget //1` base
- `:diffget //2` ours (current)
- `:diffget //3` theirs (incoming)

Save and stage:

- `:w`
- `:Gwrite`

## Custom keybindings (from this dotfiles)

- `<leader>gv` → `:Gvdiffsplit`
- `<leader>gH` → `:Gdiffsplit`
- `<leader>g1` → `:diffget //1`
- `<leader>g2` → `:diffget //2`
- `<leader>g3` → `:diffget //3`
