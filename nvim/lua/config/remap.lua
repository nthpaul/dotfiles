local opts = { noremap = true, silent = true }

vim.g.mapleader = " "
vim.g.maplocaleader = " "
vim.keymap.set("n", "<leader>pv", vim.cmd.Ex, { desc = "go to netrw of current directory" })

-- center with zz when navigating vertically
vim.keymap.set("n", "<C-d>", "<C-d>zz", { desc = "center with zz when navigating vertically" })
vim.keymap.set("n", "<C-u>", "<C-u>zz", { desc = "center with zz when navigating vertically" })

vim.keymap.set("n", "n", "nzzzv", { desc = "center with zz when navigating vertically" })
vim.keymap.set("n", "N", "Nzzzv", { desc = "center with zz when navigating vertically" })

-- better up + down
vim.keymap.set('n', 'j', 'gj', { desc = 'Up', noremap = true })
vim.keymap.set('n', 'k', 'gk', { desc = 'Down', noremap = true })

-- move lines up and down in visual line mode
vim.keymap.set("v", "J", ":m '>+1<CR>gv=gv", { desc = "move lines down in visual selection" })
vim.keymap.set("v", "K", ":m '>-2<CR>gv=gv", { desc = "move lines up in visual selection" })

-- shift left or right
opts.desc = "Shift right in visual selection"
vim.keymap.set("v", ">", ">gv", opts)
opts.desc = "Shift left in visual selection"
vim.keymap.set("v", "<", "<gv", opts)

-- do not affect clipboard
opts.desc = "paste without saving to register"
vim.keymap.set("v", "p", [["_dp]], opts)
vim.keymap.set({ "n", "v" }, "<leader>d", [["_d]], { desc = "delete chunks without saving to register" })
vim.keymap.set("n", "x", [["_x]], { desc = "delete single char without saving to register" })

-- exit insert mode with ctrl-c
vim.keymap.set("i", "C-c", "<Esc>", { desc = "exit insert mode" })

-- word replacement
vim.keymap.set("n", "<leader>s", [[:%s/\<<C-r><C-w>\>/<C-r><C-w>/gI<Left><Left><Left>]],
  { desc = 'Replace word cursor is on globally' })

-- copy current filepath to clipboard
vim.keymap.set("n", "<leader>fp", [[:let @+ = expand('%:p')<CR>]], { desc = 'Copy current filepath to clipboard' })
