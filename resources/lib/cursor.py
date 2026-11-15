"""Hide the KWin cursor during playback after a mode change.

While Kodi resizes its window to the new mode the pointer can end up outside it,
and KWin then shows its own cursor over the video until the mouse moves. The
KWin "Hide Cursor" effect is loaded for the playback and unloaded afterwards,
unless it was already loaded.
"""

import subprocess

import xbmc

from resources.lib.kscreen import log

EFFECT = "hidecursor"
GROUP = "Effect-hidecursor"
KEY = "InactivityDuration"
HIDE_AFTER = 3  # seconds without pointer activity


def run(cmd):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"{cmd[0]} failed: {e}", xbmc.LOGWARNING)
        return None
    if res.returncode != 0:
        log(f"{' '.join(cmd)}: {res.stderr.strip()}", xbmc.LOGWARNING)
        return None
    return res.stdout.strip()


def effects(method, name):
    return run(["gdbus", "call", "--session", "--dest", "org.kde.KWin",
                "--object-path", "/Effects", "--method", f"org.kde.kwin.Effects.{method}", name])


def kwinrc(*args):
    return ["--file", "kwinrc", "--group", GROUP, "--key", KEY, *args]


class CursorHider:
    def __init__(self):
        self.loaded = False
        self.wrote = False

    def hide(self):
        if self.loaded or effects("isEffectLoaded", EFFECT) != "(false,)":
            return
        if not run(["kreadconfig6", *kwinrc()]):
            # Not set by the user, the effect's default 0 never hides the cursor.
            self.wrote = run(["kwriteconfig6", *kwinrc(str(HIDE_AFTER))]) is not None
        if effects("loadEffect", EFFECT) == "(true,)":
            self.loaded = True
            # Loading doesn't reread kwinrc, this does.
            effects("reconfigureEffect", EFFECT)
            log("cursor hidden during playback")
        else:
            self.restore()

    def restore(self):
        if self.loaded:
            effects("unloadEffect", EFFECT)
            self.loaded = False
        if self.wrote:
            run(["kwriteconfig6", *kwinrc("--delete")])
            self.wrote = False
