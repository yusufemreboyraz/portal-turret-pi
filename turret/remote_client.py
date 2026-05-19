"""
Turret Uzak İstemci (Remote Client)

Bu script, Raspberry Pi üzerinde çalışan Turret'ten gelen:
1. GStreamer video yayınını izleme komutunu gösterir.
2. UDP üzerinden gelen ses tetikleyicilerini dinler ve kendi hoparlörünüzden çalar.

Gereksinimler:
pip install pygame

GStreamer Kurulumu:
- Windows: GStreamer MSVC sürümünü indirin ve kurun. (PATH'e eklendiğinden emin olun)
- Mac: brew install gstreamer
- Linux: sudo apt install gstreamer1.0-tools

Çalıştırmak için:
python remote_client.py
"""

import os
import socket
import sys
import threading
import time
import random

try:
    import pygame
except ImportError:
    print("Hata: pygame modülü bulunamadı. Lütfen yükleyin: pip install pygame")
    sys.exit(1)

# Ayarlar (config.yaml'daki ile eşleşmeli)
UDP_IP = "0.0.0.0"  # Tüm ağ arayüzlerini dinle
UDP_PORT = 5001

# Ses dizini
HERE = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(HERE, "sounds")

SOUND_FILES = {
    "found": ["TargetFound/ISeeYou.wav", "TargetFound/ThereYouAre.wav", "TargetFound/Acquired.wav"],
    "lock": ["TargetFound/Gotcha.wav", "Fire.wav", "Fire/FireShort.wav"],
    "lost": ["TargetLost/AreYouStillThere.wav", "TargetLost/TargetLost.wav"]
}

def play_sound(group):
    files = SOUND_FILES.get(group, [])
    if not files:
        return
    
    # Geçerli dosyaları filtrele
    valid_files = [os.path.join(SOUNDS_DIR, f) for f in files if os.path.isfile(os.path.join(SOUNDS_DIR, f))]
    if not valid_files:
        print(f"[uyarı] '{group}' için ses dosyası bulunamadı. Lütfen '{SOUNDS_DIR}' dizinini Turret projesinden bu bilgisayara kopyaladığınızdan emin olun.")
        return

    path = random.choice(valid_files)
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"[hata] Ses çalınamadı: {e}")

def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"\n[SES] UDP Dinleniyor: Port {UDP_PORT} ...")
    
    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode('utf-8').strip()
        print(f"[{addr[0]}] Tetikleyici geldi: {msg}")
        play_sound(msg)

def main():
    pygame.mixer.init()
    
    print("="*60)
    print(" PORTAL TURRET UZAKTAN İZLEYİCİ İSTEMCİSİ")
    print("="*60)
    print("\n1. GÖRÜNTÜYÜ İZLEMEK İÇİN YENİ BİR TERMİNAL AÇIP ŞU KOMUTU GİRİN:")
    print("gst-launch-1.0 udpsrc port=5000 caps=\"application/x-rtp, media=video, clock-rate=90000, encoding-name=H264\" ! rtph264depay ! decodebin ! videoconvert ! autovideosink")
    print("\n2. SESLER:")
    print("Bu pencere açık kaldığı sürece, Turret'ten gelen sesleri hoparlörünüzden duyacaksınız.")
    
    # UDP dinleyicisini ayrı bir thread'de başlat
    listener_thread = threading.Thread(target=udp_listener, daemon=True)
    listener_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nÇıkış yapılıyor...")
        pygame.mixer.quit()
        sys.exit(0)

if __name__ == "__main__":
    main()
