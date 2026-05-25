# Ekip ve Katkılar — Authors / Acknowledgments / Team Contributions

**Durum:** Faz 0 tamamlandı — `turret_report.tex` içinde `\author{}` ve `\section*{Acknowledgments}` uygulandı.

**Senin doldurman gereken:** `[Institution Name]` ve `[instructor/department]` (aşağıda işaretli).

---

## Yazarlar

| Ad Soyad | Rol özeti |
|----------|-----------|
| **Hamza Tekin** | Yazılım (kodlama), rapor hazırlığı (yoğun) |
| **Kerem Çatalbaş** | Kablolama (tam sorumluluk), rapor hazırlığı (yoğun) |
| **Yusuf Emre Boyraz** | Yazılım (kodlama), 3D model/baskı |
| **Yusuf Baki Demiryürek** | 3D model/baskı, malzeme temini (Kayseri) |

**Ortak:** Dört kişi projenin tüm aşamlarında yoğun katkı verdi; **taret montajı ve entegrasyon** birlikte yapıldı.

---

## Görev dağılımı (Tablo — raporda `\subsection{Team Contributions}`)

| Alan | Sorumlular | Detay |
|------|------------|-------|
| Yazılım / kodlama | Hamza Tekin, Yusuf Emre Boyraz | Python: vision, FSM, serial, ses; Arduino firmware; kalibrasyon |
| Edge AI / ONNX | Hamza Tekin, Yusuf Emre Boyraz | YOLO→ONNX, Pi ONNX Runtime (`edge-ai-onnx-deployment.md`) |
| Ses (telefon hoparlör) | Hamza Tekin, Yusuf Emre Boyraz | `audio_stream.py`, network mod (`methodology-audio.md`) |
| 3D tasarım & baskı | Yusuf Baki Demiryürek, Yusuf Emre Boyraz | Mekanik gövde, montaj parçaları |
| Kablolama & elektrik | Kerem Çatalbaş | Güç, servo/lazer/LED, GND, test |
| Malzeme temini | Yusuf Baki Demiryürek | Pi, Arduino, servo, kaynak (Kayseri çevresi) |
| Mekanik montaj | **Tüm ekip** | Birleştirme, saha testi |
| Rapor / dokümantasyon | Kerem Çatalbaş, Hamza Tekin | IEEE LaTeX, planlar, ölçüm |

---

## LaTeX — `\author{}` (turret_report.tex’te aktif)

Dosya: `ReportLatex/turret_report.tex` satır 22–25.

**Değiştir:**

```latex
[Institution Name]  →  üniversite / bölüm adın
```

İsimler: `Kerem~\.{C}atalba\c{s}` (LaTeX Türkçe karakter).

---

## LaTeX — Acknowledgments (turret_report.tex’te aktif)

```latex
\section*{Acknowledgments}
The authors thank the course instructor and department for project guidance.
Component sourcing in the Kayseri region was coordinated by Y.~B.~Demiry\"{u}rek.
Late-stage audio used a custom HTTP streaming solution and team smartphones
after local unavailability of replacement speaker drivers.
```

**Değiştir:** `course instructor and department` → gerçek hoca/bölüm adı.

---

## LaTeX — Team Contributions (Faz 1’de Introduction sonuna veya ayrı subsection)

```latex
\subsection{Team Contributions}
All four authors contributed across integration and testing. Software and
ONNX edge deployment were led by H.~Tekin and Y.~E.~Boyraz. Mechanical CAD
and 3D printing were led by Y.~B.~Demiry\"{u}rek and Y.~E.~Boyraz.
K.~\.{C}atalba\c{s} was solely responsible for electrical wiring and power
distribution. System assembly was performed jointly. Report preparation was
led primarily by K.~\.{C}atalba\c{s} and H.~Tekin; component procurement by
Y.~B.~Demiry\"{u}rek.
```

---

## Türkçe özet (kapak / sunum)

Bu çalışma **Hamza Tekin**, **Kerem Çatalbaş**, **Yusuf Emre Boyraz** ve **Yusuf Baki Demiryürek** tarafından yürütülmüştür. Yazılım Hamza Tekin ve Yusuf Emre Boyraz; 3D parça ve baskı Yusuf Baki Demiryürek ile Yusuf Emre Boyraz; kablolama Kerem Çatalbaş; malzeme temini Yusuf Baki Demiryürek; montaj tüm ekip; rapor Kerem Çatalbaş ve Hamza Tekin tarafından hazırlanmıştır.

---

## Raporda nereye yazılır?

| Bölüm | Durum |
|-------|--------|
| Title / `\author{}` | ✅ `turret_report.tex` |
| Acknowledgments | ✅ `turret_report.tex` |
| Team Contributions subsection | ⏳ Faz 1 (metin yukarıda hazır) |
| Introduction cümlesi | ⏳ Faz 1 (`intro.md` ile birlikte) |

---

## Faz 0 checklist

- [x] Dört yazar adı doğrulandı (Kerem Çatalbaş)
- [x] Görev tablosu
- [x] LaTeX author + thanks + acknowledgments
- [x] Team Contributions paragrafı hazır
- [ ] `[Institution Name]` ve hoca adı — **sen doldur**
