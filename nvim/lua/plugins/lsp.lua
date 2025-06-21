-- LSP AND COMPLETIONS
return {
	"neovim/nvim-lspconfig",
	dependencies = {
		{ "williamboman/mason.nvim", version = "1.11.0" },
		{ "williamboman/mason-lspconfig.nvim", version = "1.32.0" },
		"WhoIsSethDaniel/mason-tool-installer.nvim",
		"hrsh7th/nvim-cmp",
		"hrsh7th/cmp-nvim-lsp",
		"hrsh7th/cmp-buffer",
		"hrsh7th/cmp-path",
		"catgoose/nvim-colorizer.lua",
		"roobert/tailwindcss-colorizer-cmp.nvim",
	},

	config = function()
		-- COMPLETIONS SETUP
		local cmp = require("cmp")
		local colorizer = require("colorizer")
		local tailwindcss_colorizer = require("tailwindcss-colorizer-cmp")

		colorizer.setup({
			user_default_options = {
				tailwind = true,
			},
			filetypes = {
				"*",
			},
		})

		-- makes tailwind colors show up in completion menu
		tailwindcss_colorizer.setup({
			color_square_width = 2,
		})
		vim.api.nvim_create_autocmd({ "BufReadPost", "BufNewFile" }, {
			callback = function()
				vim.cmd("ColorizerAttachToBuffer")
			end,
		})

		-- setup completions keybindings
		cmp.setup({
			experimental = {
				ghost_text = false, -- predictive ghost completions
			},
			mapping = {
				["<C-n>"] = cmp.mapping.select_next_item(),
				["<C-p>"] = cmp.mapping.select_prev_item(),
				["<CR>"] = cmp.mapping.confirm({ select = true }),
				["<C-space>"] = cmp.mapping.complete(),
				["<C-e>"] = cmp.mapping.abort(),
			},
			sources = {
				{ name = "nvim_lsp" },
				{ name = "buffer" },
				{ name = "path" },
			},
		})
		-- extend completions with lsp capabilities
		local cmp_lsp = require("cmp_nvim_lsp")
		local capabilities = vim.tbl_deep_extend(
			"force",
			vim.lsp.protocol.make_client_capabilities(),
			cmp_lsp.default_capabilities() -- let's lsp know that nvim is capable of handling completion requests
		)

		-- LSP SETUP
		require("mason").setup()
		require("mason-lspconfig").setup({
			ensure_installed = {
				"lua_ls",
				"html",
				"cssls",
				"tailwindcss",
				"ts_ls",
				"elixirls",
				"rust_analyzer",
				"pyright",
			},
			automatic_installation = true,
		})

		require("mason-tool-installer").setup({
			ensure_installed = {
				"prettier",
				"stylua",
				"isort",
				"pylint",
				"clangd",
				{ "eslint_d", verion = "13.1.2" },
				"trivy",
			},
		})

		require("mason-lspconfig").setup_handlers({
			function(server_name)
				local server_config = {
					capabilities = capabilities,
				}

				if server_name == "lua_ls" then
					server_config.settings = {
						Lua = {
							diagnostics = {
								globals = { "vim" }, -- recognize `vim` as a global
							},
							workspace = {
								library = {
									vim.api.nvim_get_runtime_file("", true),
								}, -- finds files in runtime dirs in runtimepath order
							},
						},
					}
				end

				if server_name == "elixirls" then
					server_config.filetypes = { "elixir", "eelixir", "heex", "surface" }
					server_config.root_dir = require("lspconfig.util").root_pattern("mix.exs", ".git")(vim.fn.getcwd())
					server_config.settings = {
						elixirLS = {
							dialyzerEnabled = true,
							fetchDeps = true,
							enableTestLenses = true,
							workingDirectory = { mode = "multi_root" },
							format = true,
						},
					}
				end

				if server_name == "ts_ls" or server_name == "eslint" then
					server_config.filetypes = { "javascript", "javascriptreact", "typescript", "typescriptreact" }
					server_config.root_dir = vim.fs.dirname(
						vim.fs.find(".git", { path = vim.fn.getcwd(), upward = true })[1]
					) or require("lspconfig.util").root_pattern("tsconfig.json", "package.json", ".git") or vim.fn.getcwd()
				end

				require("lspconfig")[server_name].setup(server_config)
			end,
		})

		-- local buffer mappings for when lsp server attaches
		vim.api.nvim_create_autocmd("LspAttach", {
			group = vim.api.nvim_create_augroup("keymaps_on_lsp_attach", {}),
			callback = function(event)
				-- print("LSP attached to buffer: " .. event.buf) -- to debug lsp
				-- check `:help vim.lsp.*` for docs on any of the below functions
				local opts = { buffer = event.buf, silent = true }

				-- keymaps
				opts.desc = "Show LSP references"
				vim.keymap.set("n", "gr", "<CMD>Telescope lsp_references<CR>", opts)

				opts.desc = "Go to definition"
				vim.keymap.set("n", "gd", "<CMD>Telescope lsp_definitions<CR>", opts)

				opts.desc = "Go to declaration"
				vim.keymap.set("n", "gD", vim.lsp.buf.declaration, opts)

				opts.desc = "Go to implementations"
				vim.keymap.set("n", "gi", "<CMD>Telescope lsp_implementations<CR>", opts)

				-- opts.desc = "Go to type definition"
				-- vim.keymap.set("n", "gt", "<CMD>Telescope lsp_type_definitions<CR>", opts)

				opts.desc = "Rename all instances of the referenced object in the current buffer"
				vim.keymap.set("n", "<leader>prn", vim.lsp.buf.rename, opts)

				opts.desc = "Show code actions available at current cursor"
				vim.keymap.set("n", "<leader>ca", function()
					vim.lsp.buf.code_action()
				end, opts)

				-- PROJECT DIAGNOSTICS
				-- error diagnostics in current buffer
				opts.desc = "Go to next diagnostic"
				vim.keymap.set("n", "[d", function()
					vim.diagnostic.goto_next()
				end, opts)

				opts.desc = "Go to prev diagostic"
				vim.keymap.set("n", "]d", function()
					vim.diagnostic.goto_prev()
				end, opts)

				opts.desc = "Show current buffer diagnostics"
				vim.keymap.set("n", "<leader>fd", "<CMD>Telescope diagnostics bufnr=0<CR>", opts)

				opts.desc = "Show project wide diagnostics"
				vim.keymap.set("n", "<leader>pd", "<CMD>Telescope diagnostics<CR>", opts)

				opts.desc = "Show documentation of what is under cursor"
				vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)

				opts.desc = "Restart LSP"
				vim.keymap.set("n", "<leader>lsp", function()
					print("Restarting LSP...")
					vim.cmd("LspRestart")
				end, opts)

				opts.desc = "Show function signature"
				vim.keymap.set("i", "<C-h>", function()
					vim.lsp.buf.signature_help()
				end, opts)
			end,
		})
	end,
}
