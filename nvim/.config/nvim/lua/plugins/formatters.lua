return {
	"stevearc/conform.nvim",
	event = { "BufReadPre", "BufNewFile" },
	config = function()
		local conform = require("conform")
		conform.setup({
			formatters_by_ft = {
				lua = { "stylua" },
				python = { "isort", "black" },
				javascript = { "prettier" },
				typescript = { "prettier" },
				typescriptreact = { "prettier" },
				javascriptreact = { "prettier" },
				tailwind = { "prettier" },
				html = { "prettier" },
				css = { "prettier" },
				scss = { "prettier" },
				graphql = { "prettier" },
				markdown = { "prettier" },
				elixir = { "mix" },
				eelixir = { "mix" },
				heex = { "mix" },
				yaml = { "prettier" },
				json = { "prettier" },
			},
			formatters = {
				prettier = {
					prepend_args = { "--config-precedence", "prefer-file" },
				},
			},
			format_on_save = {
				timeout_ms = 5000,
				lsp_format = "fallback",
			},
		})
		vim.keymap.set({ "n", "v" }, "<leader>mp", function()
			conform.format({
				lsp_fallback = true,
				async = false,
				timeout_ms = 5000,
			})
		end, { desc = " Prettier format whole file or range (in visual mode)" })
	end,
}
