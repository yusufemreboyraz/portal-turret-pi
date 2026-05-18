"""İnteraktif kalibrasyon — kamera pikseli <-> servo açısı eşlemesi.

Kamera sabit, silah hareketli olduğundan bu eşleme şart. Yöntem:
  1. Servoları klavyeyle oynat, lazer noktasını fiziksel bir yere getir.
  2. O lazer noktasının kamera görüntüsündeki yerine FARE ile tıkla.
  3. Bu, (tıklanan piksel) <-> (mevcut servo açısı) çifti olarak kaydedilir.
  4. Pan için solda+sağda, tilt için üstte+altta ikişer nokta topla.
  5. 's' ile çöz ve config.yaml'ın 'calibration' bölümüne yaz (yorumlar korunur).

Tuşlar:
  a/d : pan -/+        w/s : tilt -/+        (Shift ile büyük adım)
  [   : pan extremlerinden birini "aktif eksen" yap (otomatik; sırayla tıkla)
  fare sol tık : mevcut açıda hedef pikselini kaydet
  u   : son kaydı geri al
  S   : çöz + config.yaml'a yaz
  c   : servoları merkeze al
  q   : çık (kaydetmeden)
"""

from __future__ import annotations

import os
import sys

import cv2
import yaml

from serial_link import SerialLink
from vision import Camera

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "config.yaml")


def load_cfg():
    with open(CFG_PATH) as f:
        return yaml.safe_load(f)


def solve_axis(samples):
    """samples: [(px, deg), ...] -> en uç iki noktadan doğrusal eşleme."""
    samples = sorted(samples, key=lambda s: s[0])
    (px_min, d_min) = samples[0]
    (px_max, d_max) = samples[-1]
    return {
        "px_min": int(px_min),
        "px_max": int(px_max),
        "deg_at_px_min": int(round(d_min)),
        "deg_at_px_max": int(round(d_max)),
    }


def write_calibration(pan_axis, tilt_axis):
    """config.yaml'ın sadece calibration bölümünü günceller (yorumlar korunur)."""
    try:
        from ruamel.yaml import YAML

        ry = YAML()
        ry.preserve_quotes = True
        with open(CFG_PATH) as f:
            doc = ry.load(f)
        doc["calibration"]["pan"].update(pan_axis)
        doc["calibration"]["tilt"].update(tilt_axis)
        with open(CFG_PATH, "w") as f:
            ry.dump(doc, f)
        print("[calib] config.yaml güncellendi (yorumlar korundu)")
    except ImportError:
        # ruamel yoksa PyYAML ile yeniden yaz (yorumlar kaybolur).
        cfg = load_cfg()
        cfg["calibration"]["pan"] = pan_axis
        cfg["calibration"]["tilt"] = tilt_axis
        with open(CFG_PATH, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
        print("[calib] config.yaml güncellendi (ruamel yok -> yorumlar kayboldu)")


def main():
    cfg = load_cfg()
    cam = Camera(cfg["camera"]["width"], cfg["camera"]["height"],
                 cfg["camera"]["fps"], cfg["camera"]["hflip"],
                 cfg["camera"]["vflip"])
    link = SerialLink(cfg["serial"]["port"], cfg["serial"]["baud"],
                      cfg["serial"]["command_hz"],
                      cfg["serial"]["reconnect_delay_s"])

    s = cfg["servos"]
    pan = float(s["pan"]["center"])
    tilt = float(s["tilt"]["center"])
    eye_c_x = s["eye_x"]["center"]
    eye_c_y = s["eye_y"]["center"]

    pan_samples: list[tuple[int, float]] = []
    tilt_samples: list[tuple[int, float]] = []
    last_click = {"xy": None}

    def on_mouse(event, x, y, flags, _):
        if event == cv2.EVENT_LBUTTONDOWN:
            pan_samples.append((x, pan))
            tilt_samples.append((y, tilt))
            last_click["xy"] = (x, y)
            print(f"[calib] kayıt: px=({x},{y})  pan={pan:.0f} tilt={tilt:.0f}  "
                  f"(toplam {len(pan_samples)})")

    cv2.namedWindow("calibrate")
    cv2.setMouseCallback("calibrate", on_mouse)
    print(__doc__)

    while True:
        frame = cam.read()
        if frame is None:
            continue
        link.send(int(pan), int(tilt), eye_c_x, eye_c_y, laser=True, force=True)

        h, w = frame.shape[:2]
        cv2.drawMarker(frame, (w // 2, h // 2), (0, 255, 0),
                       cv2.MARKER_CROSS, 20, 1)
        if last_click["xy"]:
            cv2.circle(frame, last_click["xy"], 6, (0, 0, 255), 2)
        cv2.putText(frame, f"pan={pan:.0f} tilt={tilt:.0f} "
                    f"pts={len(pan_samples)}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow("calibrate", frame)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("a"):
            pan -= 1
        elif k == ord("d"):
            pan += 1
        elif k == ord("A"):
            pan -= 8
        elif k == ord("D"):
            pan += 8
        elif k == ord("w"):
            tilt -= 1
        elif k == ord("s"):
            tilt += 1
        elif k == ord("W"):
            tilt -= 8
        elif k == ord("X"):
            tilt += 8
        elif k == ord("c"):
            pan, tilt = float(s["pan"]["center"]), float(s["tilt"]["center"])
        elif k == ord("u") and pan_samples:
            pan_samples.pop()
            tilt_samples.pop()
            print(f"[calib] geri alındı (kalan {len(pan_samples)})")
        elif k == ord("S"):
            if len(pan_samples) < 2:
                print("[calib] en az 2 nokta gerekli (uçlardan).")
                continue
            write_calibration(solve_axis(pan_samples), solve_axis(tilt_samples))
            break
        elif k == ord("q"):
            print("[calib] kaydetmeden çıkıldı")
            break

        pan = max(s["pan"]["min"], min(s["pan"]["max"], pan))
        tilt = max(s["tilt"]["min"], min(s["tilt"]["max"], tilt))

    cam.close()
    link.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())
