return {
    'nvim-telescope/telescope.nvim',
    dependencies = {
        'nvim-lua/plenary.nvim',
    },
    config = function()
        local actions = require('telescope.actions')
        require('telescope').setup({
            defaults = {
                mappings = {
                    i = {
                        ["<C-k>"] = actions.move_selection_previous,
                        ["<C-j>"] = actions.move_selection_next,
                    }
                }
            }
        })

        local builtin = require('telescope.builtin')
        vim.keymap.set('n', '<leader>ff', builtin.find_files, {})
        vim.keymap.set('n', '<leader>fb', builtin.buffers, { desc = 'Telescope buffers' })
        vim.keymap.set("n", "<leader>gs", ":Telescope git_status<CR>")
        vim.keymap.set("n", "<leader>fs", function()
          builtin.grep_string({ search = vim.fn.input("Grep > ")})
        end)

        -- fun
        vim.keymap.set('n', '<leader>fth', ':Telescope colorscheme<CR>')
    end
}
