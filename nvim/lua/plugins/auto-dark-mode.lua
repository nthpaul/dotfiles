return {
  "f-person/auto-dark-mode.nvim",
  opts = {
    update_interval = 1000, -- Check for OS theme changes every 1000ms
    set_dark_mode = function()
      vim.api.nvim_set_option("background", "dark")
      vim.opt.background = "dark"
      vim.cmd("colorscheme terafox")
    end,
    set_light_mode = function()
      vim.api.nvim_set_option("background", "light")
      vim.opt.background = "light"
      vim.cmd("colorscheme dayfox")
    end,
  },
}
