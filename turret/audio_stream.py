"""Pi -> telefon basit ağ ses sunucusu.

Pi 5'te ses kartı/hoparlör yoksa: telefonu tarayıcı üzerinden hoparlör
gibi kullanır. Pi olay başlattığında (örn. "I see you") telefon o wav'ı
indirip çalar. Tek bağımlılık: Python stdlib (http.server + threading).

Kullanım:
    streamer = AudioStreamer(base_dir="/.../sounds", port=8765)
    streamer.start()
    streamer.play_file("TargetFound/ISeeYou.wav")

Telefondan:
    http://<pi-ip>:8765/ -> "Sesi Başlat"a bas, sayfa açık kalsın.
"""

from __future__ import annotations

import json
import mimetypes
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional

INDEX_HTML = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Portal Turret Speaker</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{font-family:system-ui;text-align:center;padding:1.5em;background:#0b0b0b;color:#eee}
  h1{margin:.2em 0}
  button{font-size:1.5em;padding:.7em 1.6em;border-radius:.5em;border:0;
         background:#ff8800;color:#000;cursor:pointer;font-weight:600}
  #status{margin:1em 0;color:#9c9}
  #log{font-size:.85em;color:#888;text-align:left;max-height:40vh;
       overflow:auto;background:#181818;padding:.5em;border-radius:.3em;margin-top:1em}
</style></head><body>
<h1>Portal Turret 🔊</h1>
<p>Telefon hoparlör modu. <b>Sayfayı kapatma</b>, ekranı uyandır.</p>
<button id="start">▶ Sesi Başlat</button>
<div id="status">Bekleniyor…</div>
<div id="log"></div>
<script>
const status = (m) => document.getElementById('status').textContent = m;
const log = (m) => { const d=document.createElement('div');
  d.textContent=new Date().toLocaleTimeString()+'  '+m;
  const el=document.getElementById('log'); el.prepend(d);
  while (el.children.length>60) el.removeChild(el.lastChild); };
let started = false;
let queueAudio = [];
// Çok kısa sessiz wav (autoplay kilidini click içinde açmak için)
const SILENT_WAV = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=';
document.getElementById('start').onclick = () => {
  started = true;
  document.getElementById('start').style.display='none';
  status('Aktif. Olaylar bekleniyor.');
  // User-gesture bağlamında bir ses çal -> autoplay kilidi açılır.
  const first = queueAudio.shift();
  const src = first ? ('/sounds/' + encodeURI(first)) : SILENT_WAV;
  const a = new Audio(src);
  a.play().then(()=>log('autoplay kilidi açıldı'))
          .catch(e=>log('başlatma: '+e));
  // Kalan kuyruğu boşalt
  while (queueAudio.length) {
    const f = queueAudio.shift();
    new Audio('/sounds/' + encodeURI(f)).play().catch(e=>log('hata: '+e));
  }
};
const es = new EventSource('/events');
es.onopen = () => status(started ? 'Aktif.' : 'Bağlandı — "Sesi Başlat"a bas.');
es.onerror = () => status('Bağlantı koptu, yeniden deniyor…');
es.onmessage = (e) => {
  let data; try { data = JSON.parse(e.data); } catch { return; }
  log('▶ ' + data.file);
  if (!started) { queueAudio.push(data.file); return; }
  const a = new Audio('/sounds/' + encodeURI(data.file));
  a.play().catch(err => log('oynatma: ' + err));
};
</script></body></html>
"""


class _Handler(BaseHTTPRequestHandler):
    server_version = "PortalTurret/1"

    def log_message(self, fmt, *args):  # sessiz
        pass

    def _streamer(self) -> "AudioStreamer":
        return self.server.streamer  # type: ignore[attr-defined]

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/events":
            self._serve_events()
            return

        if self.path.startswith("/sounds/"):
            self._serve_sound(self.path[len("/sounds/"):])
            return

        self.send_error(404)

    # ---- SSE (Server-Sent Events) ----
    def _serve_events(self):
        srv = self._streamer()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        q: "queue.Queue[dict]" = queue.Queue(maxsize=64)
        srv._add_client(q)
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    ev = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")  # keep-alive
                    self.wfile.flush()
                    continue
                self.wfile.write(("data: " + json.dumps(ev) + "\n\n").encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            srv._remove_client(q)

    # ---- statik wav servisi ----
    def _serve_sound(self, rel: str):
        srv = self._streamer()
        from urllib.parse import unquote

        rel = unquote(rel)
        norm = os.path.normpath(rel).lstrip("/").replace("\\", "/")
        if ".." in norm.split("/"):
            self.send_error(403)
            return
        full = os.path.join(srv.base_dir, norm)
        if not os.path.isfile(full):
            self.send_error(404)
            return
        ctype, _ = mimetypes.guess_type(full)
        ctype = ctype or "application/octet-stream"
        size = os.path.getsize(full)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "max-age=3600")
        self.end_headers()
        with open(full, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return


class AudioStreamer:
    def __init__(self, base_dir: str, host: str = "0.0.0.0", port: int = 8765):
        self.base_dir = os.path.abspath(base_dir)
        self.host = host
        self.port = port
        self._clients: List[queue.Queue] = []
        self._lock = threading.Lock()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    # ---- yaşam döngüsü ----
    def start(self):
        if self._server is not None:
            return
        try:
            srv = ThreadingHTTPServer((self.host, self.port), _Handler)
        except OSError as e:
            print(f"[audio] sunucu açılamadı ({self.host}:{self.port}): {e}")
            return
        srv.streamer = self  # type: ignore[attr-defined]
        self._server = srv
        self._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        self._thread.start()
        print(f"[audio] HTTP ses sunucusu: http://{self.host}:{self.port}/  "
              f"(telefonda bu adresi aç, 'Sesi Başlat'a bas)")

    def stop(self):
        if self._server is None:
            return
        try:
            self._server.shutdown()
            self._server.server_close()
        except Exception:  # noqa: BLE001
            pass
        self._server = None

    # ---- istemci yönetimi ----
    def _add_client(self, q: "queue.Queue[dict]"):
        with self._lock:
            self._clients.append(q)
        print(f"[audio] istemci bağlandı (toplam {len(self._clients)})")

    def _remove_client(self, q: "queue.Queue[dict]"):
        with self._lock:
            try:
                self._clients.remove(q)
            except ValueError:
                pass
        print(f"[audio] istemci ayrıldı (toplam {len(self._clients)})")

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    # ---- çalma ----
    def play_file(self, rel_path: str):
        """rel_path: base_dir'e göreceli wav (örn 'TargetFound/ISeeYou.wav')."""
        ev = {"file": rel_path, "ts": time.time()}
        with self._lock:
            clients = list(self._clients)
        for q in clients:
            try:
                q.put_nowait(ev)
            except queue.Full:
                pass
