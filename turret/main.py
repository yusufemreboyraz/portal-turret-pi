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
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


class Turret:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        t = cfg["timers"]
        self.found_s = t["found_ms"] / 1000.0
        self.lost_s = t["lost_ms"] / 1000.0
        self.reacquire_s = t["reacquire_ms"] / 1000.0
        self.fire_cooldown_s = t["fire_cooldown_ms"] / 1000.0
        self.lock_tol = t["lock_tolerance_px"]
        self.laser_on = cfg["servos"]["laser_always_on"]

        self.cam = Camera(cfg["camera"]["width"], cfg["camera"]["height"],
                          cfg["camera"]["fps"], cfg["camera"]["hflip"],
                          cfg["camera"]["vflip"])
        d = cfg["detection"]
        self.detector = PersonDetector(d["backend"], d["model"], d["use_ncnn"],
                                       d["conf"], d["person_class_id"])
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

        self._streaming = cfg.get("streaming", {}).get("enabled", False)
        if self._streaming:
            ip = cfg["streaming"].get("client_ip", "127.0.0.1")
            port = cfg["streaming"].get("video_port", 5000)
            fps = cfg["camera"]["fps"]
            w = cfg["camera"]["width"]
            h = cfg["camera"]["height"]
            # Raspberry Pi'de düşük gecikme için x264enc donanım/yazılım encoding
            pipeline = (
                f"appsrc ! videoconvert ! video/x-raw,format=I420 ! "
                f"x264enc tune=zerolatency bitrate=1000 speed-preset=ultrafast ! "
                f"rtph264pay ! udpsink host={ip} port={port}"
            )
            import cv2
            self._video_writer = cv2.VideoWriter(pipeline, cv2.CAP_GSTREAMER, 0, fps, (w, h))
            if not self._video_writer.isOpened():
                print("[turret] UYARI: GStreamer VideoWriter başlatılamadı!")
            else:
                print(f"[turret] GStreamer yayını başladı -> {ip}:{port}")
        else:
            self._video_writer = None

    def _set_state(self, new: str):
        if new != self.state:
            print(f"[state] {self.state} -> {new}")
            self.state = new
            self._state_since = time.monotonic()

    def _in_state(self) -> float:
        return time.monotonic() - self._state_since

    def stop(self, *_):
        self._running = False

    def run(self):
        cfg = self.cfg
        show = cfg["debug"]["show_window"]
        print_fps = cfg["debug"]["print_fps"]
        if show or self._video_writer is not None:
            import cv2
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
            if has_target and self.state in (ACQUIRED, TRACKING):
                px = (target.cx, target.cy)
            else:
                px = None
            cmd = self.ctrl.update(px)
            self.link.send(cmd.pan, cmd.tilt, cmd.eye_x, cmd.eye_y,
                           laser=self.laser_on)

            # ---- "kilit" -> Fire sesi (ateş yok, sadece ses) ----
            if self.state == TRACKING and has_target:
                err = math.hypot(target.cx - self._cx, target.cy - self._cy)
                if (err <= self.lock_tol
                        and now - self._last_fire >= self.fire_cooldown_s):
                    self.sound.play("lock")
                    self._last_fire = now

            # ---- debug & streaming ----
            if show or self._video_writer is not None:
                if target:
                    cv2.rectangle(
                        frame,
                        (target.cx - target.w // 2, target.cy - target.h // 2),
                        (target.cx + target.w // 2, target.cy + target.h // 2),
                        (0, 0, 255), 2)
                cv2.putText(frame, self.state, (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
            if self._video_writer is not None:
                self._video_writer.write(frame)

            if show:
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
        if getattr(self, "_video_writer", None) is not None:
            self._video_writer.release()
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
