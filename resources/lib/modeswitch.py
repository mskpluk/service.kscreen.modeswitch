"""Match display mode and HDR to the playing video using kscreen-doctor."""

import os

import xbmc
import xbmcaddon

from resources.lib.kscreen import AUTO, kscreen, log, outputs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")

UHD = (3840, 2160)
FHD = (1920, 1080)
# The player reports the coded size, H.264 rounds 1080 up to 1088.
FHD_CODED_HEIGHT = 1088
DESKTOP = (FHD, 60.0)
# 24.000 fps plays at 23.976 Hz and 30.000 at 29.97 Hz (0.1 %).
RATE_TOLERANCE = 0.002


def get_output(name):
    """The output with this name, or the first active one for "auto"."""
    for output in outputs():
        if not output.get("enabled"):
            continue
        if output.get("name") == name or (name in ("", AUTO) and output.get("connected")):
            return output
    log(f"output {name} not found or disabled", xbmc.LOGWARNING)
    return None


def find_mode(output, size, rate):
    """Closest mode of the given size, or None if no refresh rate is close enough."""
    best = None
    for mode in output.get("modes", []):
        s = mode.get("size", {})
        if (s.get("width"), s.get("height")) != size:
            continue
        err = abs(mode["refreshRate"] - rate) / rate
        if err <= RATE_TOLERANCE and (best is None or err < best[0]):
            best = (err, mode)
    return best[1] if best else None


def candidates(width, height, fps, interlaced, allow_uhd_high_rate):
    """(size, refresh rate) pairs in order of preference."""
    uhd = width > FHD[0] or height > FHD_CODED_HEIGHT
    # 25p in 1080 and interlaced sources play at double rate.
    if interlaced or (not uhd and abs(fps - 25) < 0.1):
        rates = [fps * 2, fps]
    else:
        rates = [fps, fps * 2]
    result = []
    if uhd:
        result += [(UHD, r) for r in rates if r < 31 or allow_uhd_high_rate]
    result += [(FHD, r) for r in rates]
    return result


def choose_mode(output, width, height, fps, interlaced, allow_uhd_high_rate):
    for size, rate in candidates(width, height, fps, interlaced, allow_uhd_high_rate):
        mode = find_mode(output, size, rate)
        if mode:
            return mode
    return None


def apply(output, mode, hdr):
    """Set mode and HDR in one kscreen-doctor call. Returns True if anything changed."""
    name = output["name"]
    args = []
    if mode and str(mode["id"]) != str(output.get("currentModeId")):
        args.append(f"output.{name}.mode.{mode['id']}")
    if hdr is not None and hdr != bool(output.get("hdr")):
        state = "enable" if hdr else "disable"
        args += [f"output.{name}.hdr.{state}", f"output.{name}.wcg.{state}"]
    if not args:
        return False
    log(f"kscreen-doctor {' '.join(args)}")
    return kscreen(args) is not None


def to_int(label):
    digits = "".join(c for c in label if c.isdigit())
    return int(digits) if digits else 0


def to_float(label):
    try:
        return float(label.replace(",", "."))
    except ValueError:
        return 0.0


class Player(xbmc.Player):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def onAVStarted(self):
        self.service.request("start")

    def onPlayBackStopped(self):
        self.service.request("finish")

    def onPlayBackEnded(self):
        self.service.request("finish")

    def onPlayBackError(self):
        self.service.request("finish")


class Service(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.player = Player(self)
        self.pending = None
        self.changed = False

    def request(self, event):
        self.pending = event

    def setting_bool(self, key):
        return ADDON.getSettingBool(key)

    def video_info(self):
        """Width, height, fps and scan type; waits briefly until the player reports them."""
        for _ in range(20):
            width = to_int(xbmc.getInfoLabel("Player.Process(videowidth)"))
            height = to_int(xbmc.getInfoLabel("Player.Process(videoheight)"))
            fps = to_float(xbmc.getInfoLabel("Player.Process(videofps)"))
            if width and height and fps:
                interlaced = xbmc.getInfoLabel("Player.Process(videoscantype)") == "i"
                return width, height, fps, interlaced
            if self.waitForAbort(0.1):
                break
        return None

    def on_start(self):
        if not self.player.isPlayingVideo():
            return

        output = get_output(xbmcaddon.Addon().getSetting("output"))
        if not output:
            return

        mode = None
        info = self.video_info()
        if info:
            width, height, fps, interlaced = info
            mode = choose_mode(output, width, height, fps, interlaced,
                               self.setting_bool("allow_uhd_high_rate"))
            log(f"video {width}x{height} {fps:.3f}{'i' if interlaced else 'p'}, "
                f"mode {mode['name'] if mode else 'not found'}")
        else:
            log("no video info, mode unchanged", xbmc.LOGWARNING)

        hdr = None
        if self.setting_bool("switch_hdr"):
            hdr = bool(xbmc.getInfoLabel("VideoPlayer.HdrType"))

        paused = False
        if not xbmc.getCondVisibility("Player.Paused"):
            self.player.pause()
            paused = True

        if apply(output, mode, hdr):
            self.changed = True
            # Time for the TV and AV receiver to lock onto the new signal.
            self.waitForAbort(ADDON.getSettingInt("settle_delay"))

        if paused and self.player.isPlaying() and xbmc.getCondVisibility("Player.Paused"):
            self.player.pause()

    def restore(self):
        if not self.changed:
            return
        output = get_output(xbmcaddon.Addon().getSetting("output"))
        if not output:
            return
        size, rate = DESKTOP
        apply(output, find_mode(output, size, rate), False)
        self.changed = False

    def run(self):
        if not os.environ.get("WAYLAND_DISPLAY"):
            log("not a Wayland session, service idle")
            return
        log("started")
        while not self.abortRequested():
            event, self.pending = self.pending, None
            if event == "start":
                self.on_start()
            elif event == "finish" and not self.player.isPlayingVideo():
                self.restore()
            if self.waitForAbort(0.1):
                break
        self.restore()
