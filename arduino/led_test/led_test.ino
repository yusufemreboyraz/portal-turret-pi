/*
 * LED test sketch — ana firmware'i etkilemez.
 *
 * 4 namlu LED'ini bağımsız test eder. İçinde iki aşama vardır:
 *
 *  AŞAMA 1 (açılışta bir kez): SELF-TEST
 *    Her LED'i sırayla 400ms yakar (sol alt -> sol üst -> sağ alt -> sağ üst).
 *    Hangi pin hangi fiziksel LED'e gidiyor doğrula. Beklenen sırada
 *    yanmıyorsa pin haritası / kablolama yanlıştır.
 *
 *  AŞAMA 2 (sonsuz döngü): ATEŞ EFEKTİ
 *    Ana firmware'deki "F" koreografisinin AYNISI ~600ms boyunca oynatılır,
 *    sonra ~1.2s sönük bekler, sonra tekrar — sürekli ateş gösterisi.
 *    Sonsuz döngüde olduğu için reset/kapat ile durdurursun.
 *
 * Pin haritası (her LED için 470Ω SERİ DİRENÇ şart — Uno R4 pini ~8mA):
 *   pin 2  -> sol alt   (LL)
 *   pin 3  -> sol üst   (LU)
 *   pin 12 -> sağ alt   (RL)
 *   pin 13 -> sağ üst   (RU)
 *   her LED katodu (-) ortak GND -> Arduino GND
 *
 * Kullanım:
 *   Arduino IDE -> bu .ino'yu aç -> Upload.
 *   Servolara/seri köprüye dokunmaz; bağlı kalmaları sorun değil ama hareket
 *   etmezler (bu sketch onları sürmüyor).
 */

// ---- Pin haritası (ana firmware ile birebir aynı) ----
const int PIN_LED_LL = 2;
const int PIN_LED_LU = 3;
const int PIN_LED_RL = 12;
const int PIN_LED_RU = 13;

// ---- Ateş efekti zamanlaması ----
const unsigned long FIRE_MS      = 600;   // toplam efekt süresi
const unsigned long GAP_MS       = 1200;  // ateşler arası bekleme
const unsigned long BURST_MS     = 75;    // her bir patlama uzunluğu
const unsigned long BURST_ON_MS  = 55;    // patlamanın açık olduğu kısım (parıltı)

// Bit maskesi: bit0=LL, bit1=LU, bit2=RL, bit3=RU
void setLeds(uint8_t mask) {
  digitalWrite(PIN_LED_LL, (mask & 0b0001) ? HIGH : LOW);
  digitalWrite(PIN_LED_LU, (mask & 0b0010) ? HIGH : LOW);
  digitalWrite(PIN_LED_RL, (mask & 0b0100) ? HIGH : LOW);
  digitalWrite(PIN_LED_RU, (mask & 0b1000) ? HIGH : LOW);
}

// 8 ardışık patlama deseni (ana firmware ile aynı).
const uint8_t FIRE_PATTERN[8] = {
  0b0011, // sol alt + sol üst
  0b1100, // sağ alt + sağ üst
  0b1010, // üst çapraz (LU + RU)
  0b1111, // hepsi (büyük flash)
  0b0101, // alt çapraz (LL + RL)
  0b0011,
  0b1100,
  0b1111
};

void runFireSequence() {
  unsigned long start = millis();
  while (true) {
    unsigned long el = millis() - start;
    if (el >= FIRE_MS) break;
    int b = (int)(el / BURST_MS);
    if (b > 7) b = 7;
    bool gate = (el % BURST_MS) < BURST_ON_MS;
    setLeds(gate ? FIRE_PATTERN[b] : 0);
    delay(2);  // CPU'yu yakmamak için mini gecikme
  }
  setLeds(0);
}

void selfTest() {
  const int pins[4]      = { PIN_LED_LL, PIN_LED_LU, PIN_LED_RL, PIN_LED_RU };
  const char *names[4]   = { "LL (sol alt)", "LU (sol ust)",
                             "RL (sag alt)", "RU (sag ust)" };
  Serial.println(F("[self-test] her LED sirayla 400ms yanacak..."));
  for (int i = 0; i < 4; i++) {
    Serial.print(F("  -> ")); Serial.println(names[i]);
    digitalWrite(pins[i], HIGH);
    delay(400);
    digitalWrite(pins[i], LOW);
    delay(120);
  }
  Serial.println(F("[self-test] tamam. Ates efekti dongusu basliyor."));
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_LL, OUTPUT);
  pinMode(PIN_LED_LU, OUTPUT);
  pinMode(PIN_LED_RL, OUTPUT);
  pinMode(PIN_LED_RU, OUTPUT);
  setLeds(0);
  delay(300);
  selfTest();
}

void loop() {
  Serial.println(F("[fire]"));
  runFireSequence();
  delay(GAP_MS);
}
