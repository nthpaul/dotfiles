return {
  "rmagatti/auto-session",
  config = function()
    local autosession = require("auto-session")
    autosession.setup({
      auto_restore_enabled = false,
      auto_save_enabled = true,
      auto_session_suppress_dirs = { "~/", "~/Downloads", "~/Documents", "~/Desktop" }
    })

    vim.keymap.set("n", "<leader>sr", "<cmd>SessionRestore<CR>", { desc = "Restore session for cwd" })
    vim.keymap.set("n", "<leader>ss", "<cmd>SessionSave<CR>", { desc = "Save session for cwd" })
  end
}
