"""Lazer ↔ kamera ince ayar (paralaks ofseti + kazanç/swing).

İki tür düzeltme:
  1) OFFSET — merkezde lazer göğse otursun (paralaks).
  2) SWING (kazanç) — yana giderken lazer hedefte kalsın
     (piksel başına servo kaç derece dönüyor).

Yöntem:
  - Önce kişi karenin TAM ORTASINDA dursun. a/d/w/x ile lazer göğse otursun.
  - Sonra yana doğru git (kare kenarına yakın). Lazer hedeften kayıyor mu?
      * Lazer hedeften DAHA UZAĞA savruluyor (servo aşırı salınıyor)
        -> h tuşu (pan swing daralt) / j tuşu (tilt swing daralt)
      * Lazer hedefe YETİŞEMİYOR (servo az salınıyor)
        -> l tuşu (pan swing genişlet) / k tuşu (tilt swing genişlet)
  - Sağ/sol ve yukarı/aşağı uçlarda kontrol et, gerekirse tekrar ortada
    offset'i mikro-ayarla. Tekrarla, oturunca 's' ile kaydet.

KULLANIM (Pi'de, ssh, ana main.py KAPALI):
  python3 calibrate_aim.py

TUŞLAR (Enter'a basmadan, anında):
  Offset (merkez hizalama):
    a / d   yatay  -2 / +2     (büyük A / D = 10×)
    w / x   dikey  -2 / +2     (büyük W / X = 10×)
  Swing (kenar kapsama, kazanç):
    h / l   pan swing  -1° / +1°   (büyük H / L = 5×)
    j / k   tilt swing -1° / +1°   (büyük J / K = 5×)
  Diğer:
    r       offset'i sıfırla
    p       mevcut değerleri yazdır
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


def save_all(cfg: dict):
    """detection.aim_pixel_offset_* + calibration.pan/tilt değerlerini yaz."""
    try:
        from ruamel.yaml import YAML

        ry = YAML()
        ry.preserve_quotes = True
        with open(CFG_PATH) as f:
            doc = ry.load(f)
        for k in ("aim_pixel_offset_x", "aim_pixel_offset_y"):
            doc["detection"][k] = int(cfg["detection"][k])
        for axis in ("pan", "tilt"):
            for k in ("deg_at_px_min", "deg_at_px_max"):
                doc["calibration"][axis][k] = int(round(cfg["calibration"][axis][k]))
        with open(CFG_PATH, "w") as f:
            ry.dump(doc, f)
        print("\n[kayıt] config.yaml güncellendi (ruamel: yorumlar korundu)")
    except ImportError:
        with open(CFG_PATH) as f:
            doc = yaml.safe_load(f)
        doc["detection"]["aim_pixel_offset_x"] = int(cfg["detection"]["aim_pixel_offset_x"])
        doc["detection"]["aim_pixel_offset_y"] = int(cfg["detection"]["aim_pixel_offset_y"])
        for axis in ("pan", "tilt"):
            for k in ("deg_at_px_min", "deg_at_px_max"):
                doc["calibration"][axis][k] = int(round(cfg["calibration"][axis][k]))
        with open(CFG_PATH, "w") as f:
            yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)
        print("\n[kayıt] config.yaml güncellendi (PyYAML: yorumlar kayboldu)")


def axis_state(cal_axis: dict):
    """deg_at_px_min/max'ten center + signed swing çıkarır."""
    a, b = cal_axis["deg_at_px_min"], cal_axis["deg_at_px_max"]
    center = (a + b) / 2.0
    swing = a - b  # işaretli; ana kalibrasyon yönü korunur
    return center, swing


def apply_swing(cal_axis: dict, center: float, swing: float, sv_min: int, sv_max: int):
    """center sabit, swing'e göre deg_at_px_min/max yeniden hesapla + kelepçele."""
    a = center + swing / 2.0
    b = center - swing / 2.0
    a = max(sv_min, min(sv_max, a))
    b = max(sv_min, min(sv_max, b))
    cal_axis["deg_at_px_min"] = a
    cal_axis["deg_at_px_max"] = b


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
    ctrl = Controller(cfg)  # self.cal = cfg["calibration"] referansı tutar

    aim_y_ratio = float(d.get("aim_y_offset_ratio", -0.2))
    laser_on = bool(cfg["servos"]["laser_always_on"])

    # Mutable referanslar — değiştirince controller anında etkilenir.
    d.setdefault("aim_pixel_offset_x", 0)
    d.setdefault("aim_pixel_offset_y", 0)

    pan_center, pan_swing = axis_state(cfg["calibration"]["pan"])
    tilt_center, tilt_swing = axis_state(cfg["calibration"]["tilt"])

    sv_pan = cfg["servos"]["pan"]
    sv_tilt = cfg["servos"]["tilt"]

    print(__doc__)
    print("birisi karenin TAM ORTASINDA dursun → önce a/d/w/x ile offseti oturtur.")
    print("sonra yana git → h/l ile pan swing'i, j/k ile tilt swing'i ayarla.\n")

    fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(fd)
    last_status = 0.0
    try:
        tty.setcbreak(fd)
        while True:
            frame = cam.read()
            if frame is None:
                continue

            t = det.detect(frame)
            if t is not None:
                aim_y = (t.cy + int(round(aim_y_ratio * t.h))
                         + d["aim_pixel_offset_y"])
                aim_x = t.cx + d["aim_pixel_offset_x"]
                cmd = ctrl.update((aim_x, aim_y))
            else:
                cmd = ctrl.update(None)
            link.send(cmd.pan, cmd.tilt, cmd.eye_x, cmd.eye_y, laser=laser_on)

            now = time.monotonic()
            if now - last_status >= 0.4:
                tag = "TARGET" if t is not None else " ----  "
                sys.stdout.write(
                    f"\rofs x={d['aim_pixel_offset_x']:+4d} "
                    f"y={d['aim_pixel_offset_y']:+4d}  "
                    f"swing pan={abs(pan_swing):5.1f}° tilt={abs(tilt_swing):5.1f}°  "
                    f"[{tag}]   "
                )
                sys.stdout.flush()
                last_status = now

            if not select.select([sys.stdin], [], [], 0)[0]:
                continue
            c = sys.stdin.read(1)
            off_small, off_big = 2, 10
            sw_small, sw_big = 1.0, 5.0

            if   c == 'a': d["aim_pixel_offset_x"] -= off_small
            elif c == 'd': d["aim_pixel_offset_x"] += off_small
            elif c == 'w': d["aim_pixel_offset_y"] -= off_small
            elif c == 'x': d["aim_pixel_offset_y"] += off_small
            elif c == 'A': d["aim_pixel_offset_x"] -= off_big
            elif c == 'D': d["aim_pixel_offset_x"] += off_big
            elif c == 'W': d["aim_pixel_offset_y"] -= off_big
            elif c == 'X': d["aim_pixel_offset_y"] += off_big

            elif c in ('h', 'H', 'l', 'L'):
                step = sw_big if c.isupper() else sw_small
                # 'h' azalt = swing |küçült|; 'l' artır
                sign = 1.0 if pan_swing >= 0 else -1.0
                mag = abs(pan_swing) + (-step if c in ('h','H') else step)
                mag = max(5.0, min(180.0, mag))
                pan_swing = sign * mag
                apply_swing(cfg["calibration"]["pan"], pan_center, pan_swing,
                            sv_pan["min"], sv_pan["max"])
            elif c in ('j', 'J', 'k', 'K'):
                step = sw_big if c.isupper() else sw_small
                sign = 1.0 if tilt_swing >= 0 else -1.0
                mag = abs(tilt_swing) + (-step if c in ('j','J') else step)
                mag = max(5.0, min(180.0, mag))
                tilt_swing = sign * mag
                apply_swing(cfg["calibration"]["tilt"], tilt_center, tilt_swing,
                            sv_tilt["min"], sv_tilt["max"])

            elif c == 'r':
                d["aim_pixel_offset_x"] = 0
                d["aim_pixel_offset_y"] = 0
                print(f"\n[reset] offset 0,0  (swing'ler aynı kaldı)")
            elif c == 'p':
                print(f"\n[durum] offset x={d['aim_pixel_offset_x']:+d} "
                      f"y={d['aim_pixel_offset_y']:+d}  "
                      f"pan_swing={abs(pan_swing):.1f}° "
                      f"tilt_swing={abs(tilt_swing):.1f}°  "
                      f"calibration.pan={cfg['calibration']['pan']}  "
                      f"calibration.tilt={cfg['calibration']['tilt']}")
            elif c == 's':
                save_all(cfg)
            elif c == 'q':
                print("\n[çıkış] kaydedilmedi.")
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
        cam.close()
        link.close()


if __name__ == "__main__":
    main()
