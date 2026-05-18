"""Portal ses replikleri — durum geçişlerinde çalınır.

Pi 5'te 3.5mm jak YOKTUR: ses USB ses kartı (-> PAM8403 -> 8Ω hoparlör)
ya da MAX98357A I2S amfi üzerinden çıkar. ALSA varsayılan cihazı doğru
karta ayarlanmalı (README'ye bak).

pygame.mixer ile bloklamadan çalar; yoksa `aplay`'e düşer.
"""

from __future__ import annotations

import os
import random
import subprocess
import time


class SoundPlayer:
    def __init__(self, cfg: dict, project_dir: str):
        self.enabled = cfg["sounds"]["enabled"]
        base = os.path.join(project_dir, cfg["sounds"]["base_dir"])
        self.groups = {
            k: [os.path.join(base, p) for p in cfg["sounds"][k]]
            for k in ("found", "lock", "lost")
        }
        self._backend = None
        self._mixer = None
        self._last_play = 0.0

        if not self.enabled:
            return
        try:
            import pygame

            pygame.mixer.init()
            self._mixer = pygame
            self._backend = "pygame"
        except Exception as e:  # noqa: BLE001
            print(f"[sound] pygame yok ({e}); 'aplay' kullanılacak")
            self._backend = "aplay"

    def _is_busy(self) -> bool:
        if self._backend == "pygame":
            return bool(self._mixer.mixer.get_busy())
        return False

    def play(self, group: str, allow_interrupt: bool = False):
        """group: 'found' | 'lock' | 'lost'. Bloklamaz."""
        if not self.enabled:
            return
        files = self.groups.get(group, [])
        files = [f for f in files if os.path.isfile(f)]
        if not files:
            return
        if self._is_busy() and not allow_interrupt:
            return

        path = random.choice(files)
        self._last_play = time.monotonic()
        try:
            if self._backend == "pygame":
                self._mixer.mixer.music.load(path)
                self._mixer.mixer.music.play()
            else:
                subprocess.Popen(
                    ["aplay", "-q", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception as e:  # noqa: BLE001 - ses kritik değil, sistemi durdurma
            print(f"[sound] çalınamadı {path}: {e}")

    def close(self):
        if self._backend == "pygame":
            try:
                self._mixer.mixer.quit()
            except Exception:  # noqa: BLE001
                pass
