-- Window snapping + saved layout profiles via AutoArrange.spoon
-- Docs: https://github.com/jamesagarside/hammerspoon-auto-arrange
--
-- Default base modifier: Cmd + Ctrl + Alt (change via menubar WL > Configuration)
--
-- Snap hotkeys (Cmd+Ctrl+Alt + key):
--   Left/Right half:     <- / ->
--   Maximize/Minimize:   Up / Down
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
