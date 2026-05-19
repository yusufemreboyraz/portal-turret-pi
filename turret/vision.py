"""Kamera yakalama + insan tespiti.

Camera: Pi 5 üzerinde picamera2 (CSI modül). picamera2 yoksa OpenCV
VideoCapture'a düşer (geliştirme/USB kamera için).

PersonDetector: ultralytics YOLO (varsayılan, Pi 5'te NCNN export ile hızlı)
veya MediaPipe (daha hafif fallback). En büyük insan kutusu hedef seçilir.
"""

from __future__ import annotations

import os
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
            import cv2
            
            # model uzantısını zorla .onnx yapıyoruz (eğer .pt girildiyse)
            onnx_model = model.replace(".pt", ".onnx")
            
            if not os.path.exists(onnx_model):
                print(f"[detect] UYARI: {onnx_model} bulunamadı!")
                print("[detect] Lütfen bilgisayarınızda 'yolo export model=yolo11n.pt format=onnx' komutunu çalıştırıp")
                print(f"[detect] oluşan .onnx dosyasını Raspberry Pi'ye ({onnx_model}) kopyalayın.")
                
            try:
                self._net = cv2.dnn.readNetFromONNX(onnx_model)
                print(f"[detect] OpenCV DNN ile {onnx_model} yüklendi. (Ultralytics kullanılmıyor)")
            except Exception as e:
                print(f"[detect] ONNX modeli yüklenirken hata oluştu: {e}")
                self._net = None
                
            self._input_size = (640, 640)  # YOLO varsayılan giriş boyutu

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
        if getattr(self, "_net", None) is None:
            return None
            
        import cv2
        import numpy as np
        
        orig_h, orig_w = frame.shape[:2]
        
        # 1. Letterbox resize (görüntü oranını bozmadan 640x640'a sığdır)
        ratio = min(self._input_size[0] / orig_w, self._input_size[1] / orig_h)
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        dw = (self._input_size[0] - new_w) / 2
        dh = (self._input_size[1] - new_h) / 2
        
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        
        img = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        
        # 2. OpenCV DNN forward
        blob = cv2.dnn.blobFromImage(img, 1 / 255.0, self._input_size, swapRB=True, crop=False)
        self._net.setInput(blob)
        preds = self._net.forward()  # YOLOv8/11 çıktısı genelde (1, 84, 8400)
        
        preds = preds[0]  # shape: (84, 8400)
        if preds.shape[0] > preds.shape[1]:
            preds = preds.T
            
        # 3. İnsan sınıfı (person_class_id genelde 0) olasılıkları
        class_scores = preds[4 + self.person_class_id, :]
        valid_indices = np.where(class_scores > self.conf)[0]
        
        boxes = []
        confidences = []
        
        for idx in valid_indices:
            score = class_scores[idx]
            xc, yc, w, h = preds[0:4, idx]
            
            # Orijinal resim boyutlarına geri ölçekle
            xc = (xc - dw) / ratio
            yc = (yc - dh) / ratio
            w = w / ratio
            h = h / ratio
            
            x1 = xc - w / 2
            y1 = yc - h / 2
            
            boxes.append([int(x1), int(y1), int(w), int(h)])
            confidences.append(float(score))
            
        best: Optional[Target] = None
        if len(boxes) > 0:
            # Non-Maximum Suppression (Üst üste binen kutuları ele)
            indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf, 0.45)
            if len(indices) > 0:
                for i in indices.flatten():
                    x, y, w, h = boxes[i]
                    t = Target(int(x + w/2), int(y + h/2), int(w), int(h), confidences[i])
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
