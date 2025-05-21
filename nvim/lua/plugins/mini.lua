return {
  { "echasnovski/mini.nvim", version = false },
  {
    "echasnovski/mini.files",
    config = function()
      local MiniFiles = require("mini.files")
      MiniFiles.setup({
        mappings = {
          go_in_plus = "<CR>",
          go_out_plus = "-"
        }
      })

      vim.keymap.set("n", "<leader>ee", "<cmd>lua MiniFiles.open()<CR>", { desc = "Toggle mini file explorer" })
      vim.keymap.set("n", "<leader>ec", function()
        MiniFiles.open(vim.api.nvim_buf_get_name(0), false)
        MiniFiles.reveal_cwd()
      end, { desc = "Open mini file explorer at current file" })

      -- TODO: get relative numbers working in mini files buffer
      local augroup = vim.api.nvim_create_augroup("MiniFilesConfig", { clear = true })
      vim.api.nvim_create_autocmd("FileType", {
        pattern = "mini.files",
        callback = function()
          vim.opt_local.relativenumber = true
          vim.opt_local.number = true
        end,
        group = augroup
      })
    end,
  },
  {
    "echasnovski/mini.surround",
    config = function()
      require("mini.surround").setup({
        mappings = {
          add = "<leader>xa",
          delete = "<leader>xd",
          find = "<leader>xf",
          find_left = "<leader>xF",
          highlight = "<leader>xh",
          replace = "<leader>xr",
        }
      })
    end
  },
  {
    "echasnovski/mini.trailspace",
    event = { "BufReadPre", "BufNewFile" },
    config = function()
      local trailspace = require("mini.trailspace")
      trailspace.setup({
        only_in_normal_buffers = true
      })

      vim.keymap.set("n", "<leader>tt", function() trailspace.trim() end, { desc = "Trim trailing whitespace" })

      -- Unhighlight on cursor move
      vim.api.nvim_create_autocmd("CursorMoved", {
        pattern = "*",
        callback = function()
          require("mini.trailspace").unhighlight()
        end
      })
    end
  },
  {
    "echasnovski/mini.splitjoin",
    config = function()
      local splitjoin = require("mini.splitjoin")

      splitjoin.setup({
        mappings = { toggle = "" } -- disable default mapping
      })

      vim.keymap.set("n", "<leader>sjs", function() splitjoin.split() end, { desc = "Split line" })
      vim.keymap.set("n", "<leader>sjj", function() splitjoin.join() end, { desc = "Join the line" })
    end
  }
}
