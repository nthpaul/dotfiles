return {
  "f-person/auto-dark-mode.nvim",
  opts = {
    update_interval = 1000, -- Check for OS theme changes every 1000ms
    set_dark_mode = function()
      vim.opt.background = "dark"
      vim.cmd("colorscheme carbonfox")
    end,
    set_light_mode = function()
      vim.opt.background = "light"
      vim.cmd("colorscheme dayfox")
    end,
  },
}
