-- One table of colorscheme plugins. Edit here to add a theme.
-- `schemes` is the :colorscheme names that plugin provides.

return {
	{
		repo = "datsfilipe/vesper.nvim",
		schemes = { "vesper" },
		config = function()
			require("vesper").setup({
				transparent = true,
				italics = {
					comments = false,
					keywords = false,
					functions = false,
					strings = false,
					variables = false,
				},
				overrides = {},
				palette_overrides = {},
			})
		end,
	},
	{
		repo = "folke/tokyonight.nvim",
		schemes = {
			"tokyonight",
			"tokyonight-night",
			"tokyonight-storm",
			"tokyonight-day",
			"tokyonight-moon",
		},
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
		repo = "EdenEast/nightfox.nvim",
		schemes = { "nightfox", "dayfox", "dawnfox", "duskfox", "nordfox", "terafox", "carbonfox" },
		config = function()
			require("nightfox").setup({
				options = {
					transparent = true,
				},
			})
		end,
	},
	{
		repo = "jesseleite/nvim-noirbuddy",
		schemes = { "noirbuddy" },
		dependencies = {
			{ "tjdevries/colorbuddy.nvim" },
		},
		config = function()
			require("noirbuddy").setup({
				preset = "slate",
			})
		end,
	},
	{
		repo = "ellisonleao/gruvbox.nvim",
		schemes = { "gruvbox" },
		config = function()
			require("gruvbox").setup({
				transparent_mode = true,
			})
		end,
	},
	{
		repo = "zenbones-theme/zenbones.nvim",
		schemes = {
			"zenbones",
			"zenwritten",
			"neobones",
			"vimbones",
			"rosebones",
			"forestbones",
			"nordbones",
			"tokyobones",
			"seoulbones",
			"duckbones",
			"zenburned",
			"kanagawabones",
			"randombones",
		},
		-- Optionally install Lush. Allows for more configuration or extending the colorscheme
		-- If you don't want to install lush, make sure to set g:zenbones_compat = 1
		-- In Vim, compat mode is turned on as Lush only works in Neovim.
		dependencies = "rktjmp/lush.nvim",
		config = function()
			vim.g.zenwritten_transparent_background = "true"
			vim.g.rosebones_transparent_background = "true"
		end,
	},
	{
		repo = "rose-pine/neovim",
		name = "rose-pine",
		schemes = { "rose-pine", "rose-pine-main", "rose-pine-moon", "rose-pine-dawn" },
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
		repo = "projekt0n/github-nvim-theme",
		name = "github-theme",
		schemes = {
			"github_dark",
			"github_dark_default",
			"github_dark_dimmed",
			"github_dark_high_contrast",
			"github_dark_colorblind",
			"github_dark_tritanopia",
			"github_light",
			"github_light_default",
			"github_light_high_contrast",
			"github_light_colorblind",
			"github_light_tritanopia",
		},
		config = function()
			require("github-theme").setup({
				-- nothing here for now
			})
		end,
	},
	{
		repo = "AlessandroYorba/Alduin",
		schemes = { "alduin" },
		config = function()
			vim.g.alduin_Shout_Fire_Breath = 1
		end,
	},
	{
		repo = "oskarnurm/koda.nvim",
		schemes = { "koda", "koda-dark", "koda-light", "koda-glade", "koda-moss" },
	},
	{
		repo = "andreypopp/vim-colors-plain",
		schemes = { "plain", "plain-cterm" },
	},
	{
		repo = "catppuccin/nvim",
		name = "catppuccin",
		schemes = {
			"catppuccin",
			"catppuccin-latte",
			"catppuccin-frappe",
			"catppuccin-macchiato",
			"catppuccin-mocha",
		},
		config = function()
			require("catppuccin").setup({
				transparent_background = true,
			})
		end,
	},
	{
		repo = "rebelot/kanagawa.nvim",
		schemes = { "kanagawa", "kanagawa-wave", "kanagawa-dragon", "kanagawa-lotus" },
		config = function()
			require("kanagawa").setup({
				transparent = true,
			})
		end,
	},
	{
		repo = "shaunsingh/nord.nvim",
		schemes = { "nord" },
	},
	{
		repo = "navarasu/onedark.nvim",
		schemes = { "onedark" },
		config = function()
			require("onedark").setup({
				style = "dark",
				transparent = true,
			})
		end,
	},
	{
		repo = "sainnhe/everforest",
		schemes = { "everforest" },
		config = function()
			vim.g.everforest_transparent_background = 1
		end,
	},
	{
		repo = "sainnhe/sonokai",
		schemes = { "sonokai" },
		config = function()
			vim.g.sonokai_transparent_background = 1
		end,
	},
	{
		repo = "sainnhe/edge",
		schemes = { "edge" },
		config = function()
			vim.g.edge_transparent_background = 1
		end,
	},
	{
		repo = "marko-cerovac/material.nvim",
		schemes = {
			"material",
			"material-darker",
			"material-deep-ocean",
			"material-lighter",
			"material-oceanic",
			"material-palenight",
		},
	},
	{
		repo = "Mofiqul/dracula.nvim",
		schemes = { "dracula", "dracula-soft" },
		config = function()
			require("dracula").setup({
				transparent_bg = true,
			})
		end,
	},
	{
		repo = "nyoom-engineering/oxocarbon.nvim",
		schemes = { "oxocarbon" },
	},
	{
		repo = "RRethy/base16-nvim",
		-- Plugin ships many base16-* schemes; these two are the defaults we care about listing.
		schemes = { "base16-default-dark", "base16-default-light" },
	},
}
