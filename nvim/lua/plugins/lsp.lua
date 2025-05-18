return {
  "neovim/nvim-lspconfig",
  dependencies = {
    { "williamboman/mason.nvim", version = "1.11.0" },
    { "williamboman/mason-lspconfig.nvim", version = "1.32.0" },
    "hrsh7th/nvim-cmp",
    "hrsh7th/cmp-nvim-lsp",
    "hrsh7th/cmp-buffer",
    "hrsh7th/cmp-path"
  },

  config = function()
    -- setup completions keybindings
    local cmp = require("cmp")
    cmp.setup({
      mapping = {
        ['<C-n>'] = cmp.mapping.select_next_item(),
        ['<C-p>'] = cmp.mapping.select_prev_item(),
        ['<C-y>'] = cmp.mapping.confirm({ select = true }),
        ['<C-space>'] = cmp.mapping.complete(),
        ['<C-e>'] = cmp.mapping.abort()
      },
      sources = {
        { name = 'nvim_lsp' },
        { name = 'buffer' },
        { name = 'path' }
      }
    })
    -- extend lsp capabilities
    local cmp_lsp = require("cmp_nvim_lsp")
    local capabilities = vim.tbl_deep_extend(
      "force",
      vim.lsp.protocol.make_client_capabilities(),

      cmp_lsp.default_capabilities()
    )

    require("mason").setup()
    require("mason-lspconfig").setup({
      ensure_installed = {
        "lua_ls",
        "ts_ls",
        "elixirls",
        "rust_analyzer",
        "pyright"
      },
      automatic_installation = true
    })

    require("mason-lspconfig").setup_handlers({
      function(server_name)
        local server_config = {
          capabilities = capabilities,
        }

        if server_name == "lua_ls"
          then server_config.settings = {
            Lua = {
              diagnostics = {
                globals = { 'vim' } -- recognize `vim` as a global
              },
              workspace = {
                library = vim.api.nvim_get_runtime_file("", true) -- finds files in runtime dirs in runtimepath order
              }
            }
          }
        end

        if server_name == "elixirls" then
          server_config.filetypes = { "elixir", "eelixir", "heex", "surface" }
          server_config.root_dir = require("lspconfig.util").root_pattern("mix.exs", ".git") or vim.fn.getcwd()
          server_config.settings = {
            elixirls = {
              -- dialyzerEnabled = true,
              -- fetchDeps = true,
              workingDirectory = { mode = "location" },
              format = true
            }
          }
          server_config.root_dir = vim.fs.dirname(vim.fs.find('.git', { path = vim.fn.getcwd(), upward = true })[1]) or require("lspconfig.util").root_pattern("tsconfig.json", "package.json", ".git") or vim.fn.getcwd()
        end

        if server_name == "ts_ls" then
          server_config.filetypes = { "javascript", "javascriptreact", "typescript", "typescriptreact" }
          server_config.root_dir = vim.fs.dirname(vim.fs.find('.git', { path = vim.fn.getcwd(), upward = true })[1]) or require("lspconfig.util").root_pattern("tsconfig.json", "package.json", ".git") or vim.fn.getcwd()
        end

        require("lspconfig")[server_name].setup(server_config)
      end
    })

    -- local buffer mappings for when lsp server attaches
    vim.api.nvim_create_autocmd("LspAttach", {
      group = vim.api.nvim_create_augroup("keymaps_on_lsp_attach", {}),
      callback = function(event)
        print("LSP attached to buffer: " .. event.buf) -- to debug lsp
        -- check `:help vim.lsp.*` for docs on any of the below functions
        local opts = { buffer = event.buf, silent = true }

        -- keymaps
        opts.desc = "Show LSP references"
        vim.keymap.set("n", "gr", "<cmd>Telescope lsp_references<CR>", opts)

        opts.desc = "Go to definition"
        vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)

        opts.desc = "Go to declaration"
        vim.keymap.set("n", "gD", vim.lsp.buf.declaration, opts)

        opts.desc = "Rename all instances of the referenced object in the current buffer"
        vim.keymap.set("n", "<leader>prn", vim.lsp.buf.rename, opts)

        opts.desc = "Show code actions available at current cursor"
        vim.keymap.set("n", "<leader>ca", function() vim.lsp.buf.code_action() end, opts)
      end
    })
  end
}

