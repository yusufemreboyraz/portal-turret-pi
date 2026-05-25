# Plans — Portal Turret akademik rapor kaynakları

Bu klasör, `turret/` ve `arduino/` kod tabanının **tek seferlik inceleme çıktısıdır**. Rapor yazarken Cursor’a tekrar tüm repo’yu okutmak yerine ilgili `.md` dosyasını `@plans/...` ile ver.

## Ekip

**Hamza Tekin · Kerem Çatalbaş · Yusuf Emre Boyraz · Yusuf Baki Demiryürek**  
Görev dağılımı → `team-and-contributions.md`

## Başlangıç

1. **`main-plan.md`** — adım adım rapor yol haritası
2. **`project-summary.md`** — sistem özeti (1 sayfa)
3. **`edge-ai-onnx-deployment.md`** — **YOLO→ONNX, Pi çıkarım, kuantize edge AI (rapor vurgusu)**
4. **`latex-mapping.md`** — hangi MD hangi `\section{}`

## Bölüm dosyaları

| Dosya | IEEE bölümü |
|-------|-------------|
| `abstract-conclusion.md` | Abstract, Conclusion, Future Work |
| `intro.md` | Introduction |
| `architecture.md` | System Architecture |
| `edge-ai-onnx-deployment.md` | Methodology — ONNX / edge AI (ana teknik hikâye) |
| `methodology-vision.md` | Methodology — Vision |
| `methodology-audio.md` | Methodology — Ses (telefon hoparlör, Kayseri) |
| `methodology-control.md` | Methodology — Control / FSM |
| `methodology-communication.md` | Methodology — Serial |
| `results.md` | Experimental Results |
| `discussion.md` | Discussion |
| `team-and-contributions.md` | Authors, Acknowledgments, görevler |
| `references.md` | References |

## Raporda mutlaka geçmesi gerekenler

1. **ONNX:** YOLO11n dönüşümü, Pi’de ONNX Runtime, analytics modu yok, edge/kuantize AI yaklaşımı  
2. **Ses:** Hoparlör driver arızası, Kayseri’de yedek yok → `audio_stream.py` ile telefon hoparlör  
3. **Ekip:** Dört yazar + görev tablosu (isteğe bağlı Acknowledgments)

## Veri

- `data/latency.csv` — latency ölçümlerini buraya yaz → grafik `results.md` içinde

## Kritik notlar

- Proje **HSV / top sıralama** kullanmıyor; **YOLO11n + ONNX** (Pi), opsiyonel MediaPipe  
- LaTeX şablonu: `ReportLatex/bare_jrnl_new_sample4.tex`

## Faz durumu

| Faz | Durum |
|-----|--------|
| **Faz 0** | ✅ Tamamlandı — `turret_report.tex`, ölçüm scriptleri, abstract/team/results planları |
| Faz 1 | ⏸ Beklemede (kullanıcı onayı sonrası) |
| Faz 3 | Ölçüm: `python3 turret/measure_results.py` |

## Son güncelleme

Faz 0: 2026-05-25
