"""Portal ses replikleri — durum geçişlerinde çalınır.

Üç çalma modu (config.sounds.mode):
  - 'network' : Pi bir HTTP sunucusu açar, telefon tarayıcısı hoparlör olur
                (Pi 5'te ses kartı yoksa en temiz yol).
  - 'pygame'  : pygame.mixer ile yerel ses çıkışı (Mac/Linux'ta ses kartı varsa).
  - 'aplay'   : ALSA aplay subprocess (basit Linux fallback).

play() asla bloklamaz; ses kritik değildir, bir hata sistemi durdurmaz.
"""

from __future__ import annotations

import os
import random
import subprocess
import time
from typing import Optional


class SoundPlayer:
    def __init__(self, cfg: dict, project_dir: str):
        s = cfg["sounds"]
        self.enabled = s["enabled"]
        # 'pygame' | 'network' | 'aplay' (eski configler için default pygame)
        self.mode = s.get("mode", "pygame")
        base_rel = s["base_dir"]
        self.base_dir = os.path.join(project_dir, base_rel)
        # Gruplar — RELATIVE yollar (network modu için lazım); local mod
        # tam yola çevirir.
        self._rel_groups = {k: list(s[k]) for k in ("found", "lock", "lost")}
        self._abs_groups = {
            k: [os.path.join(self.base_dir, p) for p in v]
            for k, v in self._rel_groups.items()
        }
        self._last_play = 0.0
        self._mixer = None
        self._streamer = None

        if not self.enabled:
            return

        if self.mode == "network":
            try:
                from audio_stream import AudioStreamer

                net = s.get("network", {}) or {}
                self._streamer = AudioStreamer(
                    base_dir=self.base_dir,
                    host=net.get("host", "0.0.0.0"),
                    port=int(net.get("port", 8765)),
                )
                self._streamer.start()
            except Exception as e:  # noqa: BLE001
                print(f"[sound] network modu açılamadı ({e}); aplay'e düşülüyor")
                self.mode = "aplay"

        if self.mode == "pygame":
            try:
                import pygame

                pygame.mixer.init()
                self._mixer = pygame
            except Exception as e:  # noqa: BLE001
                print(f"[sound] pygame yok ({e}); 'aplay' kullanılacak")
                self.mode = "aplay"

    # ---- yardımcılar ----
    def _is_busy(self) -> bool:
        if self.mode == "pygame" and self._mixer is not None:
            return bool(self._mixer.mixer.get_busy())
        return False  # network/aplay'de meşgul takibi yok

    def _pick(self, group: str) -> Optional[tuple]:
        rels = self._rel_groups.get(group, [])
        absp = self._abs_groups.get(group, [])
        idx = [i for i, p in enumerate(absp) if os.path.isfile(p)]
        if not idx:
            return None
        i = random.choice(idx)
        return rels[i], absp[i]

    # ---- ana arayüz ----
    def play(self, group: str, allow_interrupt: bool = False):
        """group: 'found' | 'lock' | 'lost'. Bloklamaz."""
        if not self.enabled:
            return
        pick = self._pick(group)
        if pick is None:
            return
        if self._is_busy() and not allow_interrupt:
            return
        rel, full = pick
        self._last_play = time.monotonic()
        try:
            if self.mode == "network" and self._streamer is not None:
                self._streamer.play_file(rel)
            elif self.mode == "pygame" and self._mixer is not None:
                self._mixer.mixer.music.load(full)
                self._mixer.mixer.music.play()
            else:
                subprocess.Popen(
                    ["aplay", "-q", full],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception as e:  # noqa: BLE001 - ses kritik değil
            print(f"[sound] çalınamadı {full}: {e}")

    def close(self):
        if self._streamer is not None:
            self._streamer.stop()
        if self._mixer is not None:
            try:
                self._mixer.mixer.quit()
            except Exception:  # noqa: BLE001
                pass
