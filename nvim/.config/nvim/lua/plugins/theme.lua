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
		"datsfilipe/vesper.nvim",
		config = function()
			require("vesper").setup({
				transparent = true, -- Boolean: Sets the background to transparent
				italics = {
					comments = false, -- Boolean: Italicizes comments
					keywords = false, -- Boolean: Italicizes keywords
					functions = false, -- Boolean: Italicizes functions
					strings = false, -- Boolean: Italicizes strings
					variables = false, -- Boolean: Italicizes variables
				},
				overrides = {}, -- A dictionary of group names, can be a function returning a dictionary or a table.
				palette_overrides = {},
			})
		end,
	},
	{
		"folke/tokyonight.nvim",
		lazy = false,
		priority = 1000,
		opts = {},
		config = function()
			require("tokyonight").setup({
				transparent = true,
				styles = {
					sidebars = "transparent",
					floats = "transparent",
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
					transparent = true,
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
	{
		"zenbones-theme/zenbones.nvim",
		-- Optionally install Lush. Allows for more configuration or extending the colorscheme
		-- If you don't want to install lush, make sure to set g:zenbones_compat = 1
		-- In Vim, compat mode is turned on as Lush only works in Neovim.
		dependencies = "rktjmp/lush.nvim",
		lazy = false,
		priority = 1000,
		-- you can set set configuration options here
		config = function()
			vim.g.zenwritten_transparent_background = "true"
			vim.g.rosebones_transparent_background = "true"
		end,
	},
	{
		"rose-pine/neovim",
		name = "rose-pine",
		config = function()
			require("rose-pine").setup({
				styles = {
					bold = true,
					italic = true,
					transparency = true,
				},
			})
		end,
	},
	{
		"projekt0n/github-nvim-theme",
		name = "github-theme",
		lazy = false,
		priority = 1000,
		config = function()
			require("github-theme").setup({
				-- nothing here for now
			})
		end,
	},
	{
		"AlessandroYorba/Alduin",
		lazy = false,
		priority = 1000,
		config = function()
			vim.g.alduin_Shout_Fire_Breath = 1
		end,
	},
	{
		"oskarnurm/koda.nvim",
		lazy = false,
		priority = 1000,
	},
	{
		"andreypopp/vim-colors-plain",
		lazy = false,
		priority = 1000,
	},
	{
		"catppuccin/nvim",
		name = "catppuccin",
		lazy = false,
		priority = 1000,
		config = function()
			require("catppuccin").setup({
				transparent_background = true,
			})
		end,
	},
	{
		"rebelot/kanagawa.nvim",
		lazy = false,
		priority = 1000,
		config = function()
			require("kanagawa").setup({
				transparent = true,
			})
		end,
	},
	{
		"shaunsingh/nord.nvim",
		lazy = false,
		priority = 1000,
	},
	{
		"navarasu/onedark.nvim",
		lazy = false,
		priority = 1000,
		config = function()
			require("onedark").setup({
				style = "dark",
				transparent = true,
			})
		end,
	},
	{
		"sainnhe/everforest",
		lazy = false,
		priority = 1000,
		config = function()
			vim.g.everforest_transparent_background = 1
		end,
	},
	{
		"sainnhe/sonokai",
		lazy = false,
		priority = 1000,
		config = function()
			vim.g.sonokai_transparent_background = 1
		end,
	},
	{
		"sainnhe/edge",
		lazy = false,
		priority = 1000,
		config = function()
			vim.g.edge_transparent_background = 1
		end,
	},
	{
		"marko-cerovac/material.nvim",
		lazy = false,
		priority = 1000,
	},
	{
		"Mofiqul/dracula.nvim",
		lazy = false,
		priority = 1000,
		config = function()
			require("dracula").setup({
				transparent_bg = true,
			})
		end,
	},
	{
		"nyoom-engineering/oxocarbon.nvim",
		lazy = false,
		priority = 1000,
	},
	{
		"RRethy/base16-nvim",
		lazy = false,
		priority = 1000,
	},
}
