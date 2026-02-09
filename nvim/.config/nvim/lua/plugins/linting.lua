return {
	"mfussenegger/nvim-lint",
	event = { "BufReadPre", "BufNewFile", "InsertLeave" },
	config = function()
		local lint = require("lint")

		lint.linters_by_ft = {
			javascript = { "eslint_d" },
			typescript = { "eslint_d" },
			javascriptreact = { "eslint_d" },
			typescriptreact = { "eslint_d" },
			svelte = { "eslint_d" },
			python = { "pylint" },
			elixir = { "trivy" },
		}

		local lint_augroup = vim.api.nvim_create_augroup("lint", { clear = true })

		local function try_lint_without_eslint()
			local ft = vim.bo.filetype
			local linters = lint.linters_by_ft[ft]

			if not linters then
				return
			end

			local filtered = {}
			for _, linter in ipairs(linters) do
				if linter ~= "eslint_d" and linter ~= "eslint" then
					table.insert(filtered, linter)
				end
			end

			if #filtered > 0 then
				lint.try_lint(filtered)
			end
		end

		vim.api.nvim_create_autocmd({ "BufEnter", "InsertLeave" }, {
			group = lint_augroup,
			callback = function()
				try_lint_without_eslint()
			end,
		})

		vim.api.nvim_create_autocmd("BufWritePost", {
			group = lint_augroup,
			callback = function()
				lint.try_lint()
			end,
		})

		vim.keymap.set({ "n", "v" }, "<leader>ml", function()
			lint.try_lint()
		end, { desc = "Trigger linting for current file" })
	end,
}
