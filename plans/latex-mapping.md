# LaTeX Section Mapping — MD → `turret_report.tex`

---

## Önerilen dosya adı

Copy: `ReportLatex/bare_jrnl_new_sample4.tex` → `ReportLatex/turret_report.tex`

---

## Section → source file

| `\section{}` in LaTeX | Primary MD source | Figures/tables |
|----------------------|-------------------|----------------|
| Abstract | `abstract-conclusion.md` | — |
| Introduction | `intro.md` | — |
| System Architecture | `architecture.md` | Fig. 1 block diagram |
| Methodology | | |
| — Vision / Edge AI | `edge-ai-onnx-deployment.md` + `methodology-vision.md` | ONNX pipeline fig. |
| — Audio | `methodology-audio.md` | Phone speaker diagram |
| — Control | `methodology-control.md` | Fig. 2 FSM |
| — Communication | `methodology-communication.md` | Fig. 3 sequence |
| Acknowledgments (optional) | `team-and-contributions.md` | Team table |
| Experimental Results | `results.md` | Fig. 4 latency, Table I metrics |
| Discussion | `discussion.md` | Table II optional |
| Conclusion | `abstract-conclusion.md` | — |
| Future Work | `abstract-conclusion.md` | subsection or paragraph |
| References | `references.md` | `.bib` or `thebibliography` |

---

## IEEE template edits (first pass)

Replace in preamble/title:

```latex
\title{Embedded Vision Pan-Tilt Turret:\\
Raspberry Pi 5 and Arduino Uno R4 Co-Design}

\author{Hamza~Tekin, Yusuf~Emre~Boyraz, Kerem~Çatalbaş, and Yusuf~Baki~Demiryürek%
\thanks{Manuscript for [Course Name], [Date].}%
\thanks{See Acknowledgments for team contributions.}}
% Tam metin: plans/team-and-contributions.md

\begin{abstract}
% paste from abstract-conclusion.md (English)
\end{abstract}

\begin{IEEEkeywords}
Embedded systems, computer vision, YOLO, pan-tilt, serial communication, failsafe.
\end{IEEEkeywords}
```

Delete sample article body sections (Design Intent, etc.) from `bare_jrnl_new_sample4.tex`.

---

## Figure filenames (convention)

| File | Content |
|------|---------|
| `ReportLatex/fig_architecture.pdf` | Block diagram |
| `ReportLatex/fig_fsm.pdf` | State machine |
| `ReportLatex/fig_serial.pdf` | Protocol timing |
| `ReportLatex/fig_latency.png` | Bar chart from `results.md` |
| `ReportLatex/fig_hardware.jpg` | Photo (you provide) |

Include:

```latex
\begin{figure}[!t]
\centering
\includegraphics[width=\linewidth]{fig_architecture}
\caption{System architecture: Raspberry Pi 5 perception and planning with Arduino Uno R4 actuator node.}
\label{fig:arch}
\end{figure}
```

---

## Algorithm / pseudocode (optional)

Methodology-Control için `algorithmic` paketi (template’de zaten var):

```latex
\begin{algorithm}
\caption{Per-frame control loop}
\label{alg:loop}
\begin{algorithmic}
\STATE $frame \gets \text{Camera.read}()$
\STATE $target \gets \text{Detector.detect}(frame)$
\STATE Update FSM with $target$
\STATE $(pan,tilt,eye) \gets \text{Controller.update}(aim)$
\STATE $\text{Serial.send}(pan,tilt,eye,laser)$
\end{algorithmic}
\end{algorithm}
```

---

## Prompt template for Cursor (copy-paste)

```
Write LaTeX for ReportLatex/turret_report.tex.

Section: [Introduction | Methodology Vision | ...]
Source material: plans/[file].md
Requirements:
- IEEEtran journal format
- Academic English
- Include \ref{fig:arch} placeholders where MD says Fig. X
- Use \cite{} keys from plans/references.md
- Do not invent experimental numbers; use [TBD] if missing
```

---

## Rubric coverage checklist

| Required | Where in paper |
|----------|----------------|
| Abstract 150 words | `abstract-conclusion.md` |
| Introduction + embedded relevance | `intro.md` |
| System Architecture + block diagram | `architecture.md` |
| Vision methodology | `methodology-vision.md` |
| Control FSM | `methodology-control.md` |
| Serial packet | `methodology-communication.md` |
| Latency graph | `results.md` + `fig_latency.png` |
| Accuracy metric | `results.md` (adapted from ball-sort example) |
| Discussion challenges | `discussion.md` |
| Conclusion + future | `abstract-conclusion.md` |
| References | `references.md` |
