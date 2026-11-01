# KScreen Mode Switch

Kodi service add-on for KDE Plasma on Wayland. When a video starts it sets
the output resolution, refresh rate and HDR with `kscreen-doctor` to match
the video, and restores the desktop mode when playback stops.

Kodi cannot change the display mode itself under Wayland, which is why
this add-on exists.

## Requirements

- Kodi 21 or newer, running in a KDE Plasma 6 Wayland session
- `kscreen-doctor` (Debian/Ubuntu: `libkscreen-bin`)

## Settings

- **Output**: the output to switch; `auto` uses the first active one.
  Change it with **Choose output**.
- **Switch HDR**: enable HDR for HDR10/HLG/Dolby Vision videos.
- **Allow 4K at 50/60 Hz**: off by default, as many HDMI links cannot
  carry it.
- **Pause after mode change**: seconds to wait for the TV to resync.

## Install

Download `service.kscreen.modeswitch-<version>.zip` (not "Source code")
from [Releases](https://github.com/mskpluk/service.kscreen.modeswitch/releases)
and use *Add-ons → Install from zip file*. This needs *Unknown sources*
enabled in *Settings → System → Add-ons*.

## License

GPL-2.0-or-later
