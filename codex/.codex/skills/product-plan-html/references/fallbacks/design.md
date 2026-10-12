# Traba visual guidance when traba-design is unavailable

Use this reference only when capability discovery cannot find traba-design, or the user
requests a standalone package. Installed guidance takes precedence.

The light theme uses a white page, Poppins at weights 400, 500 and 600, 1px dividers
in #E2E5E9, a 154px app sidebar, and 52px app topbar. Badges have a 4px radius;
buttons, inputs and navigation use 8px; cards and avatars use 12px. Icons use SVG
stroke-width 1.8. Use generous whitespace and soft borders.

Core tokens: violet #8000FF, violet tint #F5EBFF, navy #08105E, body #414D58,
muted #66788A, gray tint #F7F7F8. Semantic text/tint pairs: green #138656/#EDF8F3,
red #C20A47/#FEE7EE, orange #C2750A/#FEF4E7, blue #4562A1/#E9EFFC.

Use 13px body text, 13–14px medium section labels, 18–20px semibold app headings,
and 28px semibold KPI values. Uppercase small table/KPI/sidebar labels. Violet marks
primary actions and active states; semantic badges describe status. Keep focus states
visible, label controls and ensure disabled actions have a visible reason nearby.

Scope mock app frames separately from the document viewer. At narrow widths stack
columns, hide the simulated desktop sidebar, keep tables and diagrams scrollable, and
avoid clipped phone frames or dialogs. Use realistic fictional workers, facilities,
roles and shifts, clearly labeled as sample data.

These tokens guide standalone HTML as well as app components. Do not imply a vanilla
HTML prototype imports production React components. Bundle local licensed font assets
when available and retain a readable sans-serif fallback.
