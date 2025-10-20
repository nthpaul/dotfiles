return {
	"tpopp/vim-fugitive",
	config = function()
		vim.keymap.set("n", "<leader>gs", "<cmd>Git<cr>", { desc = "Open git status" })
	end,
	event = "VeryLazy",
}
