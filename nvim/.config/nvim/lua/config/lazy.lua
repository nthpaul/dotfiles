local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
	local lazyrepo = "https://github.com/folke/lazy.nvim.git"
	local out = vim.fn.system({ "git", "clone", "--filter=blob:none", "--branch=stable", lazyrepo, lazypath })
	if vim.v.shell_error ~= 0 then
		vim.api.nvim_echo({
			{ "Failed to clone lazy.nvim:\n", "ErrorMsg" },
			{ out, "WarningMsg" },
			{ "\nPress any key to exit..." },
		}, true, {})
		vim.fn.getchar()
		os.exit(1)
	end
end

vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
	spec = {
		{ import = "plugins" },
	},
	defaults = {
		lazy = false,
		version = false, -- always use the latest git commit
	},
	checker = {
		enabled = true, -- check for plugin updates periodically
		notify = false, -- notify on update
	},
	change_detection = { notify = false },
})

-- AUTOCOMMANDS

-- 1. watch for external writes that update the current buffer
vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
	pattern = "*",
	command = "silent! checktime",
})
