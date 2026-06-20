-- Window snapping + saved layout profiles via AutoArrange.spoon
-- Docs: https://github.com/jamesagarside/hammerspoon-auto-arrange
--
-- Default base modifier: Ctrl + Alt (change via menubar WL > Configuration)
--
-- Snap hotkeys (Ctrl+Alt + key):
--   Left/Right half:     <- / ->
--   Top/Bottom half:     Up / Down
--   Corners:             U I J K
--   Thirds:              D F G
--   Two-thirds:          E T
--   Center:              C
--   Maximize:            Enter
--   Save layout:         S
--   Restore layout:      Backspace
--
-- Profiles: menubar WL icon. Save named layouts per monitor setup.
-- URLs: hammerspoon://windowlayout?action=restore|save&profile=Name
-- Snap gaps: 8px padding from screen edges and between tiled windows.

local autoArrangeStorage = hs.fs.pathToAbsolute("~/.hammerspoon/window-layouts")
if not hs.fs.attributes(autoArrangeStorage) then
  hs.fs.mkdir(autoArrangeStorage)
end
hs.json.write(
  { baseModifiers = { "ctrl", "alt" } },
  autoArrangeStorage .. "/settings.json",
  true,
  true
)

hs.loadSpoon("AutoArrange")
spoon.AutoArrange:start()

if not hs.accessibilityState() then
  hs.alert.show(
    "Enable Hammerspoon in System Settings > Privacy & Security > Accessibility",
    10
  )
else
  hs.alert.show("Hammerspoon loaded")
end
