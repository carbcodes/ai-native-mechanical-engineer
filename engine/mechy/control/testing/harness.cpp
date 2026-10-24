/*
 * PC harness for mechy_arm.ino (tests only). Compile:
 *   g++ -O2 -I arduino_mock -I <firmware dir> harness.cpp -o harness
 * Run: harness <script> <t_end_s> q0 q1 q2 q3
 *   script lines: "<time_s> <command line>" fed to the firmware's serial input.
 *   q0..q3: the arm's true starting joint angles (rad), unknown to the firmware.
 * The physical motors move one step per STEP pulse in the direction set by their DIR pin
 * (HIGH = positive). Limit switches (HOME_KIND 0) close when the true joint angle passes
 * HOME_POS in HOME_DIR. Index sensors (KIND 1) close inside a window of MOCK_INDEX_WIDTH rad
 * centred on HOME_POS, in the coordinate they read (q_j, or motor angle a_k when HOME_COORD = k).
 * Env MOCK_DEAD_SENSOR=j makes sensor j never close. Output: "<t> <serial line>" for every firmware line, then "RESULT ..." lines.
 */
#include "Arduino.h"
#include <string>
#include <vector>
#include <deque>

volatile uint8_t PORTA, PORTB, PORTC, PORTD, PORTF, PORTL;
volatile uint8_t SREG, TCCR1A, TCCR1B, TIMSK1, TIFR1;
volatile uint16_t TCNT1, OCR1A;
MockSerial Serial;

static double now_s = 0;
static std::deque<char> serial_in;
static std::string serial_out;
static uint8_t pin_level[256];

void cli() {}
void sei() {}
void pinMode(uint8_t, uint8_t) {}
void digitalWrite(uint8_t pin, uint8_t v) { pin_level[pin] = v; }
void delayMicroseconds(unsigned int) {}
unsigned long millis() { return (unsigned long)(now_s * 1000); }
unsigned long micros() { return (unsigned long)(now_s * 1e6); }
int MockSerial::available() { return (int)serial_in.size(); }
int MockSerial::read() { if (serial_in.empty()) return -1; char c = serial_in.front(); serial_in.pop_front(); return c; }
void MockSerial::print(const char *s) { serial_out += s; }
void MockSerial::print(char c) { serial_out += c; }
void MockSerial::print(int v) { serial_out += std::to_string(v); }
void MockSerial::print(long v) { serial_out += std::to_string(v); }
void MockSerial::print(unsigned long v) { serial_out += std::to_string(v); }
void MockSerial::print(double v, int d) { char b[64]; snprintf(b, sizeof b, "%.*f", d, v); serial_out += b; }

#include "mechy_arm.ino"

static double theta[4];            /* true joint-side motor angles (rad) */
static long phys_steps[4];
static long pulses[4];
static double q_true[4];
static std::vector<int> bucket[4]; /* step pulses per 1 ms */

static void update_q_true() {
  for (int j = 0; j < 4; j++) {
    double s = 0;
    for (int m = 0; m < 4; m++) s += MAP_MINV[j][m] * theta[m];
    q_true[j] = s;
  }
}

void _delay_us(double) {
  uint8_t hit[4] = {
    (uint8_t)((STEP0_PORT & _BV(STEP0_BIT)) != 0), (uint8_t)((STEP1_PORT & _BV(STEP1_BIT)) != 0),
    (uint8_t)((STEP2_PORT & _BV(STEP2_BIT)) != 0), (uint8_t)((STEP3_PORT & _BV(STEP3_BIT)) != 0)};
  const uint8_t dirs[4] = {DIR0_PIN, DIR1_PIN, DIR2_PIN, DIR3_PIN};
  size_t b = (size_t)(now_s * 1000);
  for (int i = 0; i < 4; i++) {
    if (!hit[i]) continue;
    int d = pin_level[dirs[i]] ? 1 : -1;
    phys_steps[i] += d;
    pulses[i]++;
    theta[i] += d / STEPS_PER_RAD[i];
    if (bucket[i].size() <= b) bucket[i].resize(b + 1, 0);
    bucket[i][b]++;
  }
  update_q_true();
}

#ifndef MOCK_INDEX_WIDTH
#define MOCK_INDEX_WIDTH 0.12      /* ~7 deg: a 5 mm magnet passing an A3144 */
#endif
static int dead_sensor = -1;

int digitalRead(uint8_t pin) {
  for (int j = 0; j < 4; j++) {
    if (pin == SWITCH_PINS[j]) {
      bool pressed;
      if (HOME_KIND[j] == 0) {
        pressed = HOME_DIR[j] * (q_true[j] - HOME_POS[j]) >= 0;
      } else {
        double c = HOME_COORD[j] == 255 ? q_true[j] : theta[HOME_COORD[j]];
        pressed = fabs(c - HOME_POS[j]) <= 0.5 * MOCK_INDEX_WIDTH;
      }
      if (j == dead_sensor) pressed = false;
      return SWITCH_ACTIVE_LOW ? (pressed ? LOW : HIGH) : (pressed ? HIGH : LOW);
    }
  }
  return HIGH;  /* e-stop open */
}

int main(int argc, char **argv) {
  if (argc < 7) { fprintf(stderr, "usage: harness script t_end q0 q1 q2 q3\n"); return 2; }
  FILE *f = fopen(argv[1], "r");
  if (!f) return 2;
  std::vector<std::pair<double, std::string>> script;
  char buf[256];
  while (fgets(buf, sizeof buf, f)) {
    double t;
    int n = 0;
    if (sscanf(buf, "%lf %n", &t, &n) >= 1) script.push_back({t, std::string(buf + n)});
  }
  fclose(f);
  double t_end = atof(argv[2]);
  if (getenv("MOCK_DEAD_SENSOR")) dead_sensor = atoi(getenv("MOCK_DEAD_SENSOR"));
  double q0[4];
  for (int j = 0; j < 4; j++) q0[j] = atof(argv[3 + j]);
  for (int m = 0; m < 4; m++) {
    double s = 0;
    for (int j = 0; j < 4; j++) s += MAP_M[m][j] * q0[j];
    theta[m] = s;
  }
  update_q_true();
  setup();
  size_t next = 0;
  const double dt = 1.0 / TICK_HZ;
  long ticks = (long)(t_end * TICK_HZ);
  for (long k = 0; k < ticks; k++) {
    now_s = k * dt;
    while (next < script.size() && script[next].first <= now_s) {
      for (char c : script[next].second) serial_in.push_back(c);
      next++;
    }
    if (TIMSK1 & _BV(OCIE1A)) TIMER1_COMPA_vect();
    loop();
    size_t p;
    while ((p = serial_out.find('\n')) != std::string::npos) {
      printf("%.5f %s\n", now_s, serial_out.substr(0, p).c_str());
      serial_out.erase(0, p + 1);
    }
  }
  printf("RESULT q_true %.6f %.6f %.6f %.6f\n", q_true[0], q_true[1], q_true[2], q_true[3]);
  printf("RESULT pos %ld %ld %ld %ld\n", (long)motor_pos[0], (long)motor_pos[1], (long)motor_pos[2], (long)motor_pos[3]);
  printf("RESULT phys %ld %ld %ld %ld\n", phys_steps[0], phys_steps[1], phys_steps[2], phys_steps[3]);
  printf("RESULT pulses %ld %ld %ld %ld\n", pulses[0], pulses[1], pulses[2], pulses[3]);
  /* peak step rate over a sliding 5 ms window and peak change of 5 ms-average rate */
  for (int i = 0; i < 4; i++) {
    int best = 0;
    for (size_t b = 0; b + 5 <= bucket[i].size(); b++) {
      int s = 0;
      for (int k = 0; k < 5; k++) s += bucket[i][b + k];
      if (s > best) best = s;
    }
    printf("RESULT rate%d %.1f\n", i, best / 0.005);
  }
  return 0;
}
