# Portal Turret — Raspberry Pi 5 + Arduino Uno R4

Pan-tilt turret: Pi 5 kameradan insanı tespit eder, tareti ona yönlendirir,
lazer sürekli yanık, ateş yerine hoparlörden Portal ses replikleri çalar.

- **Pi 5 (8GB):** görüntü işleme (picamera2 + YOLO), durum makinesi, ses, Arduino'ya komut
- **Arduino Uno R4:** 4 servo + lazer kontrolü, slew-rate limit, failsafe
- **Servolar:** 2× MG996R (silah pan/tilt), 2× SG90-sınıfı (göz)

```
turret/   -> Pi tarafı (Python)
arduino/  -> Arduino firmware (.ino)
```

## 1. Donanım & kablolama

```
[Pi Kamera CSI] → [Raspberry Pi 5] ──USB seri──> [Arduino Uno R4] ──PWM──> 4× Servo
                          │                              │  pin 9=pan 10=tilt
                   [USB ses kartı]                       │  pin 5=eyeX 6=eyeY
                          │                              └─ pin 7 = lazer (sürekli)
                   [PAM8403 amfi] → [8Ω 1W hoparlör]
```

Arduino pin haritası `arduino/turret_firmware/turret_firmware.ino` içinde.

### Güç (EN KRİTİK — yanlışı kart yakar)
- **Pi 5:** prizden, resmi **27W USB-C PD** adaptör. (1S 3.7V 3000mAh batarya
  Pi 5 + YOLO için yetersiz, kullanma.)
- **Servolar:** AYRI **5-6V regüleli kaynak, ≥6A** (2× MG996R stall ~4A).
  Servo V+ KESİNLİKLE Arduino 5V pininden çekilmez.
- **Ortak GND zorunlu:** servo kaynağı GND ↔ Arduino GND. (Pi, USB ile zaten ortak.)
- **Lazer:** sürekli yanık; modül 5V hattına (gerekirse seri direnç).
- **Ses:** Pi 5'te 3.5mm jak YOK. USB ses kartı → PAM8403 → 8Ω hoparlör.
  *Alternatif (tek modül): MAX98357A I2S amfi doğrudan GPIO'dan 8Ω sürer.*

## 2. Arduino kurulumu

1. Arduino IDE'de **Renesas Arduino Uno R4** kart paketini kur.
2. `arduino/turret_firmware/turret_firmware.ino` dosyasını yükle.
3. Servoları ayrı güçten besle, Arduino'yu Pi'ye USB ile bağla.

## 3. Raspberry Pi kurulumu

Raspberry Pi OS **Bookworm 64-bit**:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv
cd turret
python3 -m venv --system-site-packages venv   # picamera2 sistemden gelsin
source venv/bin/activate
pip install -r requirements.txt
```

Kamerayı etkinleştir (`raspi-config` → Interface → Camera) ve test et:
`libcamera-hello`.

**Ses çıkışını USB karta yönlendir:** `aplay -l` ile kart no'sunu bul,
`~/.asoundrc` veya `raspi-config` Audio'dan varsayılan yap. Test: `speaker-test -c2`.

**Seri port:** `ls /dev/ttyACM*` → `config.yaml` `serial.port` değerini güncelle.

## 4. Bring-up sırası (plan adımları)

```bash
# 4a. Arduino izole testi — servolar hareket ediyor mu?
python3 serial_test.py 90 90 90 90 1     # hepsi merkez + lazer
python3 serial_test.py sweep             # pan mekanik süpürme
#  -> komut kesilince ~500ms sonra servolar merkeze dönmeli (failsafe)

# 4b. Kamera + tespit + FPS
#  config.yaml debug.show_window: true (masaüstü/VNC ile)
python3 main.py                          # insan kutulanmalı, FPS >= 15 hedef

# 4c. Kalibrasyon (kamera sabit, silah hareketli -> şart)
python3 calibrate.py
#  servoları klavyeyle oynat, lazeri bir noktaya getir, o noktaya tıkla;
#  uçlardan 2+ nokta topla, 'S' ile config.yaml'a yaz

# 4d. Tam sistem
python3 main.py
```

## 5. Ayarlar

Her şey `turret/config.yaml` içinde: servo limitleri, kalibrasyon,
yumuşatma (titreme), durum zamanlayıcıları (found/lost/reacquire),
ses dosyaları, tespit backend (`yolo` veya hafif `mediapipe`).

## 6. Doğrulama kontrol listesi

- [ ] Servo kaynağı yük altında ≥4.8V (multimetre), Pi brownout yok
- [ ] `serial_test.py` ile servolar merkez + lazer; 500ms sonra failsafe merkez
- [ ] `main.py` insanı kutuluyor, FPS ≥ 15
- [ ] Kalibrasyon sonrası lazer bir kişiye ±birkaç cm isabet
- [ ] Kişi gir/çık → ACQUIRED→TRACKING→LOST + doğru Portal sesleri
- [ ] Gezerken takip yumuşak (titremesiz), lazer hedefte

## Notlar

- Eski Instructables/Windows kodu kullanılmadı (2013-2014, Pi'de çalışmaz).
  Yalnızca mantığı (115200 baud, found/lost/reacquire zamanlayıcı) ve Portal
  `.wav` sesleri modern mimaride yeniden yazıldı.
- Pi'siz geliştirmede `vision.Camera` otomatik USB webcam'e (OpenCV) düşer.
