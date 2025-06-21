return {
	{
		"f-person/auto-dark-mode.nvim",
		config = function()
			local theme_persistence = require("config.theme-persistence")
			theme_persistence.setup()
			theme_persistence.setup_auto_dark_mode()
			require("auto-dark-mode").init()
		end,
	},
	{
		"folke/tokyonight.nvim",
		lazy = false,
		priority = 1000,
		opts = {},
		config = function()
			require("tokyonight").setup({
				-- transparent = true,
				styles = {
					-- sidebars = "transparent",
					-- floats = "transparent",
				},
			})
		end,
	},
	{
		"EdenEast/nightfox.nvim",
		priority = 1000,
		config = function()
			require("nightfox").setup({
				options = {
					-- transparent = true
				},
			})
		end,
	},
	{
		"jesseleite/nvim-noirbuddy",
		dependencies = {
			{ "tjdevries/colorbuddy.nvim" },
		},
		priority = 1000,
		config = function()
			require("noirbuddy").setup({
				preset = "slate",
			})
		end,
	},
	{
		"ellisonleao/gruvbox.nvim",
		priority = 1000,
		config = function()
			require("gruvbox").setup({
				transparent_mode = true,
			})
		end,
	},
}
