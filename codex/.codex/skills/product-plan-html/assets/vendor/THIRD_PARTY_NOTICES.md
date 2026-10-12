# Bundled diagram renderer

`viz.js` is an unmodified distribution of @viz-js/viz 3.25.0, copyright Michael Daines, licensed under MIT. Its package metadata and checksum are in vendor.json; LICENSE-viz.txt carries its license.

The distribution embeds Graphviz 14.1.3 in WebAssembly object code. Graphviz is licensed under the Eclipse Public License 1.0; see LICENSE-Graphviz.txt. The corresponding public Graphviz source is available at https://gitlab.com/graphviz/graphviz/-/tree/14.1.3 and the Viz build source is https://github.com/mdaines/viz-js/tree/release-viz-3.25.0.

The distribution also embeds Expat object code. Its MIT-style license and copyright notices are included in LICENSE-Expat.txt, obtained from https://raw.githubusercontent.com/libexpat/libexpat/R_2_7_5/COPYING. The Expat project source is https://github.com/libexpat/libexpat.

These components run only at build time. The generated HTML contains their SVG output, not the renderer or WebAssembly.
