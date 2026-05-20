/*
 * Portal Turret firmware — Arduino Uno R4 (Minima/WiFi).
 *
 * Görevi "aptal" olmak: Pi'den seri ile gelen hedef açıları slew-rate
 * limitli uygular, lazeri yönetir, komut kesilirse güvenli duruşa geçer.
 * Tüm zekâ (görüntü, kalibrasyon, durum makinesi) Pi tarafında.
 *
 * Protokol (Pi -> Arduino), satır sonu '\n':
 *   T,<pan>,<tilt>,<eyeX>,<eyeY>,<laser>
 *   açılar 0-180 tamsayı, laser 0/1
 * Örnek:  T,90,90,90,90,1
 *
 * Arduino -> Pi: her komutta "OK\n" (Pi heartbeat doğrulaması için, isteğe bağlı).
 *
 * GÜÇ: Servolar AYRI 5-6V kaynaktan beslenir. Arduino GND <-> servo GND ortak.
 *      Servo V+ KESİNLİKLE Arduino 5V pininden çekilmez (MG996R stall ~2A).
 */

#include <Servo.h>

// ---- Pin haritası ----
const int PIN_PAN     = 9;
const int PIN_TILT    = 10;
const int PIN_EYEX    = 5;
const int PIN_EYEY    = 6;
const int PIN_LASER   = 7;
// Namlu LED'leri (her LED için 470Ω seri direnç!)
const int PIN_LED_LL  = 2;   // sol alt
const int PIN_LED_LU  = 3;   // sol üst
const int PIN_LED_RL  = 12;  // sağ alt
const int PIN_LED_RU  = 13;  // sağ üst

// ---- Ayarlar ----
const unsigned long BAUD          = 115200;
const unsigned long LOOP_MS       = 15;     // servo güncelleme periyodu
const float         MAX_STEP_DEG  = 3.0;    // döngü başına max açı değişimi (slew)
const unsigned long FAILSAFE_MS   = 500;    // bu süre komut gelmezse merkeze dön
const unsigned long FIRE_MS       = 600;    // ateş efekti toplam süresi

// Her servonun KENDİ güvenli merkezi. Açılışta ve komut kesilince
// (failsafe) servolar buraya yumuşakça gelir. Göz değerleri elle ölçüldü:
// eyeX 55(sol)-135(sağ), eyeY 0(yukarı)-70(aşağı).
const int CEN_PAN  = 90;   // yeni mekanik merkez (genişlik 70)
const int CEN_TILT = 90;   // yeni mekanik merkez (genişlik 110)
const int CEN_EYEX = 95;   // sol55-sağ135 ortası
const int CEN_EYEY = 35;   // yukarı0-aşağı70 ortası

// GÜVENLİ KENAR LİMİTLERİ — firmware bu aralık DIŞINA asla çıkmaz.
// (Ne gelirse gelsin servo zorlanmaz; çift güvenlik.)
// Göz değerleri ölçüldü. Pan/Tilt GEÇİCİ tahmin — büyük servo testinden
// sonra gerçek ölçümle güncellenecek.
const int PAN_MIN  = 55,  PAN_MAX  = 125;   // merkez 90, genişlik 70
const int TILT_MIN = 35,  TILT_MAX = 145;   // merkez 90, genişlik 110
const int EYEX_MIN = 55,  EYEX_MAX = 135;
const int EYEY_MIN = 0,   EYEY_MAX = 70;

Servo sPan, sTilt, sEyeX, sEyeY;

// Hedef ve mevcut açılar (float = pürüzsüz slew)
float tgtPan = CEN_PAN, tgtTilt = CEN_TILT, tgtEyeX = CEN_EYEX, tgtEyeY = CEN_EYEY;
float curPan = CEN_PAN, curTilt = CEN_TILT, curEyeX = CEN_EYEX, curEyeY = CEN_EYEY;
int   laserState = 0;

// true: güvenli kenar limitleri uygulanır (normal/main.py).
// false: ham mod, sadece mutlak 0-180 (serial_test ile sınır bulma).
// "L,0" / "L,1" komutuyla değişir; varsayılan güvenli (true).
bool  limitsOn = true;

// Ateş efekti durumu — "F" komutu ile tetiklenir.
unsigned long fireStartMs = 0;
bool          fireActive  = false;

unsigned long lastCmdMs = 0;
unsigned long lastLoopMs = 0;

char  buf[48];
uint8_t bufLen = 0;

int clampRange(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

// curr'i tgt'ye doğru en fazla MAX_STEP_DEG kadar yaklaştır.
float slew(float cur, float tgt) {
  float d = tgt - cur;
  if (d >  MAX_STEP_DEG) d =  MAX_STEP_DEG;
  if (d < -MAX_STEP_DEG) d = -MAX_STEP_DEG;
  return cur + d;
}

void attachAll() {
  sPan.attach(PIN_PAN);
  sTilt.attach(PIN_TILT);
  sEyeX.attach(PIN_EYEX);
  sEyeY.attach(PIN_EYEY);
}

void setLeds(uint8_t mask) {
  digitalWrite(PIN_LED_LL, (mask & 0b0001) ? HIGH : LOW);
  digitalWrite(PIN_LED_LU, (mask & 0b0010) ? HIGH : LOW);
  digitalWrite(PIN_LED_RL, (mask & 0b0100) ? HIGH : LOW);
  digitalWrite(PIN_LED_RU, (mask & 0b1000) ? HIGH : LOW);
}

// Sahnedeki ateş efekti — millis() tabanlı, blocking değil.
// 8 ardışık "patlama", her biri ~75ms; %~73 açık, %27 kapalı (parıltı hissi).
void updateFireFx(unsigned long now) {
  if (!fireActive) return;
  unsigned long el = now - fireStartMs;
  if (el >= FIRE_MS) {
    fireActive = false;
    setLeds(0);
    return;
  }
  static const uint8_t pat[8] = {
    0b0011, // sol alt+üst
    0b1100, // sağ alt+üst
    0b1010, // üst çapraz (LU+RU)
    0b1111, // hepsi (büyük flash)
    0b0101, // alt çapraz (LL+RL)
    0b0011,
    0b1100,
    0b1111
  };
  int b = (int)(el / 75); if (b > 7) b = 7;
  bool gate = (el % 75) < 55;          // ışıklar her patlamada kısa söner
  setLeds(gate ? pat[b] : 0);
}

void applyCommand(char *line) {
  // "F" -> ateş efektini başlat
  if (line[0] == 'F') {
    fireStartMs = millis();
    fireActive = true;
    return;
  }

  // "L,<0|1>" -> limit modunu değiştir (0=ham, 1=güvenli)
  if (line[0] == 'L') {
    strtok(line, ",");
    char *lv = strtok(NULL, ",");
    if (lv) {
      limitsOn = (atoi(lv) != 0);
      Serial.println(limitsOn ? "LIM_ON" : "LIM_OFF");
    }
    return;
  }

  // "T,pan,tilt,eyeX,eyeY,laser"
  if (line[0] != 'T') return;
  strtok(line, ",");                    // "T"
  char *sp = strtok(NULL, ",");
  char *st = strtok(NULL, ",");
  char *sx = strtok(NULL, ",");
  char *sy = strtok(NULL, ",");
  char *sl = strtok(NULL, ",");
  if (!sp || !st || !sx || !sy || !sl) return;

  // limitsOn ? güvenli kenarlar : sadece mutlak 0-180
  int pLo = limitsOn ? PAN_MIN  : 0, pHi = limitsOn ? PAN_MAX  : 180;
  int tLo = limitsOn ? TILT_MIN : 0, tHi = limitsOn ? TILT_MAX : 180;
  int xLo = limitsOn ? EYEX_MIN : 0, xHi = limitsOn ? EYEX_MAX : 180;
  int yLo = limitsOn ? EYEY_MIN : 0, yHi = limitsOn ? EYEY_MAX : 180;

  tgtPan  = clampRange(atoi(sp), pLo, pHi);
  tgtTilt = clampRange(atoi(st), tLo, tHi);
  tgtEyeX = clampRange(atoi(sx), xLo, xHi);
  tgtEyeY = clampRange(atoi(sy), yLo, yHi);
  laserState = atoi(sl) ? 1 : 0;

  lastCmdMs = millis();
  Serial.println("OK");
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (bufLen > 0) {
        buf[bufLen] = '\0';
        applyCommand(buf);
        bufLen = 0;
      }
    } else if (bufLen < sizeof(buf) - 1) {
      buf[bufLen++] = c;
    } else {
      bufLen = 0; // taşma -> satırı at
    }
  }
}

void setup() {
  Serial.begin(BAUD);

  pinMode(PIN_LASER, OUTPUT);
  digitalWrite(PIN_LASER, LOW);

  pinMode(PIN_LED_LL, OUTPUT);
  pinMode(PIN_LED_LU, OUTPUT);
  pinMode(PIN_LED_RL, OUTPUT);
  pinMode(PIN_LED_RU, OUTPUT);
  setLeds(0);

  // Açılışta belirlenen GÜVENLİ merkeze al ve orada tut.
  curPan = tgtPan = CEN_PAN;
  curTilt = tgtTilt = CEN_TILT;
  curEyeX = tgtEyeX = CEN_EYEX;
  curEyeY = tgtEyeY = CEN_EYEY;

  attachAll();
  sPan.write(CEN_PAN);
  sTilt.write(CEN_TILT);
  sEyeX.write(CEN_EYEX);
  sEyeY.write(CEN_EYEY);

  lastCmdMs = millis();
}

void loop() {
  readSerial();

  unsigned long now = millis();
  if (now - lastLoopMs < LOOP_MS) return;
  lastLoopMs = now;

  // Failsafe: komut kesilirse belirlenen GÜVENLİ merkeze yumuşakça dön,
  // lazeri kapat. (Merkezler ölçülerek doğrulandı, zorlama yok.)
  if (now - lastCmdMs > FAILSAFE_MS) {
    tgtPan = CEN_PAN; tgtTilt = CEN_TILT;
    tgtEyeX = CEN_EYEX; tgtEyeY = CEN_EYEY;
    laserState = 0;
  }

  curPan  = slew(curPan,  tgtPan);
  curTilt = slew(curTilt, tgtTilt);
  curEyeX = slew(curEyeX, tgtEyeX);
  curEyeY = slew(curEyeY, tgtEyeY);

  sPan.write((int)(curPan  + 0.5));
  sTilt.write((int)(curTilt + 0.5));
  sEyeX.write((int)(curEyeX + 0.5));
  sEyeY.write((int)(curEyeY + 0.5));

  digitalWrite(PIN_LASER, laserState ? HIGH : LOW);

  updateFireFx(now);
}
