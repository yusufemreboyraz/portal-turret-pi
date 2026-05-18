"""Seri bring-up testi (plan adım 4).

Arduino tek başına çalışıyor mu kontrol eder. config.yaml'daki porttan
elle servo açısı/lazer komutu gönderir.

Kullanım:
  python3 serial_test.py                 # interaktif: "pan tilt eyeX eyeY laser"
  python3 serial_test.py 90 90 90 90 1   # tek komut gönder ve çık
  python3 serial_test.py sweep           # pan'ı min-max süpür (mekanik test)
"""

from __future__ import annotations

import os
import sys
import time

import yaml

from serial_link import SerialLink

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "config.yaml")) as f:
        cfg = yaml.safe_load(f)
    link = SerialLink(cfg["serial"]["port"], cfg["serial"]["baud"],
                      cfg["serial"]["command_hz"],
                      cfg["serial"]["reconnect_delay_s"])
    s = cfg["servos"]

    args = sys.argv[1:]

    if args and args[0] == "sweep":
        print("pan süpürme; Ctrl+C ile dur")
        lo, hi = s["pan"]["min"], s["pan"]["max"]
        t, c = s["tilt"]["center"], s["eye_x"]["center"]
        try:
            while True:
                for a in list(range(lo, hi, 2)) + list(range(hi, lo, -2)):
                    link.send(a, t, c, s["eye_y"]["center"], True, force=True)
                    time.sleep(0.02)
        except KeyboardInterrupt:
            pass
    elif len(args) == 5:
        link.send(*[int(x) for x in args[:4]], bool(int(args[4])), force=True)
        time.sleep(0.5)
        print("gönderildi:", args)
    else:
        print("Format: pan tilt eyeX eyeY laser   (boş satır = çık)")
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                break
            p = line.split()
            if len(p) != 5:
                print("5 değer gerekli")
                continue
            link.send(*[int(v) for v in p[:4]], bool(int(p[4])), force=True)

    link.close()


if __name__ == "__main__":
    main()
