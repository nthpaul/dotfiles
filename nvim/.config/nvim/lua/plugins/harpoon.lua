return {
	"ThePrimeagen/harpoon",
	branch = "harpoon2",
	dependencies = { "nvim-lua/plenary.nvim" },
	config = function()
		local harpoon = require("harpoon")
		harpoon:setup()

		vim.keymap.set("n", "<leader>a", function()
			harpoon:list():add()
		end)
		vim.keymap.set("n", "<leader>A", function()
			harpoon:list():prepend()
		end)
		vim.keymap.set("n", "<leader>D", function()
			harpoon:list():remove()
		end)
		vim.keymap.set("n", "<C-e>", function()
			harpoon.ui:toggle_quick_menu(harpoon:list())
		end, { desc = "Harpoon: toggle quick menu" })

		-- <C-1..5> may not be transmitted by all terminal/tmux setups, so keep
		-- terminal-safe alternatives on <leader>1..5 and <leader>r1..5.
		for i = 1, 5 do
			vim.keymap.set("n", "<C-" .. i .. ">", function()
				harpoon:list():select(i)
			end, { desc = "Harpoon: select file " .. i })
			vim.keymap.set("n", "<leader>" .. i, function()
				harpoon:list():select(i)
			end, { desc = "Harpoon: select file " .. i })

			vim.keymap.set("n", "<leader><C-" .. i .. ">", function()
				harpoon:list():replace_at(i)
			end, { desc = "Harpoon: replace file " .. i })
			vim.keymap.set("n", "<leader>r" .. i, function()
				harpoon:list():replace_at(i)
			end, { desc = "Harpoon: replace file " .. i })
		end

		vim.keymap.set("n", "<C-S-N>", function()
			harpoon:list():next()
		end)
		vim.keymap.set("n", "<C-S-P>", function()
			harpoon:list():prev()
		end)
	end,
}
