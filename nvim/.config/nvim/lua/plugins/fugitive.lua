return {
	"tpopp/vim-fugitive",
	config = function()
		vim.keymap.set("n", "<leader>gs", "<cmd>Git<cr>", { desc = "Open git status" })
		vim.keymap.set("n", "<leader>gv", "<cmd>Gvdiffsplit<cr>", { desc = "Fugitive vertical diff" })
		vim.keymap.set("n", "<leader>gH", "<cmd>Gdiffsplit<cr>", { desc = "Fugitive horizontal diff" })
		vim.keymap.set("n", "<leader>g1", "<cmd>diffget //1<cr>", { desc = "Fugitive diffget base" })
		vim.keymap.set("n", "<leader>g2", "<cmd>diffget //2<cr>", { desc = "Fugitive diffget ours" })
		vim.keymap.set("n", "<leader>g3", "<cmd>diffget //3<cr>", { desc = "Fugitive diffget theirs" })
	end,
	event = "VeryLazy",
}
