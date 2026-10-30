return {
	{
		"MeanderingProgrammer/render-markdown.nvim",
		ft = "markdown",
		cmd = "MarkdownReadingMode",
		keys = {
			{ "<leader>vmt", "<cmd>MarkdownReadingMode<cr>", desc = "Markdown: toggle reading mode" },
		},
		dependencies = { "nvim-treesitter/nvim-treesitter", "nvim-tree/nvim-web-devicons" },
		opts = {
			code = { disable = { "mermaid" } },
			change_events = { "CursorMovedI", "TextChangedI" },
		},
		config = function(_, opts)
			local markdown = require("render-markdown")
			markdown.setup(opts)

			local reading = false
			local reading_opts = vim.tbl_deep_extend("force", {}, opts, {
				render_modes = true,
				anti_conceal = { enabled = false },
				win_options = { concealcursor = { rendered = "nvic" } },
			})

			vim.api.nvim_create_user_command("MarkdownReadingMode", function()
				reading = not reading
				markdown.setup(reading and reading_opts or opts)
				markdown.enable()

				-- Snacks uses this window option to decide whether to reveal diagram source.
				for _, win in ipairs(vim.api.nvim_list_wins()) do
					local buf = vim.api.nvim_win_get_buf(win)
					if vim.bo[buf].filetype == "markdown" then
						vim.wo[win].concealcursor = reading and "nvic" or ""
						vim.api.nvim_win_call(win, function()
							vim.api.nvim_exec_autocmds("CursorMoved", { buffer = buf })
						end)
					end
				end
				vim.notify("Markdown reading mode " .. (reading and "on" or "off"))
			end, { desc = "Toggle persistent Markdown and Mermaid rendering" })
		end,
	},
	{
		"folke/snacks.nvim",
		opts = function(_, opts)
			-- Snacks invokes mmdc directly; scope the Pele adapter to Neovim.
			local bin = vim.fn.stdpath("config") .. "/tools/mermaid/bin"
			vim.env.PATH = bin .. ":" .. vim.env.PATH
			return vim.tbl_deep_extend("force", opts, {
				image = {
					enabled = true,
					-- Keep previously rendered Mermaid.js images out of Pele's cache.
					cache = vim.fn.stdpath("cache") .. "/snacks/image/pele",
					convert = { notify = true },
					doc = {
						inline = true,
						conceal = function(_, kind)
							return kind == "chart" or kind == "math"
						end,
					},
				},
			})
		end,
	},
}
