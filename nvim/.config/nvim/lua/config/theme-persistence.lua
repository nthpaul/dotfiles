-- Store in memory, only persist on exit
local M = {}
local theme_prefs = { dark = "carbonfox", light = "dayfox" }

-- Load saved preferences on startup
local function load_preferences()
	local ok, saved = pcall(function()
		return dofile(vim.fn.stdpath("config") .. "/theme-prefs.lua")
	end)
	if ok and saved then
		theme_prefs = saved
	end
end

-- Save only on VimLeavePre
local function save_preferences()
	local file = io.open(vim.fn.stdpath("config") .. "/theme-prefs.lua", "w")
	if file then
		file:write("return " .. vim.inspect(theme_prefs))
		file:close()
	end
end

function M.setup()
	load_preferences()

	-- Auto-save on exit
	vim.api.nvim_create_autocmd("VimLeavePre", {
		callback = save_preferences,
	})

	-- Track theme changes
	vim.api.nvim_create_autocmd("ColorScheme", {
		callback = function()
			if vim.g.colors_name then
				theme_prefs[vim.o.background] = vim.g.colors_name
			end
		end,
	})
end

-- Get current theme for the given background mode
function M.get_theme(background)
	return theme_prefs[background or vim.o.background]
end

-- Apply theme function
function M.apply_current_theme()
	local theme = theme_prefs[vim.o.background]
	if theme then
		vim.cmd("colorscheme " .. theme)
	end
end

-- Setup auto-dark-mode with theme persistence
function M.setup_auto_dark_mode()
	require("auto-dark-mode").setup({
		update_interval = 1000,
		set_dark_mode = function()
			vim.o.background = "dark"
			M.apply_current_theme()
		end,
		set_light_mode = function()
			vim.o.background = "light"
			M.apply_current_theme()
		end,
	})
end

return M
