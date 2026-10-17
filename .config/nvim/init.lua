-- ~/.config/nvim/init.lua
-- Fast, cross-platform Neovim configuration with sensible defaults and optional lazy.nvim plugins

--------------------------------------------------------------------------------
-- 1. Leader Key
--------------------------------------------------------------------------------
vim.g.mapleader = " "
vim.g.maplocalleader = " "

--------------------------------------------------------------------------------
-- 2. Core Editor Options (preserved from .vimrc + modern defaults)
--------------------------------------------------------------------------------
local opt = vim.opt

-- Line numbers
opt.number = true
opt.relativenumber = true
opt.signcolumn = "yes"

-- Indentation (4 spaces default from .vimrc)
opt.tabstop = 4
opt.softtabstop = 4
opt.shiftwidth = 4
opt.expandtab = true
opt.smartindent = true
opt.autoindent = true

-- Search behavior
opt.ignorecase = true
opt.smartcase = true
opt.incsearch = true
opt.hlsearch = true

-- Windows, Splits & UI
opt.splitbelow = true
opt.splitright = true
opt.wrap = false
opt.mouse = "a"
opt.termguicolors = true
opt.scrolloff = 8
opt.sidescrolloff = 8
opt.cursorline = true
opt.showmode = false
opt.updatetime = 250
opt.timeoutlen = 300

-- Files, Buffers & Undo
opt.hidden = true
opt.autowrite = true
opt.undofile = true
opt.swapfile = false
opt.backup = false

-- Clipboard (sync with system clipboard when supported)
opt.clipboard = "unnamedplus"

--------------------------------------------------------------------------------
-- 3. Core Autocommands
--------------------------------------------------------------------------------
local augroup = vim.api.nvim_create_augroup("UserConfig", { clear = true })

-- Jump to last known cursor position on file reopen (ported from .vimrc)
vim.api.nvim_create_autocmd("BufReadPost", {
    group = augroup,
    callback = function(args)
        local mark = vim.api.nvim_buf_get_mark(args.buf, '"')
        local line_count = vim.api.nvim_buf_line_count(args.buf)
        if mark[1] > 0 and mark[1] <= line_count then
            pcall(vim.api.nvim_win_set_cursor, 0, mark)
        end
    end,
})

-- Highlight text momentarily on yank
vim.api.nvim_create_autocmd("TextYankPost", {
    group = augroup,
    callback = function()
        vim.highlight.on_yank({ higroup = "IncSearch", timeout = 150 })
    end,
})

-- 2-space indentation for web, configuration, and doc formats
vim.api.nvim_create_autocmd("FileType", {
    group = augroup,
    pattern = { "lua", "json", "yaml", "toml", "markdown", "html", "css", "javascript", "typescript", "typescriptreact" },
    callback = function()
        vim.opt_local.tabstop = 2
        vim.opt_local.softtabstop = 2
        vim.opt_local.shiftwidth = 2
    end,
})

--------------------------------------------------------------------------------
-- 4. Keymaps
--------------------------------------------------------------------------------
local map = vim.keymap.set

-- Clear search highlight on <Esc>
map("n", "<Esc>", "<cmd>nohlsearch<CR>", { silent = true, desc = "Clear search highlight" })

-- Better window navigation
map("n", "<C-h>", "<C-w>h", { desc = "Navigate left window" })
map("n", "<C-j>", "<C-w>j", { desc = "Navigate down window" })
map("n", "<C-k>", "<C-w>k", { desc = "Navigate up window" })
map("n", "<C-l>", "<C-w>l", { desc = "Navigate right window" })

-- Diagnostics navigation
map("n", "[d", vim.diagnostic.goto_prev, { desc = "Previous diagnostic" })
map("n", "]d", vim.diagnostic.goto_next, { desc = "Next diagnostic" })
map("n", "<leader>e", vim.diagnostic.open_float, { desc = "Line diagnostics" })
map("n", "<leader>q", vim.diagnostic.setloclist, { desc = "Quickfix diagnostics" })

-- Fast buffer navigation
map("n", "<leader>bn", "<cmd>bnext<CR>", { desc = "Next buffer" })
map("n", "<leader>bp", "<cmd>bprevious<CR>", { desc = "Previous buffer" })
map("n", "<leader>bd", "<cmd>bdelete<CR>", { desc = "Close buffer" })

--------------------------------------------------------------------------------
-- 5. Package Manager Bootstrap (lazy.nvim)
--------------------------------------------------------------------------------
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
local has_git = vim.fn.executable("git") == 1

if has_git and not vim.loop.fs_stat(lazypath) then
    vim.fn.system({
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/folke/lazy.nvim.git",
        "--branch=stable",
        lazypath,
    })
end

if vim.loop.fs_stat(lazypath) then
    vim.opt.rtp:prepend(lazypath)

    local status_ok, lazy = pcall(require, "lazy")
    if status_ok then
        lazy.setup({
            -- Colorscheme
            {
                "catppuccin/nvim",
                name = "catppuccin",
                priority = 1000,
                config = function()
                    pcall(vim.cmd.colorscheme, "catppuccin-mocha")
                end,
            },

            -- Which-key (keymap hints)
            {
                "folke/which-key.nvim",
                event = "VeryLazy",
                opts = {},
            },

            -- Git signs in gutter
            {
                "lewis6991/gitsigns.nvim",
                event = { "BufReadPre", "BufNewFile" },
                opts = {},
            },

            -- Fuzzy Finder
            {
                "nvim-telescope/telescope.nvim",
                branch = "0.1.x",
                dependencies = { "nvim-lua/plenary.nvim" },
                cmd = "Telescope",
                keys = {
                    { "<leader>ff", "<cmd>Telescope find_files<cr>", desc = "Find files" },
                    { "<leader>fg", "<cmd>Telescope live_grep<cr>", desc = "Live grep" },
                    { "<leader>fb", "<cmd>Telescope buffers<cr>", desc = "Buffers" },
                    { "<leader>fh", "<cmd>Telescope help_tags<cr>", desc = "Help tags" },
                },
            },

            -- Treesitter (Syntax Highlighting)
            {
                "nvim-treesitter/nvim-treesitter",
                build = ":TSUpdate",
                event = { "BufReadPost", "BufNewFile" },
                config = function()
                    local ts_ok, configs = pcall(require, "nvim-treesitter.configs")
                    if ts_ok then
                        configs.setup({
                            ensure_installed = { "c", "cpp", "python", "lua", "bash", "markdown", "json", "yaml" },
                            highlight = { enable = true },
                            indent = { enable = true },
                        })
                    end
                end,
            },

            -- LSP Configuration & Mason
            {
                "neovim/nvim-lspconfig",
                dependencies = {
                    "williamboman/mason.nvim",
                    "williamboman/mason-lspconfig.nvim",
                },
                config = function()
                    local mason_ok, mason = pcall(require, "mason")
                    if mason_ok then mason.setup() end

                    local mlsp_ok, mlsp = pcall(require, "mason-lspconfig")
                    if mlsp_ok then
                        mlsp.setup({
                            ensure_installed = { "clangd", "pyright", "ruff", "lua_ls" },
                        })
                    end

                    local lspconfig_ok, lspconfig = pcall(require, "lspconfig")
                    if not lspconfig_ok then return end

                    -- Common LSP keymaps when language server attaches
                    vim.api.nvim_create_autocmd("LspAttach", {
                        group = augroup,
                        callback = function(event)
                            local bmap = function(keys, func, desc)
                                vim.keymap.set("n", keys, func, { buffer = event.buf, desc = "LSP: " .. desc })
                            end
                            bmap("gd", vim.lsp.buf.definition, "Goto Definition")
                            bmap("gr", vim.lsp.buf.references, "Goto References")
                            bmap("K", vim.lsp.buf.hover, "Hover Documentation")
                            bmap("<leader>rn", vim.lsp.buf.rename, "Rename")
                            bmap("<leader>ca", vim.lsp.buf.code_action, "Code Action")
                        end,
                    })

                    -- Default server configurations
                    pcall(lspconfig.clangd.setup, {})
                    pcall(lspconfig.pyright.setup, {})
                    pcall(lspconfig.ruff.setup, {})
                    pcall(lspconfig.lua_ls.setup, {
                        settings = {
                            Lua = {
                                diagnostics = { globals = { "vim" } },
                                workspace = { checkThirdParty = false },
                            },
                        },
                    })
                end,
            },
        }, {
            defaults = { lazy = true },
            ui = { border = "rounded" },
            performance = {
                rtp = {
                    disabled_plugins = {
                        "gzip",
                        "tarPlugin",
                        "tohtml",
                        "tutor",
                        "zipPlugin",
                    },
                },
            },
        })
    end
end

-- Fallback colorscheme if catppuccin is not loaded
if vim.g.colors_name == nil then
    pcall(vim.cmd.colorscheme, "habamax")
end
