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
            from picamera2 import Picamera2  # type: ignore

            self._picam = Picamera2()
            cfg = self._picam.create_preview_configuration(
                main={"size": (width, height), "format": "RGB888"}
            )
            self._picam.configure(cfg)
            self._picam.start()
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

        elif backend == "onnx":
            # ultralytics/torch gerekmez; sadece onnxruntime + numpy + cv2.
            # Pi 5 için ideal (kurulum hafif, RAM az, hız iyi).
            import onnxruntime as ort
            import os

            path = model
            if not os.path.isabs(path):
                here = os.path.dirname(os.path.abspath(__file__))
                cand = os.path.join(here, path)
                if os.path.isfile(cand):
                    path = cand
            if not os.path.isfile(path):
                raise FileNotFoundError(f"ONNX modeli bulunamadı: {model}")

            self._ort = ort.InferenceSession(
                path, providers=["CPUExecutionProvider"]
            )
            inp = self._ort.get_inputs()[0]
            self._ort_input = inp.name
            # Beklenen şekil: [1, 3, H, W]; YOLO11n için 640x640.
            shape = inp.shape
            self._img_size = int(shape[2]) if isinstance(shape[2], int) else 640
            print(f"[detect] ONNX modeli yüklendi: {path}  giriş={self._img_size}")

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
        if self.backend == "onnx":
            return self._detect_onnx(frame)
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

    # -- ONNX (ultralytics-bağımsız) --
    def _letterbox(self, im: np.ndarray, new_size: int):
        import cv2
        h, w = im.shape[:2]
        r = min(new_size / h, new_size / w)
        nw, nh = int(round(w * r)), int(round(h * r))
        pad_w = (new_size - nw) // 2
        pad_h = (new_size - nh) // 2
        resized = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((new_size, new_size, 3), 114, dtype=np.uint8)
        canvas[pad_h:pad_h + nh, pad_w:pad_w + nw] = resized
        return canvas, r, pad_w, pad_h

    @staticmethod
    def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float = 0.5):
        # boxes: [N,4] xyxy
        if boxes.size == 0:
            return []
        x1, y1, x2, y2 = boxes.T
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(int(i))
            if order.size == 1:
                break
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.clip(xx2 - xx1, 0, None)
            h = np.clip(yy2 - yy1, 0, None)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
            order = order[1:][iou < iou_thr]
        return keep

    def _detect_onnx(self, frame: np.ndarray) -> Optional[Target]:
        size = self._img_size
        img, r, pad_w, pad_h = self._letterbox(frame, size)
        x = img[:, :, ::-1].astype(np.float32) / 255.0   # BGR->RGB, [0,1]
        x = np.ascontiguousarray(x.transpose(2, 0, 1)[None])  # 1,3,H,W

        out = self._ort.run(None, {self._ort_input: x})[0]   # genelde [1,84,N]
        pred = out[0]
        # Bazı export'larda [N,84] olabilir; 84 ekseni dış olsun.
        if pred.shape[0] != 84 and pred.shape[1] == 84:
            pred = pred.T
        boxes_xywh = pred[:4].T            # [N,4] (cx,cy,w,h) — 640 uzayında
        cls_scores = pred[4:].T            # [N, num_classes]
        cls_id = cls_scores.argmax(axis=1)
        conf = cls_scores.max(axis=1)

        m = (cls_id == self.person_class_id) & (conf >= self.conf)
        if not m.any():
            return None
        bxywh = boxes_xywh[m]
        conf = conf[m]
        cx, cy, bw, bh = bxywh[:, 0], bxywh[:, 1], bxywh[:, 2], bxywh[:, 3]
        x1 = cx - bw / 2; y1 = cy - bh / 2
        x2 = cx + bw / 2; y2 = cy + bh / 2
        keep = self._nms(np.stack([x1, y1, x2, y2], axis=1), conf, 0.5)
        if not keep:
            return None
        # En büyük kutu = en yakın hedef
        best = max(keep, key=lambda i: (x2[i] - x1[i]) * (y2[i] - y1[i]))
        # Letterbox geri al: orijinal kare koordinatlarına ölçekle
        bx1 = (x1[best] - pad_w) / r
        by1 = (y1[best] - pad_h) / r
        bx2 = (x2[best] - pad_w) / r
        by2 = (y2[best] - pad_h) / r
        return Target(
            int((bx1 + bx2) / 2), int((by1 + by2) / 2),
            int(bx2 - bx1), int(by2 - by1), float(conf[best]),
        )

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
