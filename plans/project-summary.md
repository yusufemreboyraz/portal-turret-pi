# Portal Turret — Proje Özeti (Rapor için tek kaynak)

## Ne yapıyor?

Valve *Portal* oyunundaki otonom turret’in modern bir donanım klonu:

- **Raspberry Pi 5:** CSI kamera, insan tespiti (derin öğrenme), durum makinesi, ses, Arduino’ya servo komutları
- **Arduino Uno R4:** 4 servo (pan, tilt, 2× göz), lazer, 4× namlu LED; slew-rate + failsafe
- **Davranış:** İnsan görülünce takip; Portal `.wav` replikleri; hedef yeterince büyükse “ateş” (ses + LED koreografisi, lazer sürekli yanık)

Eski 2013–2014 Instructables/Windows kodu **kullanılmadı**; sadece zamanlayıcı mantığı (found/lost/reacquire) ve ses fikri yeniden yazıldı (`README.md`).

**Ekip (4 kişi):** Hamza Tekin, Kerem Çatalbaş, Yusuf Emre Boyraz, Yusuf Baki Demiryürek — ayrıntılı görevler: `team-and-contributions.md`.

**Teknik öne çıkanlar:**
- **Edge AI:** YOLO11n → ONNX, Pi 5’te ONNX Runtime; analytics/PyTorch yığını cihazda yok (`edge-ai-onnx-deployment.md`)
- **Ses:** Hoparlör driver arızası + Kayseri’de yedek bulunamayınca telefon hoparlör script’i (`methodology-audio.md`)

---

## Dizin yapısı

```
Turret/
├── turret/          # Pi Python uygulaması
│   ├── main.py      # Orkestratör + FSM
│   ├── vision.py    # Kamera + PersonDetector
│   ├── controller.py# Piksel→açı + smoothing
│   ├── serial_link.py
│   ├── config.yaml
│   ├── calibrate.py / calibrate_aim.py
│   └── sounds/      # Portal wav (git’te olmayabilir)
├── arduino/
│   ├── turret_firmware/turret_firmware.ino
│   └── led_test/led_test.ino
└── ReportLatex/     # IEEE şablonu
```

---

## Donanım özeti

| Bileşen | Model / not |
|---------|-------------|
| Bilgisayar | Raspberry Pi 5 (8 GB önerilir) |
| MCU | Arduino Uno R4 (Minima/WiFi) |
| Kamera | Pi CSI modülü (`picamera2`) |
| Pan/Tilt | 2× MG996R |
| Göz | 2× SG90 sınıfı |
| Lazer | Dijital pin 7, sürekli mod |
| LED | 4× namlu LED (pin 2,3,12,13 + 470Ω) |
| Ses | **Network modu (telefon hoparlör)** — driver arızası sonrası ekip çözümü; USB/pygame yedek |
| Seri | USB `115200` baud, `/dev/ttyACM0` |

**Güç (kritik):** Servolar **ayrı 5–6 V ≥6 A** kaynak; Arduino 5V’den servo beslenmez. Ortak GND zorunlu.

---

## Yazılım pipeline (her frame)

1. `Camera.read()` → BGR 640×480 @ 30 FPS hedef
2. `PersonDetector.detect()` → en büyük `person` kutusu (`Target`)
3. FSM (`main.py`): SEARCHING → ACQUIRED → TRACKING → LOST
4. Nişan: kutu merkezi + `aim_y_offset_ratio` + piksel ofset
5. `Controller.update()` → pan/tilt/eye açıları (kalibrasyon + low-pass + slew)
6. `SerialLink.send()` → `T,pan,tilt,eyeX,eyeY,laser\n` max 30 Hz
7. Arduino: slew 3°/15 ms, failsafe 500 ms, LED `F` komutu

---

## Tespit backend’leri (config)

| Backend | Kullanım | Bağımlılık |
|---------|----------|------------|
| `onnx` | **Pi 5 üretim — raporun ana hikâyesi** | YOLO→ONNX export, onnxruntime, kuantize edge AI |
| `yolo` | Mac geliştirme / export | ultralytics; Pi’de analytics modu **gerekmez** |
| `mediapipe` | Hafif fallback | mediapipe pose |

**HSV / renk eşiği yok** — raporda **ONNX edge AI** vurgula (`edge-ai-onnx-deployment.md`).

---

## Durum makinesi (kısa)

| Durum | Anlam |
|-------|--------|
| `SEARCHING` | Hedef yok; merkez / idle scan |
| `TARGET_ACQUIRED` | İnsan görüldü; `found_ms` (1000 ms) sonra TRACKING |
| `TRACKING` | Sürekli takip; bbox oranı ≥0.4 → lock sesi + `F` |
| `TARGET_LOST` | Kayıp; `lost_ms` sonra SEARCHING + lost sesi |

`reacquire_ms`: LOST iken hemen tekrar görülürse TRACKING’e dön.

---

## Kalibrasyon (rapor Methodology)

- **calibrate.py:** Sabit kamera + hareketli silah → fare tıklaması ile (piksel, servo açısı) çiftleri → `calibration.pan/tilt` doğrusal eşleme
- **calibrate_aim.py:** Lazer–kamera paralaks ofseti (`aim_pixel_offset_*`) ve swing kazancı

---

## Güvenlik

- Arduino **failsafe:** 500 ms komut yok → merkez + lazer kapalı
- Firmware **clamp:** PAN/TILT/EYE min-max (`limitsOn`, `L,1`)
- Pi kapanışında merkez komutu + `laser=False`

---

## Doğrulama checklist (README)

- Servo kaynağı yük altında ≥4.8 V
- `serial_test.py` failsafe
- FPS ≥ 15, insan kutusu
- Kalibrasyon sonrası lazer ±birkaç cm
- Kişi gir/çık → doğru sesler

---

## Ödev rubriği ile eşleme

| Rubrik maddesi | Bu projede karşılığı |
|----------------|----------------------|
| Vision / HSV | YOLO11n ONNX + opsiyonel MediaPipe (HSV yok) |
| Control / FSM | `main.py` 4 durum + `controller.py` smoothing |
| Communication | `T,...` satır protokolü, 115200 baud |
| Results / balls | **İnsan takibi:** lock oranı, latency, FPS (top yok) |
| Discussion | Güç, aydınlatma, seri gecikme, kalibrasyon |
