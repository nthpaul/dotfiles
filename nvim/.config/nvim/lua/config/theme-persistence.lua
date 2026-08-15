-- Store in memory, only persist on exit
local M = {}
local theme_prefs = { dark = "carbonfox", light = "dayfox" }

local function state_prefs_path()
	return vim.fn.stdpath("state") .. "/theme-prefs.lua"
end

local function legacy_config_prefs_path()
	return vim.fn.stdpath("config") .. "/theme-prefs.lua"
end

local function read_prefs(path)
	local ok, saved = pcall(dofile, path)
	if ok and type(saved) == "table" then
		return saved
	end
	return nil
end

local function save_preferences()
	local path = state_prefs_path()
	vim.fn.mkdir(vim.fn.fnamemodify(path, ":h"), "p")
	local file = io.open(path, "w")
	if file then
		file:write("return " .. vim.inspect(theme_prefs))
		file:close()
	end
end

-- Load saved preferences on startup
local function load_preferences()
	local saved = read_prefs(state_prefs_path())
	if saved then
		theme_prefs = saved
		return
	end
	saved = read_prefs(legacy_config_prefs_path())
	if saved then
		theme_prefs = saved
		save_preferences()
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
