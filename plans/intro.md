# Introduction — Rapor taslağı (Section II)

> LaTeX’e aktarırken akademik İngilizceye çevir. Aşağıdaki paragraflar içerik iskeletidir.

**İlişkili planlar:** `edge-ai-onnx-deployment.md`, `methodology-audio.md`, `team-and-contributions.md`

---

## Authors (title page)

This work was carried out by **Hamza Tekin**, **Kerem Çatalbaş**, **Yusuf Emre Boyraz**, and **Yusuf Baki Demiryürek**. All four contributed substantially across hardware and software integration; role details appear in Acknowledgments or a Team Contributions subsection (`team-and-contributions.md`).

---

## Problem statement (önerilen açılış)

Interactive pan-tilt platforms that detect and engage human targets combine **real-time computer vision**, **closed-loop actuator control**, and **resource-constrained embedded hardware**. Educational and hobbyist projects often rely on legacy PC software (e.g., early Instructables turret builds from 2013–2014) that cannot run on modern single-board computers or satisfy latency and safety requirements for physical servos.

This project implements a **Portal-inspired autonomous turret**: a fixed camera on a Raspberry Pi 5 performs person detection; a separate pan-tilt-laser assembly is driven by an Arduino Uno R4 over a serial link. The split architecture mirrors industrial practice: a “smart” edge node for perception and planning, and a “dumb” real-time actuator node for deterministic PWM and failsafe behavior.

---

## Why embedded systems are relevant

1. **Hard real-time constraints:** Servo PWM and slew limiting must run even if the Pi stalls on inference; the Arduino loop (~15 ms) guarantees bounded actuator updates and a 500 ms communication failsafe.

2. **Power and thermal limits:** The Pi 5 must run neural inference at ≥15 FPS while the MG996R pair can draw stall currents near 2 A each—mandating **separate power domains** and common ground design, a core embedded lesson.

3. **Sensor–actuator calibration:** The camera is **fixed** on the turret body while the laser moves; pixel-to-angle mapping is not a simple pinhole model but an empirically calibrated linear map (`calibrate.py`), typical of embedded vision systems without encoders.

4. **Fault containment:** Serial disconnect, USB reset, or process crash must not leave servos at extreme angles; firmware centers servos and disables the laser when commands stop.

5. **Human-in-the-loop safety:** The system tracks people for demonstration; failsafe centering and mechanical software limits reduce risk compared to open-loop hobby servos.

---

## Project goals (bullet → prose)

- Detect the **largest person** in the camera FOV (proxy for nearest target).
- Track with smooth pan/tilt and coordinated eye servos for anthropomorphic motion.
- Reproduce **Portal audio cues** on state transitions (found, lock, lost).
- Achieve interactive latency suitable for demonstration (target ≥15 FPS vision, 30 Hz command stream).
- Provide bring-up tools: `serial_test.py`, `calibrate.py`, `detect_test.py`.

---

## Contributions (what to claim in the paper)

| Contribution | Evidence in repo |
|--------------|------------------|
| Split Pi/Arduino architecture with documented serial protocol | `serial_link.py`, `turret_firmware.ino` |
| **YOLO11n exported to ONNX; edge inference on Pi 5 (no on-device analytics stack)** | `edge-ai-onnx-deployment.md`, `vision.py`, `yolo11n.onnx` |
| **Quantized / optimized embedded AI** vs classical HSV thresholding | Methodology Vision + Discussion |
| Calibrated pixel-to-servo mapping for fixed-camera turret | `controller.py`, `calibrate.py` |
| State machine with debounced acquire/loss timers | `main.py`, `config.yaml` timers |
| **Custom network audio — smartphones as speakers** after driver failure (Kayseri supply) | `methodology-audio.md`, `audio_stream.py` |
| 3D-printed mechanical structure | Team: Y. B. Demiryürek, Y. E. Boyraz |
| Electrical integration | Team: K. Çatalbaş |

---

## Scope and non-goals

- **Not** a ball-sorting or color-blob pipeline (no HSV thresholding in codebase).
- **Not** autonomous weaponization: laser is demonstrator-grade; firing is audio/LED choreography.
- **Not** SLAM or 3D pose—2D bounding box center + optional aim offset only.

---

## Suggested section ending (transition to Architecture)

The following section describes the hardware–software partition, data flow from CSI camera to servo PWM, and the rationale for delegating motion limits and failsafe logic to the microcontroller while retaining perception and high-level behavior on the Raspberry Pi.

---

## Keywords (IEEEkeywords önerisi)

Embedded systems, Raspberry Pi, Arduino, pan-tilt, object detection, YOLO, serial communication, real-time control, human tracking.
