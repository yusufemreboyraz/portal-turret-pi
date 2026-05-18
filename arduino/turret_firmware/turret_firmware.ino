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
const int PIN_PAN   = 9;
const int PIN_TILT  = 10;
const int PIN_EYEX  = 5;
const int PIN_EYEY  = 6;
const int PIN_LASER = 7;

// ---- Ayarlar ----
const unsigned long BAUD          = 115200;
const unsigned long LOOP_MS       = 15;     // servo güncelleme periyodu
const float         MAX_STEP_DEG  = 3.0;    // döngü başına max açı değişimi (slew)
const unsigned long FAILSAFE_MS   = 500;    // bu süre komut gelmezse merkeze dön
const int           CENTER        = 90;

Servo sPan, sTilt, sEyeX, sEyeY;

// Hedef ve mevcut açılar (float = pürüzsüz slew)
float tgtPan = CENTER, tgtTilt = CENTER, tgtEyeX = CENTER, tgtEyeY = CENTER;
float curPan = CENTER, curTilt = CENTER, curEyeX = CENTER, curEyeY = CENTER;
int   laserState = 0;

unsigned long lastCmdMs = 0;
unsigned long lastLoopMs = 0;

char  buf[48];
uint8_t bufLen = 0;

int clampAngle(int a) {
  if (a < 0)   return 0;
  if (a > 180) return 180;
  return a;
}

// curr'i tgt'ye doğru en fazla MAX_STEP_DEG kadar yaklaştır.
float slew(float cur, float tgt) {
  float d = tgt - cur;
  if (d >  MAX_STEP_DEG) d =  MAX_STEP_DEG;
  if (d < -MAX_STEP_DEG) d = -MAX_STEP_DEG;
  return cur + d;
}

void applyCommand(char *line) {
  // Beklenen: T,pan,tilt,eyeX,eyeY,laser
  if (line[0] != 'T') return;
  char *p = strtok(line, ",");          // "T"
  char *sp = strtok(NULL, ",");
  char *st = strtok(NULL, ",");
  char *sx = strtok(NULL, ",");
  char *sy = strtok(NULL, ",");
  char *sl = strtok(NULL, ",");
  if (!sp || !st || !sx || !sy || !sl) return;

  tgtPan  = clampAngle(atoi(sp));
  tgtTilt = clampAngle(atoi(st));
  tgtEyeX = clampAngle(atoi(sx));
  tgtEyeY = clampAngle(atoi(sy));
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

  sPan.attach(PIN_PAN);
  sTilt.attach(PIN_TILT);
  sEyeX.attach(PIN_EYEX);
  sEyeY.attach(PIN_EYEY);

  sPan.write(CENTER);
  sTilt.write(CENTER);
  sEyeX.write(CENTER);
  sEyeY.write(CENTER);

  lastCmdMs = millis();
}

void loop() {
  readSerial();

  unsigned long now = millis();
  if (now - lastLoopMs < LOOP_MS) return;
  lastLoopMs = now;

  // Failsafe: Pi sustuysa güvenli merkeze dön, lazeri kapat.
  if (now - lastCmdMs > FAILSAFE_MS) {
    tgtPan = tgtTilt = tgtEyeX = tgtEyeY = CENTER;
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
}
