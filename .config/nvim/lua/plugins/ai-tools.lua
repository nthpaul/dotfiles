return {
	{
		"NickvanDyke/opencode.nvim",
		dependencies = {
			-- Recommended for `ask()` and `select()`.
			-- Required for `snacks` provider.
			---@module 'snacks' <- Loads `snacks.nvim` types for configuration intellisense.
			{ "folke/snacks.nvim", opts = { input = {}, picker = {}, terminal = {} } },
		},
		config = function()
			---@type opencode.Opts
			vim.g.opencode_opts = {
				-- Your configuration, if any — see `lua/opencode/config.lua`, or "goto definition".
			}

			-- Required for `opts.events.reload`.
			vim.o.autoread = true

			-- Recommended/example keymaps.
			vim.keymap.set({ "n", "x" }, "<C-a>", function()
				require("opencode").ask("@this: ", { submit = true })
			end, { desc = "Ask opencode" })
			vim.keymap.set({ "n", "x" }, "<C-x>", function()
				require("opencode").select()
			end, { desc = "Execute opencode action…" })
			vim.keymap.set({ "n", "t" }, "<C-.>", function()
				require("opencode").toggle()
			end, { desc = "Toggle opencode" })

			vim.keymap.set({ "n", "x" }, "go", function()
				return require("opencode").operator("@this ")
			end, { expr = true, desc = "Add range to opencode" })
			vim.keymap.set("n", "goo", function()
				return require("opencode").operator("@this ") .. "_"
			end, { expr = true, desc = "Add line to opencode" })

			vim.keymap.set("n", "<S-C-u>", function()
				require("opencode").command("session.half.page.up")
			end, { desc = "opencode half page up" })
			vim.keymap.set("n", "<S-C-d>", function()
				require("opencode").command("session.half.page.down")
			end, { desc = "opencode half page down" })

			-- You may want these if you stick with the opinionated "<C-a>" and "<C-x>" above — otherwise consider "<leader>o".
			vim.keymap.set("n", "+", "<C-a>", { desc = "Increment", noremap = true })
			vim.keymap.set("n", "-", "<C-x>", { desc = "Decrement", noremap = true })
		end,
	},

	{
		"augmentcode/augment.vim",
		config = function()
			vim.keymap.set("n", "<leader>;", ":Augment chat-toggle<CR>")
			vim.keymap.set("n", "<leader>:", ":Augment chat<CR>")
			vim.keymap.set("n", "<leader>'", ":Augment chat-new<CR>")
		end,
	},
	-- {
	-- 	"xTacobaco/cursor-agent.nvim",
	-- 	config = function()
	-- 		vim.keymap.set("n", "<leader>aa", ":CursorAgent<CR>", { desc = "Cursor Agent: Toggle terminal" })
	-- 		vim.keymap.set("v", "<leader>as", ":CursorAgentSelection<CR>", { desc = "Cursor Agent: Send selection" })
	-- 		vim.keymap.set("n", "<leader>ab", ":CursorAgentBuffer<CR>", { desc = "Cursor Agent: Send buffer" })
	-- 	end,
	-- },
	-- {
	-- 	"github/copilot.vim",
	-- 	config = function()
	-- 		vim.keymap.set("n", "<leader>aa", ":CursorAgent<CR>", { desc = "Cursor Agent: Toggle terminal" })
	-- 		vim.keymap.set("v", "<leader>as", ":CursorAgentSelection<CR>", { desc = "Cursor Agent: Send selection" })
	-- 		vim.keymap.set("n", "<leader>ab", ":CursorAgentBuffer<CR>", { desc = "Cursor Agent: Send buffer" })
	-- 	end,
	-- },
	{
		"github/copilot.vim",
		config = function()
			vim.api.nvim_set_keymap(
				"i",
				"<M-CR>",
				'copilot#Accept("<CR>")',
				{ expr = true, noremap = true, silent = true }
			)
			vim.g.copilot_no_tab_map = true
			-- vim.cmd(":Copilot disable")
			-- keymaps to disable and enable copilot
			vim.api.nvim_set_keymap("n", "<leader>cpd", ":Copilot disable<CR>", { noremap = true, silent = true })
			vim.api.nvim_set_keymap("n", "<leader>cpe", ":Copilot enable<CR>", { noremap = true, silent = true })
		end,
	},
	-- 	{
	-- 		"yetone/avante.nvim",
	-- 		event = "VeryLazy",
	-- 		version = false, -- Never set this value to "*"! Never!
	-- 		opts = {
	-- 			-- add any opts here
	-- 			-- for example
	-- 			providers = {
	-- 				openai = {
	-- 					endpoint = "https://api.openai.com/v1",
	-- 					model = "gpt-4.1", -- your desired model (or use gpt-4o, etc.)
	-- 					timeout = 30000, -- Timeout in milliseconds, increase this for reasoning models
	-- 					extra_request_body = {
	-- 						temperature = 0,
	-- 						max_completion_tokens = 8192, -- Increase this to include reasoning tokens (for reasoning models)
	-- 						--reasoning_effort = "medium", -- low|medium|high, only used for reasoning models
	-- 					},
	-- 				},
	-- 			},
	-- 		},
	-- 		-- if you want to build from source then do `make BUILD_FROM_SOURCE=true`
	-- 		build = "make",
	-- 		-- build = "powershell -ExecutionPolicy Bypass -File Build.ps1 -BuildFromSource false" -- for windows
	-- 		dependencies = {
	-- 			"nvim-treesitter/nvim-treesitter",
	-- 			"stevearc/dressing.nvim",
	-- 			"nvim-lua/plenary.nvim",
	-- 			"MunifTanjim/nui.nvim",
	-- 			--- The below dependencies are optional,
	-- 			"echasnovski/mini.pick", -- for file_selector provider mini.pick
	-- 			"nvim-telescope/telescope.nvim", -- for file_selector provider telescope
	-- 			"hrsh7th/nvim-cmp", -- autocompletion for avante commands and mentions
	-- 			"ibhagwan/fzf-lua", -- for file_selector provider fzf
	-- 			"nvim-tree/nvim-web-devicons", -- or echasnovski/mini.icons
	-- 			"zbirenbaum/copilot.lua", -- for providers='copilot'
	-- 			{
	-- 				-- support for image pasting
	-- 				"HakonHarnes/img-clip.nvim",
	-- 				event = "VeryLazy",
	-- 				opts = {
	-- 					-- recommended settings
	-- 					default = {
	-- 						embed_image_as_base64 = false,
	-- 						prompt_for_file_name = false,
	-- 						drag_and_drop = {
	-- 							insert_mode = true,
	-- 						},
	-- 						-- required for Windows users
	-- 						use_absolute_path = true,
	-- 					},
	-- 				},
	-- 			},
	-- 			{
	-- 				-- Make sure to set this up properly if you have lazy=true
	-- 				"MeanderingProgrammer/render-markdown.nvim",
	-- 				opts = {
	-- 					file_types = { "markdown", "Avante" },
	-- 				},
	-- 				ft = { "markdown", "Avante" },
	-- 			},
	-- 		},
	-- 	},
}
