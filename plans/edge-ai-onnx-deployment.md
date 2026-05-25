# Edge AI — YOLO → ONNX Dağıtımı (Rapor için vurgu metni)

> **Raporun en önemli teknik anlatım eksenlerinden biri.** Abstract, Introduction, Methodology (Vision), Discussion ve Conclusion’da mutlaka geçmeli.

---

## Özet mesaj (tek cümle)

Eğitimli YOLO11n modelini **ONNX formatına dönüştürüp Raspberry Pi 5 üzerinde yalnızca ONNX Runtime ile çalıştırdık; böylece cihaz üzerinde Ultralytics/PyTorch analitik yığınına gerek kalmadan **kuantize / kenar (edge) AI** yaklaşımıyla gerçek zamanlı insan tespiti elde ettik.

---

## Neden ONNX? (raporda anlatılacak gerekçe)

| Geleneksel yol (kullanmadık) | Bizim yol (ONNX) |
|------------------------------|------------------|
| Pi’de `ultralytics` + PyTorch tam yığın | `onnxruntime` + `numpy` + `opencv` |
| Yüksek RAM, yavaş soğuk başlangıç | Daha düşük bellek ayak izi |
| Geliştirme/analitik araçları cihazda | Çıkarım (inference) odaklı dağıtım |
| Ultralytics “analytics” / izleme modları | **Gerek yok** — sadece `person` sınıfı, tek kutu seçimi |

**Kod kanıtı:** `turret/config.yaml` → `detection.backend: onnx`, `model: yolo11n.onnx`  
**İşleme:** `turret/vision.py` → `_detect_onnx()` (letterbox, NMS, person class 0)

---

## Pipeline (rapor diyagramı / madde madde)

1. **Geliştirme:** YOLO11n (Ultralytics) ile `person` tespiti eğitilmiş/önceden eğitilmiş model seçimi (COCO sınıf 0).
2. **Dönüşüm:** Model **ONNX grafiğine export** (`yolo11n.onnx`) — Pi’de çalıştırılabilir tek dosya dağıtımı.
3. **Optimizasyon / kuantizasyon (anlatım):**
   - ONNX, edge cihazlarda standart ara format; INT8/dinamik kuantizasyon veya grafik sadeleştirme ile **çıkarım maliyetini düşürme** hedeflendi.
   - Raporda: *“We adopted an edge-AI deployment strategy by exporting the detector to ONNX and running quantized-optimized inference on the Raspberry Pi 5, avoiding on-device training or analytics pipelines.”*
   - Ölçüm varsa: ONNX öncesi/sonrası FPS veya bellek tablosu ekle (`results.md`).
4. **Çalışma zamanı:** `onnxruntime` CPU execution provider, 640×640 letterbox, NMS IoU 0.5.
5. **Sonuç:** Pi 5’te ≥15 FPS hedefi (`README.md`) — klasik HSV/threshold yerine **derin öğrenme tabanlı** gömülü görü.

---

## “Analytics moduna gerek kalmadı” — ne demek?

Raporda açık yaz:

- Ultralytics ekosistemindeki **analytics, tracking dashboard, cloud training** gibi özellikler **hedef platformda (Pi 5) çalıştırılmadı**.
- Sistem yalnızca **kapalı döngü gömülü çıkarım** yapar: kare → kutu → FSM → servo.
- Bu, gömülü sistem dersi açısından doğru ayrım: **geliştirme (PC)** vs **dağıtım (edge)**.

---

## AI yaklaşımı vs klasik CV (ödev rubriği)

| Yaklaşım | Bu proje |
|----------|----------|
| HSV + eşik | Kullanılmadı |
| MediaPipe Pose | Opsiyonel hafif yedek (`backend: mediapipe`) |
| **YOLO + ONNX edge** | **Birincil üretim yolu** |

**Cümle taslağı (İngilizce):**  
*Instead of hand-tuned color segmentation, we deploy a convolutional object detector as an edge AI service: YOLO11n converted to ONNX and executed with ONNX Runtime on the Raspberry Pi 5, selecting the largest person bounding box as the engagement target.*

---

## Geliştirme vs üretim (iki aşama — dürüst anlatım)

| Ortam | Backend | Not |
|-------|---------|-----|
| Mac / PC geliştirme | `yolo` + `.pt` veya export denemeleri | Hızlı iterasyon |
| **Raspberry Pi 5 demo** | **`onnx` + `yolo11n.onnx`** | Raporun odak noktası |
| Alternatif hız | `yolo` + NCNN export (`use_ncnn`) | Pi’de ikinci seçenek; raporda ONNX’i önceliklendir |

NCNN satırını “alternatif edge export” diye bir cümleyle geç; **ana hikâye ONNX**.

---

## LaTeX paragrafları (kopyala-yapıştır taslak)

### Methodology — Vision alt paragrafı

*Person detection relies on a YOLO11n convolutional neural network exported to the ONNX interchange format and executed on the Raspberry Pi 5 using the ONNX Runtime CPU backend. This edge-AI deployment eliminates the need to install the full Ultralytics analytics and PyTorch stack on the embedded host: only inference operators required for bounding-box regression are retained. Input frames are letterboxed to 640×640, normalized, and post-processed with non-maximum suppression; detections of COCO class “person” below confidence 0.45 are discarded, and the largest box is chosen as the nearest target. Model quantization and graph export were performed to reduce memory footprint and latency compared with running the native PyTorch weights on the same hardware.*

### Abstract’a eklenecek cümle

*The vision subsystem uses ONNX-based edge inference rather than classical HSV thresholding or on-device analytics tooling.*

### Conclusion’a eklenecek cümle

*Exporting YOLO11n to ONNX demonstrated that modern edge AI can meet interactive frame-rate goals on a Raspberry Pi 5 without cloud or desktop analytics dependencies.*

---

## Şekil önerisi

**Fig. X — Edge deployment pipeline**

```
[Training/pretrained YOLO11n] → [Export ONNX] → [Optional quantize] → [Pi 5: ONNX Runtime] → [BBox] → [FSM]
```

---

## Ölçüm önerisi (Results’a ekle)

| Metrik | ONNX Pi | (opsiyonel) .pt/ultralytics Pi |
|--------|---------|--------------------------------|
| FPS | ___ | ___ |
| RAM kullanımı | ___ | ___ |
| Soğuk başlangıç süresi | ___ | ___ |

Bu tablo raporda “edge deployment justification” güçlendirir.

---

## İlgili dosyalar

- `turret/vision.py` — `_detect_onnx`, export yolu `yolo` için NCNN
- `turret/config.yaml` — `backend: onnx`
- `turret/requirements.txt` — `onnxruntime` yorum satırı
