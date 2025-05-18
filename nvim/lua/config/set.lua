vim.g.netrw_bufsettings = 'noma nomod nu nowrap ro nobl' -- add relative line numbers to netrw

vim.opt.tabstop = 2
vim.opt.softtabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true

vim.opt.autoindent = true
vim.opt.smartindent = true
vim.opt.wrap = false

vim.opt.relativenumber = true

vim.opt.clipboard:append("unnamedplus")

vim.opt.ignorecase = true
vim.opt.smartcase = true

vim.opt.termguicolors = true
vim.opt.scrolloff = 8
vim.opt.signcolumn = "no"

vim.opt.backspace = {"start", "eol", "indent"}

vim.opt.updatetime = 50
