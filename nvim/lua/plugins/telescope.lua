return {
	"nvim-telescope/telescope.nvim",
	dependencies = {
		"nvim-lua/plenary.nvim",
		{ "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
		"nvim-tree/nvim-web-devicons",
		"andrew-george/telescope-themes",
	},
	config = function()
		local telescope = require("telescope")
		local actions = require("telescope.actions")
		local builtin = require("telescope.builtin")

		telescope.load_extension("fzf")
		telescope.load_extension("themes")

		telescope.setup({
			defaults = {
				path_display = { "smart" },
				mappings = {
					i = {
						["<C-k>"] = actions.move_selection_previous,
						["<C-j>"] = actions.move_selection_next,
					},
				},
				extensions = {
					themes = {
						enable_preview = true,
						previewer = true,
						persist = {
							enabled = true,
							path = vim.fn.stdpath("config") .. "/lua/plugins/theme.lua",
						},
					},
				},
			},
		})

		-- Buffer specific
		vim.keymap.set("n", "<leader>fcw", function()
			builtin.grep_string({ search = vim.fn.expand("<cword>") })
		end, { desc = "Telescope grep current word" })

		vim.keymap.set("n", "<leader>ff", builtin.find_files, { desc = "Telescope find files" })
		vim.keymap.set("n", "<leader>fr", builtin.oldfiles, { desc = "Telescope recent files" })
		vim.keymap.set("n", "<leader>fb", builtin.buffers, { desc = "Telescope buffers" })
		vim.keymap.set("n", "<leader>ft", "<CMD>Telescope treesitter<CR>", { desc = "Telescope treesitter" })
		vim.keymap.set("n", "<leader>flg", "<CMD>Telescope live_grep<CR>", { desc = "Telescope live grep" })

		-- Workspace specific
		vim.keymap.set("n", "<leader>fgs", ":Telescope git_status<CR>", { desc = "Telescope git status" })
		vim.keymap.set("n", "<leader>fs", function()
			builtin.grep_string({ search = vim.fn.input("Grep > ") })
		end, { desc = "Telescope grep string" })

		-- Config specific
		vim.keymap.set("n", "<leader>km", ":Telescope keymaps<CR>", { desc = "Telescope keymaps" })
		vim.keymap.set("n", "<leader>fth", ":Telescope themes<CR>", { desc = "Telescope colorscheme" })
	end,
}
