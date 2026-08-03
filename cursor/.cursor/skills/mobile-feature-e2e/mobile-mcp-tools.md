# Mobile MCP tool catalog

Server id: `user-mobile-mcp`. Call `GetMcpTools` for the server before invoking if schemas may have changed. Use `mcp_auth` when the server reports `needsAuth`.

## Device

| Tool | Purpose |
|------|---------|
| `mobile_list_available_devices` | Physical devices + iOS simulators + Android emulators |
| `mobile_get_screen_size` | Size in pixels |
| `mobile_get_orientation` | Current orientation |
| `mobile_set_orientation` | Change orientation |

## Apps

| Tool | Purpose |
|------|---------|
| `mobile_list_apps` | Installed apps / package ids |
| `mobile_install_app` | Install a build |
| `mobile_uninstall_app` | Remove a build |
| `mobile_launch_app` | Cold/warm start by package id |
| `mobile_terminate_app` | Force stop |
| `mobile_open_url` | Open URL / deep link on device |

## Inspect

| Tool | Purpose |
|------|---------|
| `mobile_take_screenshot` | Screenshot for reasoning (do not cache) |
| `mobile_save_screenshot` | Write screenshot to a file path |
| `mobile_list_elements_on_screen` | Accessibility tree + coordinates (do not cache) |
| `mobile_list_crashes` | Crash report ids |
| `mobile_get_crash` | Crash report body by id |

## Interact

| Tool | Purpose |
|------|---------|
| `mobile_click_on_screen_at_coordinates` | Tap `x,y` |
| `mobile_double_tap_on_screen` | Double-tap |
| `mobile_long_press_on_screen_at_coordinates` | Long-press |
| `mobile_swipe_on_screen` | Swipe direction / distance |
| `mobile_type_keys` | Type into focused field |
| `mobile_press_button` | Hardware / system button |

## Record

| Tool | Purpose |
|------|---------|
| `mobile_start_screen_recording` | Start `.mp4` capture (`device`, optional `output`, `timeLimit`) |
| `mobile_stop_screen_recording` | Stop; returns path / size / duration |

## Usage notes

- Always pass the same `device` id from `mobile_list_available_devices` for the whole session.
- Prefer `mobile_list_elements_on_screen` before coordinate taps when the hierarchy is available.
- For multi-step product flows, script with **Maestro** and use Mobile MCP for recording + verification screenshots.
- Recording output: set `output` to a durable path ending in `.mp4`. If the tool returns a temp path, copy into the evidence folder immediately.
