local colorschemes = require("config.colorschemes")

local function spec_from_colorscheme(item)
	local spec = {
		item.repo,
		lazy = false,
		priority = 1000,
	}
	for _, key in ipairs({ "name", "dependencies", "opts", "config" }) do
		if item[key] ~= nil then
			spec[key] = item[key]
		end
	end
	return spec
end

return vim.list_extend({
	{
		"f-person/auto-dark-mode.nvim",
		config = function()
			local theme_persistence = require("config.theme-persistence")
			theme_persistence.setup()
			theme_persistence.setup_auto_dark_mode()
			require("auto-dark-mode").init()
		end,
	},
}, vim.tbl_map(spec_from_colorscheme, colorschemes))
