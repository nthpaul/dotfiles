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
	},

	config = function()
		vim.diagnostic.config({
			virtual_text = { prefix = "●" },
			signs = true,
			underline = true,
			update_in_insert = false,
			severity_sort = true,
			float = { border = "rounded", source = "if_many" },
		})

		local cmp = require("cmp")

		cmp.setup({
			snippet = {
				expand = function(args)
					if vim.snippet then
						vim.snippet.expand(args.body)
					end
				end,
			},
			experimental = {
				ghost_text = false,
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

		local capabilities = require("cmp_nvim_lsp").default_capabilities()

		require("mason").setup()
		require("mason-lspconfig").setup({
			ensure_installed = {
				"lua_ls",
				"html",
				"cssls",
				"tailwindcss",
				"ts_ls",
				"eslint",
				"elixirls",
				"rust_analyzer",
				"pyright",
				"clangd",
			},
			automatic_installation = true,
		})

		require("mason-tool-installer").setup({
			ensure_installed = {
				"prettier",
				"stylua",
				"isort",
				"black",
				"pylint",
				"clang-format",
			},
		})

		local ts_inlay_hints = {
			includeInlayParameterNameHints = "all",
			includeInlayEnumMemberValueHints = true,
		}

		require("mason-lspconfig").setup_handlers({
			function(server_name)
				local util = require("lspconfig.util")
				local server_config = {
					capabilities = capabilities,
				}

				if server_name == "lua_ls" then
					server_config.root_dir = function(fname)
						return util.root_pattern(".git", ".luarc.json", ".luacheckrc")(fname)
							or util.path.dirname(fname)
					end
					server_config.settings = {
						Lua = {
							runtime = {
								version = "LuaJIT",
							},
							diagnostics = {
								globals = { "vim" },
							},
							workspace = {
								checkThirdParty = false,
								library = vim.api.nvim_get_runtime_file("", true),
							},
							telemetry = {
								enable = false,
							},
							hint = { enable = true },
							completion = { callSnippet = "Replace" },
						},
					}
				end

				if server_name == "elixirls" then
					server_config.filetypes = { "elixir", "eelixir", "heex", "surface" }
					server_config.root_dir = util.root_pattern("mix.exs", ".git")
					server_config.settings = {
						elixirLS = {
							dialyzerEnabled = true,
							fetchDeps = true,
							enableTestLenses = true,
							workingDirectory = { mode = "multi_root" },
							format = false,
						},
					}
				end

				if server_name == "ts_ls" then
					server_config.filetypes = { "javascript", "javascriptreact", "typescript", "typescriptreact" }
					server_config.root_dir = util.root_pattern("tsconfig.json", "package.json", ".git")
					server_config.init_options = {
						hostInfo = "neovim",
						maxTsServerMemory = 8192,
					}
					server_config.settings = {
						typescript = {
							inlayHints = ts_inlay_hints,
							preferences = { importModuleSpecifierPreference = "non-relative" },
						},
						javascript = {
							inlayHints = ts_inlay_hints,
							preferences = { importModuleSpecifierPreference = "non-relative" },
						},
					}
				end

				if server_name == "eslint" then
					server_config.filetypes = { "javascript", "javascriptreact", "typescript", "typescriptreact" }
					server_config.root_dir = util.root_pattern(
						"eslint.config.js",
						"eslint.config.mjs",
						"eslint.config.cjs",
						".eslintrc",
						".eslintrc.js",
						".eslintrc.cjs",
						".eslintrc.json",
						".eslintrc.yml",
						".eslintrc.yaml",
						"package.json"
					)
				end

				if server_name == "rust_analyzer" then
					server_config.settings = {
						["rust-analyzer"] = {
							checkOnSave = { command = "clippy" },
							cargo = { allFeatures = true },
							inlayHints = {
								enable = true,
								parameterHints = { enable = true },
								typeHints = { enable = true },
							},
						},
					}
				end

				if server_name == "pyright" then
					server_config.settings = {
						python = {
							analysis = {
								typeCheckingMode = "basic",
								autoSearchPaths = true,
								useLibraryCodeForTypes = true,
							},
						},
					}
				end

				if server_name == "clangd" then
					server_config.filetypes = { "c", "cpp", "objc", "objcpp" }
					server_config.cmd = {
						"clangd",
						"--background-index",
						"--clang-tidy",
						"--header-insertion=iwyu",
					}
					server_config.root_dir = util.root_pattern(
						"compile_commands.json",
						"compile_flags.txt",
						".clangd",
						"CMakeLists.txt",
						"Makefile",
						".git"
					)
					server_config.init_options = {
						clangdFileStatus = true,
					}
				end

				require("lspconfig")[server_name].setup(server_config)
			end,
		})

		vim.api.nvim_create_autocmd("LspAttach", {
			group = vim.api.nvim_create_augroup("keymaps_on_lsp_attach", {}),
			callback = function(event)
				local client = vim.lsp.get_client_by_id(event.data.client_id)
				local opts = { buffer = event.buf, silent = true }

				opts.desc = "Show LSP references"
				vim.keymap.set("n", "gr", "<CMD>Telescope lsp_references<CR>", opts)

				opts.desc = "Go to definition"
				vim.keymap.set("n", "gd", "<CMD>Telescope lsp_definitions<CR>", opts)

				opts.desc = "Go to declaration"
				vim.keymap.set("n", "gD", vim.lsp.buf.declaration, opts)

				opts.desc = "Go to implementations"
				vim.keymap.set("n", "gi", "<CMD>Telescope lsp_implementations<CR>", opts)

				opts.desc = "Go to type definition"
				vim.keymap.set("n", "gt", "<CMD>Telescope lsp_type_definitions<CR>", opts)

				opts.desc = "Rename symbol"
				vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, opts)
				opts.desc = "Rename all instances of the referenced object in the current buffer"
				vim.keymap.set("n", "<leader>prn", vim.lsp.buf.rename, opts)

				opts.desc = "Show code actions available at current cursor"
				vim.keymap.set("n", "<leader>ca", function()
					vim.lsp.buf.code_action()
				end, opts)

				opts.desc = "Go to next diagnostic"
				vim.keymap.set("n", "[d", function()
					vim.diagnostic.goto_next()
				end, opts)

				opts.desc = "Go to prev diagnostic"
				vim.keymap.set("n", "]d", function()
					vim.diagnostic.goto_prev()
				end, opts)

				opts.desc = "Show diagnostic float"
				vim.keymap.set("n", "<leader>e", vim.diagnostic.open_float, opts)

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
				vim.keymap.set("n", "gs", vim.lsp.buf.signature_help, opts)
				vim.keymap.set("i", "<C-h>", function()
					vim.lsp.buf.signature_help()
				end, opts)

				if not client then
					return
				end

				if vim.lsp.inlay_hint and client.supports_method("textDocument/inlayHint") then
					vim.lsp.inlay_hint.enable(true, { bufnr = event.buf })
				end

				if client.supports_method("textDocument/documentHighlight") then
					local highlight_group = vim.api.nvim_create_augroup("lsp_document_highlight_" .. event.buf, {
						clear = false,
					})
					vim.api.nvim_create_autocmd({ "CursorHold", "CursorHoldI" }, {
						buffer = event.buf,
						group = highlight_group,
						callback = vim.lsp.buf.document_highlight,
					})
					vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, {
						buffer = event.buf,
						group = highlight_group,
						callback = vim.lsp.buf.clear_references,
					})
				end
			end,
		})
	end,
}
