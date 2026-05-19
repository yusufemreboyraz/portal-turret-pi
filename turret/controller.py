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
        self.deadzone_px = float(sm.get("deadzone_px", 0))
        self.eye_gain = float(self.servos["eye_follow_gain"])
        self.eye_direct = bool(self.servos.get("eye_direct", False))

        cam = cfg["camera"]
        self.frame_w = int(cam["width"])
        self.frame_h = int(cam["height"])

        # Yumuşatılmış mevcut açılar — merkezden başla.
        self._pan = float(self.servos["pan"]["center"])
        self._tilt = float(self.servos["tilt"]["center"])
        self._eye_x = float(self.servos["eye_x"]["center"])
        self._eye_y = float(self.servos["eye_y"]["center"])

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

    # -- piksel -> doğrudan göz açısı (eye_direct modu) --
    def _pixel_to_eye_x(self, px: float) -> float:
        ex = self.servos["eye_x"]
        a = _lerp_map(px, 0, self.frame_w, ex["min"], ex["max"])
        if ex["invert"]:
            a = ex["min"] + ex["max"] - a
        return a

    def _pixel_to_eye_y(self, py: float) -> float:
        ey = self.servos["eye_y"]
        a = _lerp_map(py, 0, self.frame_h, ey["min"], ey["max"])
        if ey["invert"]:
            a = ey["min"] + ey["max"] - a
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

        ex_cfg, ey_cfg = self.servos["eye_x"], self.servos["eye_y"]

        if self.eye_direct:
            # Göz DOĞRUDAN hedef pikseline bakar (eye-only demo için doğru).
            if target_px is None:
                raw_ex = float(ex_cfg["center"])
                raw_ey = float(ey_cfg["center"])
            else:
                cx, cy = target_px
                # Ölü bölge: hedef kare merkezine yakınsa kıpırdama (titreme önler).
                dx = cx - self.frame_w / 2.0
                dy = cy - self.frame_h / 2.0
                if abs(dx) <= self.deadzone_px and abs(dy) <= self.deadzone_px:
                    raw_ex, raw_ey = self._eye_x, self._eye_y
                else:
                    raw_ex = self._pixel_to_eye_x(cx)
                    raw_ey = self._pixel_to_eye_y(cy)
            raw_ex = _clamp(raw_ex, ex_cfg["min"], ex_cfg["max"])
            raw_ey = _clamp(raw_ey, ey_cfg["min"], ey_cfg["max"])
            self._eye_x = self._smooth(self._eye_x, raw_ex)
            self._eye_y = self._smooth(self._eye_y, raw_ey)
        else:
            # Göz, pan/tilt merkez sapmasını ölçekli taklit eder.
            ex = ex_cfg["center"] + self.eye_gain * (self._pan - ps["center"])
            ey = ey_cfg["center"] + self.eye_gain * (self._tilt - ts["center"])
            if ex_cfg["invert"]:
                ex = 180 - ex
            if ey_cfg["invert"]:
                ey = 180 - ey
            self._eye_x = _clamp(ex, ex_cfg["min"], ex_cfg["max"])
            self._eye_y = _clamp(ey, ey_cfg["min"], ey_cfg["max"])

        eye_x = int(round(self._eye_x))
        eye_y = int(round(self._eye_y))
        return ServoCommand(pan_i, tilt_i, eye_x, eye_y)
