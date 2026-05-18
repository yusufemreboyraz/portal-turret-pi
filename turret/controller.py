"""Kamera pikselinden servo açısına dönüşüm + yumuşatma.

Kamera turret tepesinde SABİT, silah hareketli. Bu yüzden hata-güdümlü
değil, kalibre edilmiş doğrusal eşleme kullanılır: piksel (x,y) -> (pan,tilt).
calibrate.py kalibrasyon noktalarını config.yaml'a yazar.

Yumuşatma: low-pass filtre + kare başına maksimum açı adımı (servo titremesi
ve mekanik zorlanmayı önler).
"""

from __future__ import annotations

from dataclasses import dataclass


def _lerp_map(v, in_min, in_max, out_a, out_b):
    if in_max == in_min:
        return out_a
    t = (v - in_min) / (in_max - in_min)
    return out_a + t * (out_b - out_a)


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


@dataclass
class ServoCommand:
    pan: int
    tilt: int
    eye_x: int
    eye_y: int


class Controller:
    def __init__(self, cfg: dict):
        self.servos = cfg["servos"]
        self.cal = cfg["calibration"]
        sm = cfg["smoothing"]
        self.max_step = float(sm["max_step_deg"])
        self.alpha = float(sm["lowpass_alpha"])
        self.eye_gain = float(self.servos["eye_follow_gain"])

        # Yumuşatılmış mevcut açılar — merkezden başla.
        self._pan = float(self.servos["pan"]["center"])
        self._tilt = float(self.servos["tilt"]["center"])

    # -- piksel -> ham açı (kalibrasyon) --
    def _pixel_to_pan(self, px: float) -> float:
        c = self.cal["pan"]
        a = _lerp_map(px, c["px_min"], c["px_max"],
                      c["deg_at_px_min"], c["deg_at_px_max"])
        if self.servos["pan"]["invert"]:
            a = 180 - a
        return a

    def _pixel_to_tilt(self, py: float) -> float:
        c = self.cal["tilt"]
        a = _lerp_map(py, c["px_min"], c["px_max"],
                      c["deg_at_px_min"], c["deg_at_px_max"])
        if self.servos["tilt"]["invert"]:
            a = 180 - a
        return a

    def _smooth(self, cur: float, target: float) -> float:
        # low-pass
        nxt = cur + self.alpha * (target - cur)
        # slew limit
        d = nxt - cur
        if d > self.max_step:
            nxt = cur + self.max_step
        elif d < -self.max_step:
            nxt = cur - self.max_step
        return nxt

    def update(self, target_px) -> ServoCommand:
        """target_px = (cx, cy) ya da None (hedef yok -> merkeze yumuşak dönüş)."""
        ps, ts = self.servos["pan"], self.servos["tilt"]
        if target_px is None:
            raw_pan = float(ps["center"])
            raw_tilt = float(ts["center"])
        else:
            cx, cy = target_px
            raw_pan = self._pixel_to_pan(cx)
            raw_tilt = self._pixel_to_tilt(cy)

        raw_pan = _clamp(raw_pan, ps["min"], ps["max"])
        raw_tilt = _clamp(raw_tilt, ts["min"], ts["max"])

        self._pan = self._smooth(self._pan, raw_pan)
        self._tilt = self._smooth(self._tilt, raw_tilt)

        pan_i = int(round(self._pan))
        tilt_i = int(round(self._tilt))

        # Göz, pan/tilt merkez sapmasını ölçekli taklit eder.
        ex_cfg, ey_cfg = self.servos["eye_x"], self.servos["eye_y"]
        eye_x = ex_cfg["center"] + self.eye_gain * (self._pan - ps["center"])
        eye_y = ey_cfg["center"] + self.eye_gain * (self._tilt - ts["center"])
        if ex_cfg["invert"]:
            eye_x = 180 - eye_x
        if ey_cfg["invert"]:
            eye_y = 180 - eye_y
        eye_x = int(round(_clamp(eye_x, ex_cfg["min"], ex_cfg["max"])))
        eye_y = int(round(_clamp(eye_y, ey_cfg["min"], ey_cfg["max"])))

        return ServoCommand(pan_i, tilt_i, eye_x, eye_y)
