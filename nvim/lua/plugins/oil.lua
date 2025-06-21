return {
	"stevearc/oil.nvim",
	dependencies = { "nvim-tree/nvim-web-devicons" }, -- optional but recommended
	config = function()
		require("oil").setup({
			-- Use a floating window layout
			float = {
				-- Set max window padding
				padding = 2,
				max_width = 80,
				max_height = 30,
				border = "rounded",
				win_options = {
					winblend = 10,
				},
			},
			-- Keep using netrw for basic operations
			-- default_file_explorer = false,
		})

		vim.keymap.set("n", "-", "<CMD>Oil --float<CR>", { desc = "Open parent directory in float" })

		vim.api.nvim_create_autocmd("FileType", {
			pattern = "oil",
			callback = function()
				vim.opt_local.cursorline = true
			end,
		})
	end,
}
