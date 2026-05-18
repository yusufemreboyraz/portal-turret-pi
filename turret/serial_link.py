"""Pi <-> Arduino seri köprüsü.

Protokol (tek satır, '\\n'): T,<pan>,<tilt>,<eyeX>,<eyeY>,<laser>
Arduino her komuta "OK" döner. Bağlantı koparsa otomatik yeniden bağlanır;
komut göndermek hiçbir zaman ana döngüyü bloklamaz.
"""

from __future__ import annotations

import time

try:
    import serial  # pyserial
except ImportError:  # pragma: no cover - bağımlılık eksikse anlamlı hata
    serial = None


class SerialLink:
    def __init__(self, port: str, baud: int, command_hz: float = 30.0,
                 reconnect_delay_s: float = 2.0):
        if serial is None:
            raise RuntimeError("pyserial kurulu değil: pip install pyserial")
        self.port = port
        self.baud = baud
        self.min_interval = 1.0 / command_hz if command_hz > 0 else 0.0
        self.reconnect_delay_s = reconnect_delay_s
        self._ser = None
        self._last_send = 0.0
        self._last_attempt = 0.0

    # ---- bağlantı yönetimi ----
    def _ensure_open(self) -> bool:
        if self._ser is not None and self._ser.is_open:
            return True
        now = time.monotonic()
        if now - self._last_attempt < self.reconnect_delay_s:
            return False
        self._last_attempt = now
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=0.05)
            time.sleep(2.0)  # Arduino reset sonrası bootloader bekleme
            self._ser.reset_input_buffer()
            print(f"[serial] bağlandı: {self.port} @ {self.baud}")
            return True
        except (serial.SerialException, OSError) as e:
            print(f"[serial] bağlanılamadı ({e}); {self.reconnect_delay_s}s sonra tekrar")
            self._ser = None
            return False

    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    # ---- komut gönderimi ----
    def send(self, pan: int, tilt: int, eye_x: int, eye_y: int,
             laser: bool, force: bool = False) -> bool:
        """Komutu gönderir. command_hz hız sınırı uygulanır (force ile aşılır)."""
        now = time.monotonic()
        if not force and (now - self._last_send) < self.min_interval:
            return False
        if not self._ensure_open():
            return False

        line = f"T,{int(pan)},{int(tilt)},{int(eye_x)},{int(eye_y)},{1 if laser else 0}\n"
        try:
            self._ser.write(line.encode("ascii"))
            self._last_send = now
            # Arduino'nun "OK" yanıtını boşalt (birikmesin), bloklamadan.
            try:
                self._ser.reset_input_buffer()
            except OSError:
                pass
            return True
        except (serial.SerialException, OSError) as e:
            print(f"[serial] yazma hatası ({e}); bağlantı düşürülüyor")
            self.close()
            return False

    def close(self):
        if self._ser is not None:
            try:
                self._ser.close()
            except OSError:
                pass
        self._ser = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
