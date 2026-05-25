# Experimental Results — Rapor kaynağı (Section V)

**Durum:** Faz 0 tamamlandı (ölçüm altyapısı + rapor şablonu hazır).  
**Sayısal sonuçlar:** Faz 3 — Pi üzerinde `measure_results.py` çalıştırılınca doldurulacak.  
**Faz 1’e geçmeden önce:** Aşağıdaki “Hızlı ölçüm” adımlarını uygula veya en azından bir bench run yap.

---

## Faz 0’da hazırlanan araçlar

| Araç | Yol | Açıklama |
|------|-----|----------|
| Bench script | `turret/measure_results.py` | FPS, inference ms, latency trials → JSON + CSV |
| Latency CSV | `plans/data/latency.csv` | Trial tablosu (ölçüm sonrası dolar) |
| JSON özet | `plans/data/benchmark_run.json` | Son koşu metrikleri |
| Grafik | `plans/tools/plot_latency.py` | → `ReportLatex/fig_latency.png` |

### Hızlı ölçüm (Pi 5)

```bash
cd turret && source venv/bin/activate
# Vision + serial (Arduino bağlı):
python3 measure_results.py --seconds 60 --latency-trials 20
# Sadece vision (Arduino yok):
python3 measure_results.py --seconds 30 --no-serial

# Grafik (PC’de, CSV dolu olunca):
python3 plans/tools/plot_latency.py
```

Konsol çıktısındaki `=== SUMMARY ===` bloğunu bu dosyadaki tablolara yapıştır.

---

## Ödev metni vs bu proje

| Ödev örneği | Bu projede karşılığı |
|-------------|----------------------|
| “Sorted 45/50 balls” | **Tracking / lock success rate** (insan hedefi) |
| Latency motion → servo | **Detection-to-command latency** (ms) |

---

## Metrik tanımları (raporda aynen kullan)

### 1. Latency (zorunlu grafik — Fig. latency)

**Tanım:** İlk karede kişi tespit edildiği (FOV’a giriş) andan, pan veya tilt komutunun merkezden anlamlı şekilde ayrıldığı ilk `SerialLink.send()` anına kadar geçen süre (ms).

**Otomatik:** `measure_results.py` (yükselen kenar + |pan−center|>2° veya tilt).

**Rapor:** N ≥ 20 deneme, ortalama ± standart sapma, çubuk grafik.

| Trial | Latency (ms) | Not |
|-------|--------------|-----|
| 1–20 | *Faz 3 sonrası* | `plans/data/latency.csv` |
| **Mean** | ___ | |
| **Std** | ___ | |

---

### 2. Accuracy / success rate

**A — Durum makinesi (10’ar deneme önerilir):**

| Test | Geçiş kriteri | Sonuç |
|------|---------------|-------|
| FOV’a giriş | ACQUIRED → TRACKING ≤ ~1.1 s (`found_ms`) | __/10 |
| FOV’dan çıkış | LOST → SEARCHING + lost ses ~1 s | __/10 |
| Hızlı yeniden giriş | LOST → TRACKING (reacquire) | __/10 |

**Toplam state test:** __/30 → **___ %**

**B — Nişan doğruluğu (kalibrasyon sonrası, 20 deneme):**

Mesafe: ___ m, sabit duran hedef, lazer noktası vs göğüs hedefi (cm).

| Kriter | Sonuç |
|--------|-------|
| ±5 cm içinde isabet | __/20 → **___ %** |

**C — Tespit güvenilirliği:**

50 kare boyunca kişi görünür → kutu döndü: __/50 → **___ %**

---

### 3. Throughput (FPS) ve çıkarım

`measure_results.py` veya `main.py` + `debug.print_fps: true`:

| Metrik | Değer (Faz 3) | Hedef |
|--------|---------------|-------|
| End-to-end FPS | ___ | ≥ 15 |
| Inference mean (ms) | ___ | — |
| Inference p95 (ms) | ___ | — |
| Detection frame ratio | ___ % | — |

---

### 4. ONNX edge deployment (Tablo — rapor vurgusu)

| Dağıtım | FPS | Çıkarım ort. (ms) | Not |
|---------|-----|-------------------|-----|
| **ONNX + yolo11n.onnx (Pi 5)** | ___ | ___ | Üretim yolu |
| Ultralytics .pt (opsiyonel) | ___ | ___ | Karşılaştırma |

---

### 5. Seri / kontrol

| Metrik | Beklenen | Ölçülen |
|--------|----------|---------|
| Komut hızı | ~30 Hz | ___ |
| Failsafe (main durdur) | ~500 ms + slew | ___ |

---

## LaTeX — Results bölümü taslağı (Faz 1’de genişlet)

*Copy when numbers exist in `benchmark_run.json`.*

\subsection{Experimental Setup}
Tests were conducted on a Raspberry Pi~5 with Raspberry Pi OS Bookworm (64-bit), CSI camera at $640\times480$, and detection backend \texttt{onnx} with \texttt{yolo11n.onnx}. The Arduino Uno~R4 ran firmware \texttt{turret\_firmware.ino} at $115200$~baud. Servos used a separate $5$--$6$~V supply with common ground. Room lighting: [fill]. Standoff distance: [fill]~m.

\subsection{Latency}
Figure~\ref{fig:latency} shows detection-to-actuation latency over [N] trials (mean [X]$\pm$[Y]~ms).

\subsection{Tracking Performance}
State-machine tests passed [A]/30 trials ([P]\%). Aiming within $\pm5$~cm succeeded on [B]/20 trials ([Q]\%).

\subsection{Frame Rate and Inference}
The system sustained [FPS]~FPS mean end-to-end throughput; per-frame inference averaged [I]~ms (95th percentile [P95]~ms).

\subsection{Limitations}
Results assume a single dominant person in view; performance varies with lighting.

---

## Grafik özelliği

**Şekil başlığı:** *End-to-end latency from initial person detection to first corrective servo command.*

**Dosya:** `ReportLatex/fig_latency.png` (üretim: `plans/tools/plot_latency.py`)

---

## Deneysel kurulum notları (ölçüm günü doldur)

| Alan | Değer |
|------|-------|
| Aydınlatma | ___ |
| Mesafe (m) | ___ |
| `config.yaml` / git commit | ___ |
| Güç (servo V, A yük altında) | ___ |

---

## Faz 0 checklist

- [x] Metrik tanımları ve tablo şablonları
- [x] `measure_results.py` bench aracı
- [x] `latency.csv` + `plot_latency.py`
- [x] LaTeX Results subsection taslağı
- [ ] **Faz 3:** Gerçek sayılar toplandı → tablolar dolduruldu
- [ ] **Faz 2:** `fig_latency.png` üretildi
