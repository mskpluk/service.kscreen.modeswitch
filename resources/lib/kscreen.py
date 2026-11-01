"""kscreen-doctor access shared by the service and the output selection."""

import json
import subprocess

import xbmc

KSCREEN = "kscreen-doctor"
AUTO = "auto"


def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[service.kscreen.modeswitch] {msg}", level)


def kscreen(args):
    try:
        res = subprocess.run([KSCREEN] + args, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"{KSCREEN} failed: {e}", xbmc.LOGERROR)
        return None
    if res.returncode != 0:
        log(f"{KSCREEN} {' '.join(args)}: {res.stderr.strip()}", xbmc.LOGERROR)
        return None
    return res.stdout


def outputs():
    """All outputs kscreen-doctor reports, or an empty list."""
    out = kscreen(["-j"])
    if not out:
        return []
    try:
        return json.loads(out).get("outputs", [])
    except ValueError:
        log("cannot parse kscreen-doctor output", xbmc.LOGERROR)
        return []


def current_mode_name(output):
    for mode in output.get("modes", []):
        if str(mode.get("id")) == str(output.get("currentModeId")):
            return mode.get("name", "")
    return ""
