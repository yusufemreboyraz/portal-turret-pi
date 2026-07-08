# Portal Turret

An autonomous pan-tilt turret, inspired by the sentry turrets in Valve's
*Portal*, built from a Raspberry Pi 5 and an Arduino Uno R4. The Pi handles
camera-based person detection and decision-making; the Arduino drives the
servos and laser over a serial link. This was built as a term project for an
embedded/robotics course.

## What it does

A CSI camera on the Pi continuously scans for people using an object
detector. When a person is found, a finite-state machine tracks them,
aims a mounted laser pointer at the target, and plays back Portal turret
voice lines through a speaker. If the detected person's bounding box grows
large enough (i.e., they are close to the turret), the system triggers a
"fire" sequence consisting of a sound cue and an LED light show at the
barrel. No live ammunition or projectiles are involved.

State machine (`turret/main.py`):

- `SEARCHING` — no target; turret stays centered (or idle-scans, if enabled),
  laser on.
- `TARGET_ACQUIRED` — a person is detected; if they remain visible for
  `found_ms`, transitions to `TRACKING` and plays a "found" sound.
- `TRACKING` — actively following the target; if the bounding box covers
  enough of the frame, plays a "lock" sound and triggers the fire sequence.
- `TARGET_LOST` — target disappeared; after `lost_ms` without reacquiring,
  plays a "lost" sound and returns to `SEARCHING`. If the target reappears
  within `reacquire_ms`, goes back to `TRACKING` instead.

## Architecture

```
[CSI Camera] -> [Raspberry Pi 5] --USB serial--> [Arduino Uno R4] --PWM--> 4x Servo
                       |                                |  pan / tilt (barrel)
                [Audio output]                          |  eye X / eye Y
                                                         +- laser (digital on/off)
                                                         +- 4x barrel LEDs
```

All perception and decision-making happens on the Pi; the Arduino only
executes the angles it is told to, and independently enforces safety limits.

Software layers on the Pi (`turret/`):

| Layer | Module | Responsibility |
|---|---|---|
| Perception | `vision.py` | Camera capture + person detection, returns the largest detected person as a target |
| Planning | `main.py` | State machine, aim-point offset, fire trigger |
| Control | `controller.py` | Converts a target pixel into pan/tilt/eye servo angles, applies calibration, low-pass smoothing, and per-frame step limiting |
| Communication | `serial_link.py` | Sends servo commands to the Arduino over USB serial, with auto-reconnect and auto port detection |
| Audio | `sound.py`, `audio_stream.py` | Plays sound effects locally (pygame/aplay) or streams them to a phone browser over HTTP |

Serial protocol: a single ASCII line per command,
`T,<pan>,<tilt>,<eyeX>,<eyeY>,<laser>\n`, sent at up to `serial.command_hz`
(30 Hz by default). A separate one-character command (`F`) triggers the LED
fire choreography, and `L,<0|1>` toggles whether the firmware clamps angles
to their configured mechanical limits.

On the Arduino side (`arduino/turret_firmware/turret_firmware.ino`), incoming
target angles are rate-limited (slew limiting) before being written to the
servos, and a failsafe returns all servos to center and turns off the laser
if no command is received for a configurable timeout. This means transient
delays in Pi-side inference do not translate into erratic or unsafe servo
motion.

### Safety

- Arduino-side slew-rate limiting smooths raw commands before they reach the servos.
- Arduino-side failsafe centers all servos and disables the laser if the serial link goes quiet.
- Arduino-side clamping keeps commanded angles within configured mechanical limits (enabled by `main.py` at startup, disabled only by `serial_test.py` for manual limit-finding).
- On shutdown, the Pi explicitly sends a center position with the laser off before closing the serial connection.

## Detection backends

Person detection is pluggable via `detection.backend` in `config.yaml`:

- `onnx` (recommended for the Raspberry Pi) — a YOLO11n model exported to
  ONNX and run with ONNX Runtime. This avoids installing the full
  Ultralytics/PyTorch stack on the Pi; only inference is needed on-device.
  See `plans/edge-ai-onnx-deployment.md` for the rationale and export
  pipeline.
- `yolo` — Ultralytics YOLO with a `.pt` checkpoint, useful for fast
  iteration on a development machine (e.g., a Mac); optionally exported to
  NCNN for a faster CPU path.
- `mediapipe` — a lighter-weight fallback using MediaPipe pose detection.

If no camera hardware is available, `vision.Camera` falls back to a USB
webcam via OpenCV, which is useful for development off the target hardware.

## Hardware

| Component | Notes |
|---|---|
| Computer | Raspberry Pi 5 (8 GB recommended) |
| Microcontroller | Arduino Uno R4 |
| Camera | Pi CSI camera module (`picamera2`) |
| Pan/tilt servos | 2x MG996R |
| Eye servos | 2x SG90-class |
| Laser | Digital pin, continuous-on mode |
| Barrel LEDs | 4x, for the fire choreography |
| Audio | USB sound card + amplifier, or network streaming to a phone as a fallback |
| Link | USB serial, 115200 baud |

Power is the most safety-critical part of the build:

- The Pi must be powered from a proper 27 W USB-C PD supply; a small battery
  is not sufficient for the Pi 5 plus a running detection model.
- Servos require their own regulated 5-6 V supply rated for several amps
  (stall current on the MG996R units is roughly 4 A each); they must not be
  powered from the Arduino's 5V pin.
- The servo supply ground and the Arduino ground must be tied together.
- The Pi has no headphone jack; audio requires a USB sound card driving an
  amplifier and speaker, or the network-streaming fallback in
  `audio_stream.py`.

## Software setup (Raspberry Pi OS Bookworm, 64-bit)

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv
cd turret
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```

Dependencies are listed in `turret/requirements.txt`: `pyyaml`, `pyserial`,
`numpy`, `opencv-python`, `ultralytics` (development backend only),
`pygame` (audio). `onnxruntime` is required for the recommended `onnx`
backend and should be installed separately on the Pi.

Enable the camera (`raspi-config` -> Interface -> Camera) and confirm it
works with `libcamera-hello`. If using a USB sound card, select it as the
default output (`raspi-config` -> Audio, or a manual `~/.asoundrc`) and
verify with `speaker-test`. Find the Arduino's serial device with
`ls /dev/ttyACM*` and set it in `turret/config.yaml` under `serial.port`
(auto-detection is also attempted at runtime if the configured port does
not exist).

## Arduino setup

1. Install the Renesas Uno R4 board package in the Arduino IDE.
2. Flash `arduino/turret_firmware/turret_firmware.ino`.
3. Power the servos from their dedicated supply and connect the Arduino to
   the Pi over USB.

## Running and calibrating

Recommended bring-up order:

```bash
# 1. Verify servo motion and failsafe with the Arduino alone
python3 serial_test.py 90 90 90 90 1     # all centered, laser on
python3 serial_test.py sweep             # mechanical pan sweep
#    -> servos should return to center ~500ms after commands stop

# 2. Verify camera + detection (set debug.show_window: true in config.yaml)
python3 main.py                          # a detected person should be boxed, FPS >= 15

# 3. Calibrate pixel-to-angle mapping (camera fixed, turret body moves)
python3 calibrate.py
#    jog the servos with the keyboard, point the laser at a spot, click that
#    spot on the video feed; collect 2+ points, press 's' to save into config.yaml

# 4. Fine-tune laser/camera parallax and gain
python3 calibrate_aim.py

# 5. Run the full system
python3 main.py
```

All runtime behavior is configured in `turret/config.yaml`: servo limits and
calibration, smoothing/deadzone parameters, state-machine timers, sound
files and playback mode, and the detection backend.

## Verification checklist

- Servo supply holds at least 4.8 V under load; no Pi brownouts.
- `serial_test.py` moves all servos and returns to center after the failsafe timeout.
- `main.py` boxes a person reliably at an acceptable frame rate.
- After calibration, the laser lands close to the intended aim point on a person.
- Entering/leaving the camera's field of view produces the correct state transitions and sounds.
- Tracking motion is smooth (no visible jitter) while following a moving target.

## Measuring performance

`turret/measure_results.py` is a bench script for collecting FPS, per-frame
inference latency, and detection-to-command latency, either with or without
the Arduino connected:

```bash
python3 measure_results.py --seconds 60 --latency-trials 20
python3 measure_results.py --seconds 30 --no-serial   # vision only
```

As of this writing, the numbers in `plans/results.md` are preliminary
engineering estimates rather than measurements taken from a completed run;
the script above and `plans/tools/plot_latency.py` are the tools intended to
produce the real figures once a measurement pass is done on target hardware.

## Project structure

```
turret/          Python application that runs on the Raspberry Pi
  main.py           orchestrator / state machine
  vision.py         camera capture + person detection
  controller.py     pixel-to-angle conversion and smoothing
  serial_link.py    serial communication with the Arduino
  sound.py, audio_stream.py   audio playback
  calibrate.py, calibrate_aim.py   calibration tools
  measure_results.py   benchmarking tool
  config.yaml       all runtime configuration
  sounds/           audio clips (may be excluded from version control)

arduino/
  turret_firmware/  main firmware (servo control, failsafe, LEDs, laser)
  led_test/         standalone LED test sketch

plans/             planning and methodology notes used to write the report,
                   covering architecture, vision, audio, control,
                   communication, results, and the ONNX deployment approach

ReportLatex/       IEEE-format LaTeX report and figures
```

## Notes

- This project does not reuse the original 2013-2014 Instructables/Windows
  turret code; only the general idea (serial protocol at 115200 baud,
  found/lost/reacquire timing logic, Portal sound effects) carried over,
  reimplemented from scratch for this architecture.
