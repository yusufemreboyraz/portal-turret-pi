# Portal Turret — Akademik Rapor Ana Planı

Bu dosya, `ReportLatex/bare_jrnl_new_sample4.tex` (IEEEtran) şablonunu kullanarak raporu **adım adım** yazman için ana yol haritasıdır. Her adımda ilgili `plans/*.md` dosyasına bak; tekrar tüm kodu okutmak gerekmez.

---

## Ön koşullar

| Öğe | Konum |
|-----|--------|
| LaTeX şablonu | `ReportLatex/bare_jrnl_new_sample4.tex` |
| IEEE nasıl yazılır | `ReportLatex/New_IEEEtran_how-to.pdf` |
| Proje özeti (tek kaynak) | `plans/project-summary.md` |
| **ONNX / edge AI (zorunlu vurgu)** | `plans/edge-ai-onnx-deployment.md` |
| Telefon hoparlör / ses | `plans/methodology-audio.md` |
| Ekip ve katkılar | `plans/team-and-contributions.md` |
| Donanım / kablolama | `README.md` |

**Önemli:** Bu proje **top sıralama (ball sorting) değil**; Raspberry Pi 5 + Arduino ile **insan takibi yapan Portal turret**. Ödev metnindeki HSV/top örnekleri genel şablondur; senin sistemin **YOLO11n / ONNX / (opsiyonel) MediaPipe** kullanır — HSV yok (`plans/methodology-vision.md`).

---

## Faz 0 — Hazırlık (1 oturum) ✅ TAMAMLANDI (2026-05-25)

- [x] `bare_jrnl_new_sample4.tex` kopyalandı → `ReportLatex/turret_report.tex` (sample dokunulmadı)
- [x] Başlık, **dört yazar**, thanks, Acknowledgments — `team-and-contributions.md` + `turret_report.tex`
- [ ] **Senin yapman gereken:** `turret_report.tex` içinde `[Institution Name]` ve hoca/bölüm adını düzelt
- [x] `IEEEkeywords` eklendi (edge AI, ONNX, …)
- [x] Abstract (~149 kelime): ONNX, telefon sesi/Kayseri, edge AI — `abstract-conclusion.md` + `turret_report.tex`
- [x] Ölçüm altyapısı: `turret/measure_results.py`, `plans/data/latency.csv`, `plans/tools/plot_latency.py` — `results.md`
TAMAMLANDI
---

## Faz 1 — Taslak bölümler (sırayla LaTeX’e aktar)

| Sıra | IEEE bölümü | Kaynak MD | Tahmini süre |
|------|-------------|-----------|--------------|
| 1 | **Abstract** (~150 kelime) | `abstract-conclusion.md` | 30 dk |
| 2 | **Introduction** | `intro.md` | 1 saat |
| 3 | **System Architecture** | `architecture.md` | 1 saat + diyagram |
| 4 | **Methodology** (vision + audio + control + comm) | `edge-ai-onnx-deployment.md`, `methodology-vision.md`, `methodology-audio.md`, `methodology-control.md`, `methodology-communication.md` | 2–3 saat |
| 5 | **Experimental Results** | `results.md` | 2 saat + ölçüm |
| 6 | **Discussion** | `discussion.md` | 1 saat |
| 7 | **Conclusion & Future Work** | `abstract-conclusion.md` | 30 dk |
| 8 | **References** | `references.md` | 45 dk |

Her bölüm bittiğinde: `\cite{}` yer tutucularını gerçek referanslarla değiştir.

---

## Faz 2 — Şekiller ve tablolar

- [x] **Şekil 1:** Sistem blok diyagramı (Pi ↔ Arduino ↔ servolar) — `ReportLatex/fig_architecture.png`
- [x] **Şekil 2:** Durum makinesi — `ReportLatex/fig_fsm.png`
- [x] **Şekil 3:** Seri paket zaman çizelgesi — `ReportLatex/fig_serial.png`
- [x] **Şekil 4:** Latency grafiği — `ReportLatex/fig_latency_estimate.png` (preliminary estimate; gerçek ölçüm değil)
- [x] **Tablo 1:** Donanım listesi — `turret_report.tex` içinde Table~\ref{tab:hardware}
- [x] **Tablo 2:** `config.yaml` zamanlayıcıları ve servo limitleri — `turret_report.tex` içinde Table~\ref{tab:config}

---

## Faz 3 — Deneyleri çalıştır (Results için zorunlu)

`results.md` içindeki checklist’i uygula. Minimum:

**Durum (2026-05-29):** Gerçek donanım testleri çalıştırılamadığı için `turret_report.tex` Section~V içinde preliminary engineering estimates kullanıldı. Gerçek bench çıktısı geldiğinde `plans/data/latency.csv`, `plans/data/benchmark_run.json` ve `ReportLatex/fig_latency_estimate.png` yerine ölçüm tabanlı grafik/metin güncellenmeli.

1. **Latency:** hareket algısı → ilk servo komutu (ms), N≥20 ölçüm
2. **Takip doğruluğu:** sabit mesafede X deneme, lazer/hedef hizası (piksel veya cm)
3. **Durum makinesi:** found / lost / reacquire süreleri config ile uyumlu mu
4. **FPS:** `main.py` + `print_fps: true` → hedef ≥15 FPS (README)

Ölçüm yoksa Results bölümünde **“ölçüm planı + beklenen aralık”** yazma; gerçek sayı topla.

---

## Faz 4 — AI / editör ile LaTeX yazdırma

Cursor’a her seferinde şunu ver:

```
ReportLatex/turret_report.tex dosyasına şu bölümü ekle.
Kaynak: plans/<dosya>.md
IEEEtran formatında, akademik İngilizce (veya Türkçe isteniyorsa belirt).
Mevcut makale stiline uy.
```

Önerilen sıra: Abstract → Intro → Architecture → Methodology → Results → Discussion → Conclusion → References.

---

## Faz 5 — Son kontrol

**Durum (2026-05-29):** Statik LaTeX kontrolleri tamamlandı. Yerel ortamda `pdflatex`, `latexmk`, `xelatex` veya `tectonic` bulunmadığı için PDF derlemesi çalıştırılamadı.

- [x] Abstract kelime sayısı ~150 (146 kelime; IEEE genelde 150–250, ödev 150 istiyor)
- [x] Tüm `\ref{fig:...}` tanımlı
- [x] Ödev rubriği: Vision (ONNX edge AI), Control (FSM), Communication (paket), Results (grafik + accuracy), Discussion (güç, ses/Kayseri, ONNX)
- [x] Ekip: `\author{}` + Team Contributions (`team-and-contributions.md`)
- [ ] `pdflatex` / `latexmk` ile derleme hatasız — TeX motoru bu ortamda kurulu değil; statik ref/cite/görsel/brace kontrolleri temiz
- [x] Plagiarism: kod alıntıları kısa; Instructables rapor metninde kaynak/kod alıntısı olarak kullanılmadı

---

## Dosya haritası (plans/)

| Dosya | İçerik |
|-------|--------|
| `project-summary.md` | Tek sayfalık sistem özeti |
| `intro.md` | Giriş paragrafları + problem statement |
| `architecture.md` | Blok diyagram, veri akışı, donanım |
| `methodology-vision.md` | Kamera, YOLO/ONNX/MediaPipe, nişan |
| `methodology-control.md` | Controller, smoothing, FSM |
| `methodology-communication.md` | Seri protokol, baud, failsafe |
| `results.md` | Metrikler, grafik şablonu, accuracy tanımı |
| `discussion.md` | Zorluklar ve çözümler |
| `abstract-conclusion.md` | Abstract taslağı + conclusion + future work |
| `references.md` | Biblio başlangıç listesi |
| `latex-mapping.md` | MD → LaTeX `\section{}` eşlemesi |
| `edge-ai-onnx-deployment.md` | YOLO→ONNX, kuantizasyon, analytics yok |
| `methodology-audio.md` | Kayseri, driver arızası, telefon hoparlör |
| `team-and-contributions.md` | Yazarlar, Acknowledgments, görev tablosu |

---

## Tahmini takvim (örnek)

| Gün | Görev |
|-----|--------|
| 1 | Faz 0 + Architecture + Communication şekilleri |
| 2 | Methodology metin + FSM diyagramı |
| 3 | Deneyler (latency, accuracy, FPS) |
| 4 | Results + Discussion + grafikler |
| 5 | Abstract, Intro, Conclusion, References, derleme |

---

## Hızlı komutlar (Pi üzerinde)

```bash
cd turret && source venv/bin/activate
python3 serial_test.py 90 90 90 90 1    # Arduino bring-up
python3 main.py                          # tam sistem (ölçüm için debug açılabilir)
python3 calibrate.py                     # piksel↔açı (raporda methodology)
```

Config: `turret/config.yaml` — raporda tablo olarak özetlenebilir.
