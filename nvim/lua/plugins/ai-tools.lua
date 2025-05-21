return {
  {
    "augmentcode/augment.vim",
    config = function()
      vim.keymap.set("n", "<leader>;", ":Augment chat-toggle<CR>")
      vim.keymap.set("n", "<leader>:", ":Augment chat<CR>")
      vim.keymap.set("n", "<leader>'", ":Augment chat-new<CR>")
    end
  }
}
