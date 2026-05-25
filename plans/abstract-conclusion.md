# Abstract, Conclusion & Future Work

**Durum:** Faz 0 tamamlandı — LaTeX’e yapıştırılmaya hazır metinler aşağıda.  
**Konum:** `ReportLatex/turret_report.tex` içinde abstract/keywords zaten gömülü; conclusion Faz 1’de `\section{Conclusion}` doldurulacak.

---

## Abstract — FINAL (English, IEEE)

**Kelime sayısı:** ~149 (hedef 150 ±10)

This paper presents an embedded pan-tilt turret built by a four-member student team that detects and tracks persons on a Raspberry Pi 5 and offloads real-time servo actuation to an Arduino Uno R4. A fixed CSI camera captures 640×480 video; a YOLO11n detector is converted to ONNX and executed with ONNX Runtime using an edge-AI, quantization-oriented deployment that avoids on-device Ultralytics analytics or the full PyTorch stack. The microcontroller enforces slew-rate limits, mechanical bounds, and a 500 ms communication failsafe. A four-state finite-state machine debounces target acquisition and loss and triggers Portal-themed audio delivered via a custom HTTP stream to smartphones after loudspeaker drivers failed and replacements were unavailable in Kayseri, plus LED sequences when the target fills sufficient image area. Interactive calibration maps pixels to servo angles under fixed-camera, moving-head geometry. Section V reports detection-to-command latency, frame rate, and tracking success metrics from bench tests.

**IEEEkeywords (LaTeX’te kullanıldı):**  
Edge AI, ONNX, YOLO, embedded vision, pan-tilt platform, serial communication, failsafe, Raspberry Pi.

---

## Abstract — Türkçe (kapak / özet sayfası)

Dört kişilik ekip tarafından geliştirilen bu pan-tilt taret, Raspberry Pi 5 üzerinde insan tespiti yapar ve servo kontrolünü Arduino Uno R4’e devreder. YOLO11n modeli ONNX’e dönüştürülerek Pi üzerinde ONNX Runtime ile çalıştırılır; cihazda Ultralytics analytics veya tam PyTorch yığını kullanılmaz. Mikrodenetleyici slew-limit, mekanik sınırlar ve 500 ms seri failsafe sağlar. Hoparlör sürücü arızası ve Kayseri’de yedek parça bulunamaması nedeniyle Portal sesleri özel HTTP akışıyla telefonlara yönlendirilmiştir. Piksel–açı eşlemesi interaktif kalibrasyonla yapılır. Deneysel sonuçlar Bölüm V’te verilir.

---

## Conclusion — FINAL (English, for `\section{Conclusion}`)

We presented a dual-processor Portal-inspired turret developed by Hamza Tekin, Kerem Çatalbaş, Yusuf Emre Boyraz, and Yusuf Baki Demiryürek. Perception and high-level behavior run on a Raspberry Pi 5 with ONNX-based YOLO11n edge inference, eliminating the need for on-device analytics tooling or a discrete GPU. Deterministic PWM, slew limiting, and failsafe centering remain on an Arduino Uno R4 fed by a 115200 baud line-oriented protocol at up to 30 Hz. Fixed-camera geometry is addressed through calibrated pixel-to-angle mapping and optional aim offsets. When loudspeaker drivers failed and replacements could not be sourced quickly around Kayseri, a network audio script used team smartphones as speakers without blocking the vision loop. Bench campaigns in Section V quantify detection-to-command latency, sustained frame rate, and tracking success under our test conditions. The project demonstrates how edge AI export, electrical discipline, and supply-chain adaptation combine in resource-constrained embedded robotics.

**Not:** Sayıları Section V’den bir cümleyle ekle (ör. *“Mean latency was 142 ms at 18.2 FPS.”*) — Faz 3 ölçümünden sonra.

---

## Future Work (FINAL bullets → kısa paragraf)

Future work includes depth-aware engagement instead of bounding-box area heuristics, Kalman-based prediction to reduce perceived latency, closed-loop encoders on pan and tilt, and accelerator hardware (e.g., Coral or Hailo) for lower power inference. Multi-person selection policies, optional classical HSV pipelines for colored markers, ROS 2 telemetry for repeatable benchmarks, and a hardware laser interlock would further mature the platform while preserving the existing failsafe-oriented serial interface.

---

## Faz 0 checklist

- [x] Abstract ~150 kelime (ONNX, edge AI, telefon sesi, ekip implicit via “four-member”)
- [x] Keywords listesi
- [x] Conclusion taslağı (sayı yeri Section V’e referans)
- [x] Future work metni
- [x] `turret_report.tex` abstract gömülü
- [ ] Faz 3 sonrası: Conclusion’a tek cümlelik ölçüm özeti ekle

---

## Conclusion checklist (Faz 1 sonu)

- [x] Problem + mimari + ONNX + ses + ekip (conclusion draft)
- [ ] Bir sayısal sonuç cümlesi (Faz 3 gerekli)
- [x] Kısıt: tek baskın kişi, 2D nişan
- [x] 5–6 future work maddesi
