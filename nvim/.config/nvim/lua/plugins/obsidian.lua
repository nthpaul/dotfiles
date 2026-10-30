return {
	"obsidian-nvim/obsidian.nvim",
	version = "*",
	ft = "markdown",
	cmd = "Obsidian",
	dependencies = { "nvim-telescope/telescope.nvim" },
	keys = {
		{ "<leader>nf", "<cmd>Obsidian quick_switch<cr>", desc = "Notes: find" },
		{ "<leader>ns", "<cmd>Obsidian search<cr>", desc = "Notes: search" },
		{ "<leader>nn", "<cmd>Obsidian new<cr>", desc = "Notes: new" },
		{ "<leader>nd", "<cmd>Obsidian today<cr>", desc = "Notes: daily note" },
		{ "<leader>nb", "<cmd>Obsidian backlinks<cr>", desc = "Notes: backlinks" },
		{ "<leader>nl", "<cmd>Obsidian follow_link<cr>", desc = "Notes: follow link" },
		{ "<leader>nt", "<cmd>Obsidian template<cr>", desc = "Notes: insert template" },
		{ "<leader>no", "<cmd>Obsidian open<cr>", desc = "Notes: open in Obsidian" },
	},
	opts = {
		legacy_commands = false,
		workspaces = {
			{
				name = "praxis",
				path = "~/Library/Mobile Documents/com~apple~CloudDocs/Documents/praxis/praxis",
			},
		},
		notes_subdir = "Notes",
		new_notes_location = "notes_subdir",
		note_id_func = function(title)
			return title or require("obsidian.builtin").zettel_id()
		end,
		link = { style = "markdown", auto_update = true },
		picker = { name = "telescope.nvim" },
		templates = { folder = "90 System/Templates" },
		daily_notes = {
			folder = "00 Journal",
			date_format = "YYYY/[Daily]/YYYY-MM-DD",
			template = "Daily",
		},
		attachments = { folder = "System/Attachments" },
		-- Keep Markdown rendering with render-markdown.nvim and Snacks.
		ui = { enable = false },
		footer = { enabled = false },
		frontmatter = { enabled = false },
	},
}
