"""Lets the user pick the output from the ones kscreen-doctor reports."""

import xbmcaddon
import xbmcgui

from resources.lib.kscreen import AUTO, current_mode_name, outputs

ADDON = xbmcaddon.Addon("service.kscreen.modeswitch")


def main():
    found = outputs()
    if not found:
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32005), ADDON.getLocalizedString(32008))
        return

    names = [AUTO] + [o.get("name", "") for o in found]
    labels = [ADDON.getLocalizedString(32006)]
    for o in found:
        state = current_mode_name(o) if o.get("enabled") else ADDON.getLocalizedString(32007)
        labels.append(f"{o.get('name', '')}  ({state})")

    current = ADDON.getSetting("output") or AUTO
    preselect = names.index(current) if current in names else 0
    choice = xbmcgui.Dialog().select(ADDON.getLocalizedString(32005), labels, preselect=preselect)
    if choice >= 0:
        ADDON.setSetting("output", names[choice])


main()
