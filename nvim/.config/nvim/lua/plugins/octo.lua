return {
	"pwntester/octo.nvim",
	cmd = "Octo",
	dependencies = {
		"nvim-lua/plenary.nvim",
		"nvim-telescope/telescope.nvim",
		"nvim-tree/nvim-web-devicons",
	},
	opts = {
		picker = "telescope",
		enable_builtin = true,
	},
	keys = {
		{
			"<leader>op",
			"<CMD>Octo pr list<CR>",
			desc = "List GitHub PRs",
		},
		{
			"<leader>oi",
			"<CMD>Octo issue list<CR>",
			desc = "List GitHub issues",
		},
		{
			"<leader>or",
			"<CMD>Octo review start<CR>",
			desc = "Start PR review",
		},
		{
			"<leader>on",
			"<CMD>Octo notification list<CR>",
			desc = "List GitHub notifications",
		},
		{
			"<leader>os",
			function()
				require("octo.utils").create_base_search_command({ include_current_repo = true })
			end,
			desc = "Search GitHub",
		},
	},
}
