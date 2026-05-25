"""Bench measurement helper for the project report (Faz 0 / Faz 3).

Collects:
  - FPS (rolling, from main loop style timing)
  - Per-frame inference latency (ms)
  - Optional: detection-to-first-command latency when target appears

Usage (on Pi 5 with camera + optional Arduino):
  cd turret && source venv/bin/activate
  python3 measure_results.py --seconds 60
  python3 measure_results.py --seconds 30 --no-serial   # vision only

Outputs:
  plans/data/latency.csv      (if --latency-trials > 0, manual enter FOV)
  plans/data/benchmark_run.json
  Console summary for pasting into plans/results.md

Does not modify main.py permanently.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA_DIR = os.path.join(REPO, "plans", "data")


@dataclass
class Sample:
    ts: float
    infer_ms: float
    had_target: bool
    pan_cmd: int | None = None


@dataclass
class RunSummary:
    duration_s: float
    frames: int
    fps: float
    infer_ms_mean: float
    infer_ms_std: float
    infer_ms_p95: float
    detection_ratio: float
    latency_trials_ms: list = field(default_factory=list)
    backend: str = ""
    notes: str = ""


def load_cfg():
    with open(os.path.join(HERE, "config.yaml")) as f:
        return yaml.safe_load(f)


def main():
    ap = argparse.ArgumentParser(description="Report benchmark runner")
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--no-serial", action="store_true")
    ap.add_argument("--latency-trials", type=int, default=0,
                    help="Manual trials: enter FOV, script logs detection-to-command ms")
    args = ap.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    from vision import Camera, PersonDetector
    from controller import Controller

    cfg = load_cfg()
    cam = Camera(cfg["camera"]["width"], cfg["camera"]["height"],
                 cfg["camera"]["fps"], cfg["camera"]["hflip"],
                 cfg["camera"]["vflip"])
    d = cfg["detection"]
    det = PersonDetector(d["backend"], d["model"], d["use_ncnn"],
                         d["conf"], d["person_class_id"])
    ctrl = Controller(cfg)
    link = None
    if not args.no_serial:
        from serial_link import SerialLink
        link = SerialLink(cfg["serial"]["port"], cfg["serial"]["baud"],
                          cfg["serial"]["command_hz"],
                          cfg["serial"]["reconnect_delay_s"])

    ps = cfg["servos"]["pan"]
    center_pan = int(ps["center"])
    center_tilt = int(cfg["servos"]["tilt"]["center"])
    laser = bool(cfg["servos"].get("laser_always_on", True))

    samples: list[Sample] = []
    latency_ms: list[float] = []
    lat_start: float | None = None
    prev_had = False

    print(f"[bench] backend={d['backend']} duration={args.seconds}s")
    print("[bench] Walk into FOV for latency trials; Ctrl+C to stop early.\n")

    t0 = time.monotonic()
    end = t0 + args.seconds
    frames = 0

    try:
        while time.monotonic() < end:
            frame = cam.read()
            if frame is None:
                continue
            frames += 1
            now = time.monotonic()

            t_inf0 = time.perf_counter()
            target = det.detect(frame)
            infer_ms = (time.perf_counter() - t_inf0) * 1000.0
            had = target is not None

            pan_cmd = None
            if had:
                aim_y = target.cy + int(round(
                    float(d.get("aim_y_offset_ratio", -0.2)) * target.h))
                aim_x = target.cx + int(d.get("aim_pixel_offset_x", 0))
                aim_y += int(d.get("aim_pixel_offset_y", 0))
                cmd = ctrl.update((aim_x, aim_y))
                pan_cmd = cmd.pan
                if link is not None:
                    link.send(cmd.pan, cmd.tilt, cmd.eye_x, cmd.eye_y, laser=laser)

            # Latency: rising edge into detection -> first non-center pan command
            if had and not prev_had:
                lat_start = now
            if lat_start is not None and had and pan_cmd is not None:
                if abs(pan_cmd - center_pan) > 2 or abs(cmd.tilt - center_tilt) > 2:
                    dt = (now - lat_start) * 1000.0
                    latency_ms.append(dt)
                    print(f"[latency] trial {len(latency_ms)}: {dt:.1f} ms")
                    lat_start = None
                    if args.latency_trials and len(latency_ms) >= args.latency_trials:
                        break
            prev_had = had

            samples.append(Sample(now, infer_ms, had, pan_cmd))
    except KeyboardInterrupt:
        print("\n[bench] interrupted")
    finally:
        cam.close()
        if link is not None:
            c = cfg["servos"]
            link.send(c["pan"]["center"], c["tilt"]["center"],
                      c["eye_x"]["center"], c["eye_y"]["center"],
                      laser=False, force=True)
            link.close()

    duration = max(time.monotonic() - t0, 1e-6)
    infer = [s.infer_ms for s in samples]
    det_ratio = sum(1 for s in samples if s.had_target) / max(len(samples), 1)

    infer_sorted = sorted(infer)
    p95 = infer_sorted[int(0.95 * (len(infer_sorted) - 1))] if infer_sorted else 0.0

    summary = RunSummary(
        duration_s=duration,
        frames=frames,
        fps=frames / duration,
        infer_ms_mean=statistics.mean(infer) if infer else 0.0,
        infer_ms_std=statistics.stdev(infer) if len(infer) > 1 else 0.0,
        infer_ms_p95=p95,
        detection_ratio=det_ratio,
        latency_trials_ms=latency_ms,
        backend=str(d["backend"]),
        notes="Faz 3: paste values into plans/results.md",
    )

    out_json = os.path.join(DATA_DIR, "benchmark_run.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(asdict(summary), f, indent=2)

    if latency_ms:
        csv_path = os.path.join(DATA_DIR, "latency.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("trial,latency_ms\n")
            for i, ms in enumerate(latency_ms, 1):
                f.write(f"{i},{ms:.1f}\n")
        print(f"[bench] wrote {csv_path}")

    print("\n=== SUMMARY (copy to plans/results.md) ===")
    print(f"FPS:              {summary.fps:.2f}")
    print(f"Inference mean:   {summary.infer_ms_mean:.1f} ms (std {summary.infer_ms_std:.1f})")
    print(f"Inference p95:    {summary.infer_ms_p95:.1f} ms")
    print(f"Detection ratio:  {summary.detection_ratio * 100:.1f}% of frames")
    if latency_ms:
        print(f"Latency mean:     {statistics.mean(latency_ms):.1f} ms")
        print(f"Latency std:      {statistics.stdev(latency_ms):.1f} ms" if len(latency_ms) > 1 else "")
    else:
        print("Latency trials:   (none — re-run with person entering FOV)")
    print(f"Saved:            {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
