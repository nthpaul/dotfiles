# Inline Mermaid renderer

Snacks invokes the `bin/mmdc` adapter through Neovim's own `PATH`. It renders
Mermaid source with Pele, resolves its SVG theme variables, and rasterizes with
resvg. It implements the input, output, theme, background, and scale flags used
by Snacks. It does not launch Chromium.

Install dependencies after setting up these dotfiles (Node.js 20 or newer):

```sh
cd ~/.config/nvim/tools/mermaid
npm ci
```

Restart Neovim after installation. Normal shells continue to use the original
Mermaid CLI. Pele has its own layout and styling, so diagrams can look different
from Mermaid.js. Renderer errors appear through Snacks notifications.

`<leader>vmt` / `:MarkdownReadingMode` still toggles persistent Markdown and
diagram rendering.

The bundled monochrome Noto Emoji font provides emoji glyphs that resvg cannot
read from Apple's color font. It comes from Google Fonts' `ofl/notoemoji`
directory and is licensed under the SIL Open Font License in `fonts/OFL.txt`.

After changing the adapter or upgrading its dependencies, clear
`~/.cache/nvim/snacks/image/pele` before restarting so Snacks regenerates PNGs.

To return to the original renderer, remove the adapter `PATH` setup and Pele
cache setting from `lua/plugins/markdown-render.lua`, then restart Neovim.
