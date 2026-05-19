"""Hızlı tespit testi — bilgisayarın kendi kamerasından (Arduino/Pi YOK).

Sadece kamera + YOLO insan tespiti + kutu/FPS çizimi. Mac/PC'de modelin
çalıştığını doğrulamak için. Çıkış: 'q'.

Kullanım:
  python3 detect_test.py            # webcam 0, yolo11n
  python3 detect_test.py 1          # webcam index 1
"""

from __future__ import annotations

import sys
import time

import cv2
from ultralytics import YOLO


def main():
    cam_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    print("[test] model yükleniyor (ilk sefer otomatik indirilir)...")
    model = YOLO("yolo11n.pt")

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"[hata] kamera açılamadı (index {cam_index}). "
              f"Mac'te: Sistem Ayarları > Gizlilik > Kamera'dan Terminal'e izin ver.")
        return 1
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    t0, frames = time.monotonic(), 0
    fps = 0.0
    print("[test] çalışıyor — pencerede 'q' ile çık")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[hata] kare alınamadı")
            break

        # sadece 'person' (COCO sınıf 0)
        res = model.predict(frame, conf=0.45, classes=[0], verbose=False)
        best = None
        for r in res:
            if r.boxes is None:
                continue
            for b in r.boxes:
                x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
                area = (x2 - x1) * (y2 - y1)
                if best is None or area > best[4]:
                    best = (x1, y1, x2, y2, area, float(b.conf[0]))
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 255), 1)

        if best:
            x1, y1, x2, y2, _, cf = best
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"HEDEF {cf:.2f}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        frames += 1
        if time.monotonic() - t0 >= 1.0:
            fps = frames / (time.monotonic() - t0)
            frames, t0 = 0, time.monotonic()
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("detect_test (q = cik)", frame)
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
