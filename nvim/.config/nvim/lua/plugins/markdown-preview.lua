return {
	{
		"selimacerbas/markdown-preview.nvim",
		ft = { "markdown", "mermaid" },
		cmd = {
			"MarkdownPreview",
			"MarkdownPreviewRefresh",
			"MarkdownPreviewStop",
		},
		dependencies = { "selimacerbas/live-server.nvim" },
		config = function()
			require("markdown_preview").setup({
				instance_mode = "takeover",
				port = 0,
				open_browser = true,
				default_theme = "dark",
				debounce_ms = 300,
				scroll_sync = true,
				auto_refresh = true,
			})

			vim.keymap.set("n", "<leader>vms", "<cmd>MarkdownPreview<cr>", { desc = "Markdown: start preview" })
			vim.keymap.set("n", "<leader>vmS", "<cmd>MarkdownPreviewStop<cr>", { desc = "Markdown: stop preview" })
			vim.keymap.set("n", "<leader>vmr", "<cmd>MarkdownPreviewRefresh<cr>", { desc = "Markdown: refresh preview" })
		end,
	},
}
