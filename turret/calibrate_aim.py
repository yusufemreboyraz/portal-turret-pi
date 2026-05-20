"""Lazer ↔ kamera ince ayar (paralaks düzeltmesi).

Sorun: kamera, lazerle aynı noktada değil (örn. ~20cm önde, 10cm altta, 2cm
solda). O yüzden kamera "burada" derken lazer biraz farklı yere düşer. Bu
araç, hedefin merkezine eklenen sabit bir piksel ofsetini elle ayarlamayı
sağlar — birisi tipik mesafede durur, sen klavyeyle nudge edersin, lazer
göğse oturur, kaydedersin.

KULLANIM (Pi'de, ssh ile, ana main.py KAPALI):
  python3 calibrate_aim.py

  - Karşına biri tipik mesafede (örn 2m) dursun.
  - Lazer noktası neredeyse oraya bak, klavyeyle düzelt.

TUŞLAR (Enter'a basmadan, anında):
  a / d   yatay ofset  -2 / +2   (büyük A / D = 10×)
  w / x   dikey ofset  -2 / +2   (büyük W / X = 10×)
  r       ofseti sıfırla
  p       mevcut ofseti yazdır
  s       config.yaml'a kaydet
  q       kaydetmeden çık
"""

from __future__ import annotations

import os
import select
import sys
import termios
import time
import tty

import yaml

from controller import Controller
from serial_link import SerialLink
from vision import Camera, PersonDetector

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "config.yaml")


def save_offsets(x: int, y: int):
    """Sadece detection.aim_pixel_offset_* alanlarını güncelle (yorumları koru)."""
    try:
        from ruamel.yaml import YAML

        ry = YAML()
        ry.preserve_quotes = True
        with open(CFG_PATH) as f:
            doc = ry.load(f)
        doc["detection"]["aim_pixel_offset_x"] = int(x)
        doc["detection"]["aim_pixel_offset_y"] = int(y)
        with open(CFG_PATH, "w") as f:
            ry.dump(doc, f)
        print("\n[kayıt] config.yaml güncellendi (ruamel: yorumlar korundu)")
    except ImportError:
        with open(CFG_PATH) as f:
            doc = yaml.safe_load(f)
        doc["detection"]["aim_pixel_offset_x"] = int(x)
        doc["detection"]["aim_pixel_offset_y"] = int(y)
        with open(CFG_PATH, "w") as f:
            yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)
        print("\n[kayıt] config.yaml güncellendi (PyYAML: yorumlar kayboldu)")


def main():
    with open(CFG_PATH) as f:
        cfg = yaml.safe_load(f)

    cam = Camera(cfg["camera"]["width"], cfg["camera"]["height"],
                 cfg["camera"]["fps"], cfg["camera"]["hflip"],
                 cfg["camera"]["vflip"])
    d = cfg["detection"]
    det = PersonDetector(d["backend"], d["model"], d["use_ncnn"],
                         d["conf"], d["person_class_id"])
    link = SerialLink(cfg["serial"]["port"], cfg["serial"]["baud"],
                      cfg["serial"]["command_hz"],
                      cfg["serial"]["reconnect_delay_s"])
    link.send_raw("L,1")    # güvenli kenar limitleri açık
    ctrl = Controller(cfg)

    aim_y_ratio = float(d.get("aim_y_offset_ratio", -0.2))
    laser_on = bool(cfg["servos"]["laser_always_on"])
    off_x = int(d.get("aim_pixel_offset_x", 0))
    off_y = int(d.get("aim_pixel_offset_y", 0))

    print(__doc__)
    print(f"\n[başlangıç] offset_x={off_x:+d}  offset_y={off_y:+d}")
    print("birisi tipik mesafede dursun; klavyeyle nudge et\n")

    fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(fd)
    last_status = 0.0
    seen_target = False
    try:
        tty.setcbreak(fd)
        while True:
            frame = cam.read()
            if frame is None:
                continue

            t = det.detect(frame)
            if t is not None:
                seen_target = True
                aim_y = t.cy + int(round(aim_y_ratio * t.h)) + off_y
                aim_x = t.cx + off_x
                cmd = ctrl.update((aim_x, aim_y))
            else:
                cmd = ctrl.update(None)

            link.send(cmd.pan, cmd.tilt, cmd.eye_x, cmd.eye_y, laser=laser_on)

            # ~her 0.4s satırı güncelle
            now = time.monotonic()
            if now - last_status >= 0.4:
                tag = "TARGET" if t is not None else " ----  "
                sys.stdout.write(
                    f"\rofset  x={off_x:+4d} y={off_y:+4d}  [{tag}]  "
                    "(a/d w/x = nudge, büyük=10x, r reset, s save, q quit)  "
                )
                sys.stdout.flush()
                last_status = now

            # Klavye (non-blocking)
            if select.select([sys.stdin], [], [], 0)[0]:
                c = sys.stdin.read(1)
                small, big = 2, 10
                if   c == 'a': off_x -= small
                elif c == 'd': off_x += small
                elif c == 'w': off_y -= small
                elif c == 'x': off_y += small
                elif c == 'A': off_x -= big
                elif c == 'D': off_x += big
                elif c == 'W': off_y -= big
                elif c == 'X': off_y += big
                elif c == 'r':
                    off_x = 0; off_y = 0
                    print(f"\n[reset] offset 0,0")
                elif c == 'p':
                    print(f"\n[offset] x={off_x:+d} y={off_y:+d}")
                elif c == 's':
                    save_offsets(off_x, off_y)
                elif c == 'q':
                    print("\n[çıkış] kaydedilmedi.")
                    break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
        # Güvenli kapanış — Arduino failsafe ile zaten merkeze döner.
        cam.close()
        link.close()
        if not seen_target:
            print("uyarı: hiç hedef görülmedi (kamera/kişi/aydınlatma kontrol et).")


if __name__ == "__main__":
    main()
