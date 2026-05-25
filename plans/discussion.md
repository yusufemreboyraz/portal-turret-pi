# Discussion — Rapor taslağı (Section VI)

> Her madde: **Challenge → Impact → Solution implemented → Residual risk**

---

## 1. Lighting and vision robustness

**Challenge:** Person detection with YOLO/ONNX degrades in low light, strong backlight, or cluttered backgrounds; no HSV fallback exists.

**Impact:** Missed detections trigger LOST state; turret returns to SEARCHING and may play “Are you still there?”

**Solutions:**
- Use learned detector with `conf: 0.45` tunable in `config.yaml`
- Largest-box heuristic assumes one dominant person
- `hflip` for consistent operator-facing geometry
- Optional MediaPipe for CPU-only lightweight tests

**Residual:** No auto-exposure sync documented; recommend uniform front lighting in demo.

**Paper angle:** Contrast with HSV labs — we use **edge-deployed ONNX YOLO** (see `edge-ai-onnx-deployment.md`), not color thresholding.

---

## 1b. Edge AI deployment (ONNX) — discussion angle

**Challenge:** Running full Ultralytics + PyTorch on Pi 5 risks RAM, thermal throttling, and slow boot.

**Solution:** Export YOLO11n to ONNX; run with ONNX Runtime; **no on-device analytics mode** — inference-only closed loop.

**Claim for paper:** Quantized/optimized edge AI meets interactive FPS while keeping the embedded host dedicated to real-time control.

**Team:** Hamza Tekin, Yusuf Emre Boyraz (software).

---

## 2. Power distribution and brownout

**Challenge:** MG996R stall current can sag 5 V and reset Pi or Arduino via shared ground bounce.

**Impact:** USB serial drop, runaway failsafe, Pi kernel OOM/throttle under YOLO load.

**Solutions (README + firmware):**
- **Separate ≥6 A servo supply**; never power servos from Arduino 5V
- Common ground only
- Pi uses official 27W USB-C PD (not 1S LiPo)
- ONNX instead of full PyTorch on Pi to reduce RAM/CPU

**Residual:** Multimeter verification under sweep still required (`serial_test.py sweep`).

---

## 3. Serial lag and USB reset

**Challenge:** 115200 baud is ample, but USB reconnect (cable, brownout) causes 2 s bootloader wait; buffer staleness.

**Impact:** Brief period without commands → Arduino failsafe centers (500 ms).

**Solutions:**
- `SerialLink` auto-reconnect every 2 s without blocking vision loop
- `command_hz: 30` prevents flooding
- Pi flushes RX after TX (non-blocking)
- Startup `L,1` for limit enforcement

**Residual:** Ack `OK` not used for closed-loop timing — acceptable for this architecture.

---

## 4. Fixed camera vs moving laser (parallax)

**Challenge:** Camera bore-sight ≠ laser bore-sight; error grows at image edges.

**Impact:** Good center aim, poor edge aim before calibration.

**Solutions:**
- `calibrate.py` two-point linear map per axis
- `calibrate_aim.py` pixel offsets + swing gain
- `aim_y_offset_ratio` for vertical aim point

**Residual:** Linear model breaks if mechanics flex; re-calibrate after hardware changes.

---

## 5. Detection jitter → mechanical vibration

**Challenge:** Bounding box center flickers frame-to-frame.

**Impact:** Servo buzz, audible gear stress, wasted power.

**Solutions:**
- Pi: low-pass `alpha=0.55` + `max_step_deg=12`
- Arduino: `MAX_STEP_DEG=3` per 15 ms
- Eye `deadzone_px: 25` in direct mode

**Trade-off:** Higher alpha = snappier but noisier; document chosen values.

---

## 6. Audio on Raspberry Pi 5 — hoparlör arızası ve Kayseri tedarik

**Challenge:** Pi 5 has no 3.5 mm jack; USB audio was planned, but **loudspeaker drivers were damaged** during bring-up. Replacement drivers could **not be sourced quickly in Kayseri and surrounding area**, threatening the demo schedule.

**Impact:** No local Portal voice lines from a physical speaker; user experience incomplete.

**Solutions (team-developed):**
- Custom script **`audio_stream.py`**: Pi runs HTTP server on port 8765; **team smartphones act as speakers** via browser (`sounds.mode: network` in `config.yaml`)
- `SoundPlayer` in `sound.py` triggers WAV on FSM events without blocking vision
- Fallback chain: network → pygame → aplay (for other platforms)

**Paper narrative:** Emphasize *resource-constrained embedded design* — software workaround when hardware supply chain fails regionally.

**Residual:** WiFi latency on audio only (non-critical); servos and vision unaffected. See `methodology-audio.md`.

**Team:** Software (Hamza Tekin, Yusuf Emre Boyraz); material search (Yusuf Baki Demiryürek).

---

## 7. Safety and ethics

**Challenge:** Human-tracking laser demonstrator.

**Mitigations:**
- Laser **indicator** only; “fire” is sound + LED
- Failsafe centers + laser off
- Software limits on both Pi config and firmware
- README warns about power wiring

**Discuss:** Classroom/demo use only; never high-power laser.

---

## 8. Legacy inspiration vs new implementation

**Challenge:** Course may expect comparison to classic turret projects.

**Point:** 2013 Instructables code unusable on Pi; timers and wav concept preserved, architecture rewritten (`README.md`).

---

## Discussion section structure (LaTeX)

1. Paragraph: split architecture trade-offs (pro/con)
2. Subsubsection or bullets: Power, Vision, Calibration, Serial
3. Paragraph: limitations (single person, 2D aim, no depth)
4. Short paragraph: lessons for embedded vision courses

---

## Comparison table (optional Table II)

| Issue | Symptom | Fix in repo |
|-------|---------|-------------|
| Lighting | No detection | Tune conf, lighting |
| Power sag | USB disconnect | Separate servo PSU |
| Parallax | Edge miss | calibrate_aim.py |
| Jitter | Buzz | smoothing yaml |
| No audio | Silent Pi | network sound mode |
