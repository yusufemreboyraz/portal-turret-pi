"""Kamera yakalama + insan tespiti.

Camera: Pi 5 üzerinde picamera2 (CSI modül). picamera2 yoksa OpenCV
VideoCapture'a düşer (geliştirme/USB kamera için).

PersonDetector: ultralytics YOLO (varsayılan, Pi 5'te NCNN export ile hızlı)
veya MediaPipe (daha hafif fallback). En büyük insan kutusu hedef seçilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Target:
    cx: int          # kutu merkezi x (piksel)
    cy: int          # kutu merkezi y (piksel)
    w: int
    h: int
    conf: float

    @property
    def area(self) -> int:
        return self.w * self.h


# --------------------------------------------------------------------------- #
# Kamera
# --------------------------------------------------------------------------- #
class Camera:
    def __init__(self, width: int, height: int, fps: int = 30,
                 hflip: bool = False, vflip: bool = False):
        self.width = width
        self.height = height
        self.hflip = hflip
        self.vflip = vflip
        self._picam = None
        self._cv = None

        try:
            from picamera2 import Picamera2, controls  # type: ignore

            self._picam = Picamera2()
            cfg = self._picam.create_preview_configuration(
                main={"size": (width, height), "format": "RGB888"}
            )
            self._picam.configure(cfg)
            self._picam.start()
            try:
                self._picam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
            except Exception as e:
                print(f"[camera] Sürekli odaklama (AF) ayarlanamadı: {e}")
            print("[camera] picamera2 (CSI) aktif")
        except Exception as e:  # noqa: BLE001 - Pi dışında veya modül yoksa
            print(f"[camera] picamera2 yok ({e}); OpenCV VideoCapture deneniyor")
            import cv2

            self._cv = cv2.VideoCapture(0)
            self._cv.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._cv.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self._cv.set(cv2.CAP_PROP_FPS, fps)
            if not self._cv.isOpened():
                raise RuntimeError("Hiçbir kamera açılamadı (CSI ve USB başarısız)")

    def read(self) -> Optional[np.ndarray]:
        """BGR (OpenCV uyumlu) bir kare döndürür, hata varsa None."""
        if self._picam is not None:
            frame = self._picam.capture_array()  # RGB
            frame = frame[:, :, ::-1].copy()     # -> BGR
        else:
            import cv2

            ok, frame = self._cv.read()
            if not ok:
                return None

        if self.hflip:
            frame = frame[:, ::-1]
        if self.vflip:
            frame = frame[::-1, :]
        return np.ascontiguousarray(frame)

    def close(self):
        if self._picam is not None:
            self._picam.stop()
        if self._cv is not None:
            self._cv.release()


# --------------------------------------------------------------------------- #
# Tespit
# --------------------------------------------------------------------------- #
class PersonDetector:
    def __init__(self, backend: str = "yolo", model: str = "yolo11n.pt",
                 use_ncnn: bool = True, conf: float = 0.45,
                 person_class_id: int = 0):
        self.backend = backend
        self.conf = conf
        self.person_class_id = person_class_id

        if backend == "yolo":
            from ultralytics import YOLO

            mdl = YOLO(model)
            if use_ncnn:
                # İlk seferde NCNN'e export et (Pi 5'te ~2x hız), sonra onu yükle.
                try:
                    export_dir = model.replace(".pt", "_ncnn_model")
                    import os

                    if not os.path.isdir(export_dir):
                        print("[detect] YOLO NCNN'e export ediliyor (ilk sefer, biraz sürer)...")
                        mdl.export(format="ncnn")
                    mdl = YOLO(export_dir)
                    print("[detect] YOLO NCNN modeli yüklendi")
                except Exception as e:  # noqa: BLE001
                    print(f"[detect] NCNN export başarısız ({e}); .pt ile devam")
            self._yolo = mdl

        elif backend == "mediapipe":
            import mediapipe as mp

            self._mp = mp.solutions.pose.Pose(
                model_complexity=0, min_detection_confidence=conf
            )
        else:
            raise ValueError(f"Bilinmeyen backend: {backend}")

    def detect(self, frame: np.ndarray) -> Optional[Target]:
        """En büyük (en yakın) insanı döndürür, yoksa None."""
        if self.backend == "yolo":
            return self._detect_yolo(frame)
        return self._detect_mediapipe(frame)

    def _detect_yolo(self, frame: np.ndarray) -> Optional[Target]:
        res = self._yolo.predict(
            frame, conf=self.conf, classes=[self.person_class_id],
            verbose=False
        )
        best: Optional[Target] = None
        for r in res:
            if r.boxes is None:
                continue
            for b in r.boxes:
                x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
                w, h = int(x2 - x1), int(y2 - y1)
                t = Target(int((x1 + x2) / 2), int((y1 + y2) / 2),
                           w, h, float(b.conf[0]))
                if best is None or t.area > best.area:
                    best = t
        return best

    def _detect_mediapipe(self, frame: np.ndarray) -> Optional[Target]:
        res = self._mp.process(frame[:, :, ::-1])  # MediaPipe RGB ister
        if not res.pose_landmarks:
            return None
        h, w = frame.shape[:2]
        xs = [lm.x * w for lm in res.pose_landmarks.landmark]
        ys = [lm.y * h for lm in res.pose_landmarks.landmark]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        return Target(int((x1 + x2) / 2), int((y1 + y2) / 2),
                      int(x2 - x1), int(y2 - y1), 1.0)
