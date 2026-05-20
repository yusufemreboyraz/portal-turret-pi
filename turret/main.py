"""Portal Turret orkestratörü — durum makinesi.

Akış: kamera -> insan tespiti -> piksel->açı -> Arduino'ya komut + Portal sesleri.

Durumlar (eski Turret.ini zamanlayıcı mantığı):
  SEARCHING        : hedef yok, servolar merkeze, lazer yanık, nötr göz
  TARGET_ACQUIRED  : insan görüldü; found_ms boyunca sürerse -> TRACKING ("I see you")
  TRACKING         : hedefi sürekli takip; merkeze kilitlenince "Gotcha/Fire" sesi
  TARGET_LOST      : hedef kayboldu; lost_ms sonra "Are you still there?" -> SEARCHING
                     (reacquire_ms içinde yeniden görülürse -> TRACKING)

Çalıştırma:  python3 main.py
"""

from __future__ import annotations

import math
import os
import random
import signal
import sys
import time

import yaml

from controller import Controller
from serial_link import SerialLink
from sound import SoundPlayer
from vision import Camera, PersonDetector

HERE = os.path.dirname(os.path.abspath(__file__))

SEARCHING = "SEARCHING"
ACQUIRED = "TARGET_ACQUIRED"
TRACKING = "TRACKING"
LOST = "TARGET_LOST"


def load_cfg():
    with open(os.path.join(HERE, "config.yaml")) as f:
        return yaml.safe_load(f)


class Turret:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        t = cfg["timers"]
        self.found_s = t["found_ms"] / 1000.0
        self.lost_s = t["lost_ms"] / 1000.0
        self.reacquire_s = t["reacquire_ms"] / 1000.0
        self.fire_cooldown_s = t["fire_cooldown_ms"] / 1000.0
        self.fire_bbox_ratio = float(t.get("fire_bbox_ratio", 0.40))
        self.fire_duration_s = t.get("fire_duration_ms", 600) / 1000.0
        self.laser_on = cfg["servos"]["laser_always_on"]

        rc = cfg.get("recoil", {}) or {}
        self.recoil_enabled = bool(rc.get("enabled", True))
        self.recoil_tilt_deg = float(rc.get("tilt_kick_deg", 10))
        self.recoil_pan_deg = float(rc.get("pan_jitter_deg", 3))
        self.recoil_freq = float(rc.get("freq_hz", 7.0))

        idle = cfg.get("idle_scan", {}) or {}
        self.idle_enabled = bool(idle.get("enabled", True))
        self.idle_min_s = float(idle.get("min_change_s", 1.5))
        self.idle_max_s = float(idle.get("max_change_s", 4.0))
        self.idle_pan_margin = float(idle.get("pan_margin_deg", 5))
        self.idle_tilt_jitter = float(idle.get("tilt_jitter_deg", 8))
        self._idle_pan = float(cfg["servos"]["pan"]["center"])
        self._idle_tilt = float(cfg["servos"]["tilt"]["center"])
        self._idle_next_t = 0.0

        self.cam = Camera(cfg["camera"]["width"], cfg["camera"]["height"],
                          cfg["camera"]["fps"], cfg["camera"]["hflip"],
                          cfg["camera"]["vflip"])
        d = cfg["detection"]
        self.detector = PersonDetector(d["backend"], d["model"], d["use_ncnn"],
                                       d["conf"], d["person_class_id"])
        # Nişan noktası ofseti: kutu yüksekliğinin oranı kadar Y'de kaydırır.
        # 0.0 = tam merkez, -0.2 = merkezden %20 yukarı (göğüs/baş bölgesi).
        self.aim_y_offset = float(d.get("aim_y_offset_ratio", -0.2))
        self.aim_off_px_x = int(d.get("aim_pixel_offset_x", 0))
        self.aim_off_px_y = int(d.get("aim_pixel_offset_y", 0))
        self.ctrl = Controller(cfg)
        self.link = SerialLink(cfg["serial"]["port"], cfg["serial"]["baud"],
                               cfg["serial"]["command_hz"],
                               cfg["serial"]["reconnect_delay_s"])
        self.sound = SoundPlayer(cfg, HERE)

        self.state = SEARCHING
        self._state_since = time.monotonic()
        self._last_seen = 0.0
        self._last_fire = 0.0
        self._running = True

        self._cx = cfg["camera"]["width"] // 2
        self._cy = cfg["camera"]["height"] // 2

    def _set_state(self, new: str):
        if new != self.state:
            print(f"[state] {self.state} -> {new}")
            self.state = new
            self._state_since = time.monotonic()

    def _in_state(self) -> float:
        return time.monotonic() - self._state_since

    def _idle_step(self, now: float):
        """Boştayken doğal "etrafa bakınma" — rastgele pan + küçük tilt."""
        if now >= self._idle_next_t:
            ps = self.cfg["servos"]["pan"]
            ts = self.cfg["servos"]["tilt"]
            lo = ps["min"] + self.idle_pan_margin
            hi = ps["max"] - self.idle_pan_margin
            # Karışık genlik: bazen küçük, bazen büyük hareket -> doğal his.
            mag = random.choice([0.25, 0.5, 0.85, 1.0])
            mid = (lo + hi) / 2.0
            half = (hi - lo) / 2.0 * mag
            self._idle_pan = random.uniform(mid - half, mid + half)
            self._idle_tilt = ts["center"] + random.uniform(
                -self.idle_tilt_jitter, self.idle_tilt_jitter)
            self._idle_next_t = now + random.uniform(
                self.idle_min_s, self.idle_max_s)
        return (self._idle_pan, self._idle_tilt)

    def stop(self, *_):
        self._running = False

    def run(self):
        cfg = self.cfg
        show = cfg["debug"]["show_window"]
        print_fps = cfg["debug"]["print_fps"]
        if show:
            import cv2
        # Otomatik modda güvenli kenar limitleri MUTLAKA açık olsun
        # (serial_test raw bırakmış olabilir).
        self.link.send_raw("L,1")
        frames = 0
        fps_t0 = time.monotonic()

        while self._running:
            frame = self.cam.read()
            if frame is None:
                continue
            now = time.monotonic()

            target = self.detector.detect(frame)
            has_target = target is not None
            if has_target:
                self._last_seen = now

            # ---- durum geçişleri ----
            if self.state == SEARCHING:
                if has_target:
                    self._set_state(ACQUIRED)

            elif self.state == ACQUIRED:
                if not has_target:
                    self._set_state(SEARCHING)
                elif self._in_state() >= self.found_s:
                    self.sound.play("found")
                    self._set_state(TRACKING)

            elif self.state == TRACKING:
                if not has_target:
                    self._set_state(LOST)

            elif self.state == LOST:
                if has_target:
                    self._set_state(TRACKING)  # reacquire
                elif self._in_state() >= self.lost_s:
                    self.sound.play("lost")
                    self._set_state(SEARCHING)

            # ---- aktüasyon ----
            target_angle = None
            if has_target and self.state in (ACQUIRED, TRACKING):
                # Merkezden yukarıya doğru ofset (kutu yüksekliği oranı).
                aim_y = target.cy + int(round(self.aim_y_offset * target.h))
                # Lazer ↔ kamera paralaks ince ayarı (calibrate_aim.py yazar).
                aim_x = target.cx + self.aim_off_px_x
                aim_y = aim_y + self.aim_off_px_y
                px = (aim_x, aim_y)
            else:
                px = None
                if self.state == SEARCHING and self.idle_enabled:
                    target_angle = self._idle_step(now)
            cmd = self.ctrl.update(px, target_angle=target_angle)

            # ---- ATEŞ tetiği: bbox kareyi yeterince kaplıyor mu? ----
            if (self.state == TRACKING and has_target
                    and (now - self._last_fire) >= self.fire_cooldown_s):
                bbox_ratio = (target.w * target.h) / float(
                    self.cfg["camera"]["width"] * self.cfg["camera"]["height"])
                if bbox_ratio >= self.fire_bbox_ratio:
                    self.sound.play("lock")
                    self.link.send_raw("F")     # LED koreografisini başlat
                    self._last_fire = now

            # ---- Geri tepme: ateş penceresi boyunca pan/tilt'e ofset ekle ----
            pan_out, tilt_out = cmd.pan, cmd.tilt
            if self.recoil_enabled:
                dt = now - self._last_fire
                if 0.0 <= dt < self.fire_duration_s:
                    decay = 1.0 - (dt / self.fire_duration_s)         # 1 -> 0
                    phase = 2 * math.pi * self.recoil_freq * dt
                    tilt_out += int(round(self.recoil_tilt_deg * decay *
                                          (0.5 + 0.5 * math.cos(phase))))
                    pan_out += int(round(self.recoil_pan_deg * decay *
                                         math.sin(phase * 1.3)))
            self.link.send(pan_out, tilt_out, cmd.eye_x, cmd.eye_y,
                           laser=self.laser_on)

            # ---- debug ----
            if show:
                if target:
                    cv2.rectangle(
                        frame,
                        (target.cx - target.w // 2, target.cy - target.h // 2),
                        (target.cx + target.w // 2, target.cy + target.h // 2),
                        (0, 0, 255), 2)
                    # Nişan noktası (ofsetli) — sarı artı
                    aim_y = target.cy + int(round(self.aim_y_offset * target.h))
                    cv2.drawMarker(frame, (target.cx, aim_y), (0, 255, 255),
                                   cv2.MARKER_CROSS, 18, 2)
                cv2.putText(frame, self.state, (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("turret", frame)
                if (cv2.waitKey(1) & 0xFF) == ord("q"):
                    break

            frames += 1
            if print_fps and now - fps_t0 >= 2.0:
                print(f"[fps] {frames / (now - fps_t0):.1f}  state={self.state}")
                frames = 0
                fps_t0 = now

        self._shutdown(show)

    def _shutdown(self, show):
        print("[turret] kapanıyor; servolar merkeze, lazer kapalı")
        c = self.cfg["servos"]
        # Failsafe zaten merkeze döner ama açıkça da yollayalım.
        self.link.send(c["pan"]["center"], c["tilt"]["center"],
                       c["eye_x"]["center"], c["eye_y"]["center"],
                       laser=False, force=True)
        time.sleep(0.2)
        self.cam.close()
        self.link.close()
        self.sound.close()
        if show:
            import cv2
            cv2.destroyAllWindows()


def main():
    cfg = load_cfg()
    turret = Turret(cfg)
    signal.signal(signal.SIGINT, turret.stop)
    signal.signal(signal.SIGTERM, turret.stop)
    turret.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
