# References — Başlangıç bibliyografyası (Section VIII)

> IEEEtran `\cite{key}` için `thebibliography` veya `IEEEtran.bst` + `.bib` kullan. Aşağıdaki kaynakları doğrula ve eksik alanları doldur.

---

## Hardware datasheets & manuals

| Key | Citation |
|-----|----------|
| `rpi5` | Raspberry Pi Ltd., *Raspberry Pi 5 Product Brief*, 2023. [Online]. Available: https://www.raspberrypi.com/products/raspberry-pi-5/ |
| `arduino_r4` | Arduino, *Arduino Uno R4 Minima / WiFi Documentation*, 2023. [Online]. Available: https://docs.arduino.cc/hardware/uno-r4-minima |
| `mg996r` | Tower Pro, *MG996R Servo Datasheet* (stall torque, current). |
| `picamera2` | Raspberry Pi Ltd., *picamera2 Library Manual*, Bookworm. https://www.raspberrypi.com/documentation/computers/camera_software.html |

---

## Vision & ML libraries

| Key | Citation |
|-----|----------|
| `ultralytics` | G. Jocher et al., *Ultralytics YOLO*, 2023. https://github.com/ultralytics/ultralytics |
| `yolo11` | Ultralytics YOLO11 model family documentation, 2024. |
| `onnxruntime` | Microsoft, *ONNX Runtime*, https://onnxruntime.ai/ |
| `mediapipe` | V. Bazarevsky et al., "BlazePose: On-device Real-time Body Pose Tracking," Google MediaPipe, 2020. |
| `opencv` | G. Bradski, "The OpenCV Library," *Dr. Dobb's Journal*, 2000. |

---

## Embedded & serial

| Key | Citation |
|-----|----------|
| `pyserial` | C. Liechti, *pyserial* documentation, https://pythonhosted.org/pyserial/ |
| `arduino_servo` | Arduino *Servo Library* reference. |

---

## Educational / inspiration (cite carefully)

| Key | Citation |
|-----|----------|
| `mcmath_turret` | Paul McWhorter, YouTube series on Arduino turret / tracking (channel videos on pan-tilt and serial control) — specify exact video title + URL you used. |
| `instructables_legacy` | Early Portal turret Instructables (~2013–2014) — cite as *historical inspiration only*; note code not used in this implementation. |
| `portal_valve` | Valve Corporation, *Portal* (2007) — game reference for behavioral design. |

---

## Course / standards (if applicable)

| Key | Citation |
|-----|----------|
| `ieee_style` | IEEE, *IEEE Editorial Style Manual* for authors. |
| `final_project_pdf` | Course document: `Final project Instructions.pdf` (local — add university/course name). |

---

## Sample BibTeX entries (paste into `refs.bib`)

```bibtex
@misc{rpi5,
  author = {{Raspberry Pi Ltd.}},
  title = {Raspberry Pi 5 Product Brief},
  year = {2023},
  howpublished = {\url{https://www.raspberrypi.com/products/raspberry-pi-5/}}
}

@misc{ultralytics_yolo,
  author = {G. Jocher and others},
  title = {Ultralytics YOLO11},
  year = {2024},
  howpublished = {\url{https://github.com/ultralytics/ultralytics}}
}

@misc{onnxruntime,
  author = {{Microsoft}},
  title = {ONNX Runtime},
  howpublished = {\url{https://onnxruntime.ai/}}
}

@misc{arduino_uno_r4,
  author = {{Arduino}},
  title = {Arduino Uno R4 Documentation},
  year = {2023},
  howpublished = {\url{https://docs.arduino.cc/hardware/uno-r4-minima}}
}
```

---

## Paul McWhorter videos (fill in your watched list)

Template — replace `VIDEO_ID` and title:

```
[P1] Paul McWhorter, "TITLE," YouTube, YEAR. [Online]. 
     Available: https://www.youtube.com/watch?v=VIDEO_ID
```

Suggested search topics on his channel:

- Arduino servo control
- Serial communication Arduino ↔ PC
- Pan-tilt or turret tracking fundamentals

---

## Minimum reference count for academic report

Aim for **8–12** references:

- 2 hardware (Pi, Arduino)
- 2 software libs (YOLO/ONNX, picamera2 or OpenCV)
- 1 MediaPipe or alternative vision paper
- 1 pyserial / embedded comm
- 1–2 educational (McWhorter, legacy turret)
- 1 course doc (if allowed)

---

## In-text citation examples

- "Person detection employs YOLO11n exported for ONNX Runtime~\cite{ultralytics_yolo,onnxruntime}."
- "The host captures CSI frames using picamera2~\cite{picamera2}."
- "Servo failsafe and slew limiting run on the Uno R4~\cite{arduino_uno_r4}."
