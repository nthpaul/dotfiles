return {
  {
    "nvim-treesitter/nvim-treesitter",
    event = { "BufReadPre", "BufNewFile" },
    build = ":TSUpdate",
    config = function()
      require 'nvim-treesitter.configs'.setup {
        ensure_installed = {
          "c",
          "typescript",
          "javascript",
          "elixir",
          "python",
          "lua",
          "vim",
          "vimdoc",
          "query",
          "markdown",
          "markdown_inline"
        },
        sync_install = false,
        auto_install = true,
        highlight = {
          enable = true,
          indent = { enable = true },
          additional_vim_regex_highlighting = false,
        },
        incremental_selection = {
          enable = true,
          keymaps = {
            init_selection = "<leader>is",
            node_incremental = "<leader>ii",
            scope_incremental = "<leader>is",
            node_decremental = "<leader>id",
          },
        },
      }
    end
  }
}
