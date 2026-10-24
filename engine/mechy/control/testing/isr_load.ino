/* ISR load self-test (tests only): wraps mechy_arm.ino, measures how much CPU the step
 * interrupt takes, idle and with all four motors cruising at their V_MAX_STEPS, by counting
 * busy-loop iterations in 200 ms windows. Run on simavr; prints one SELFTEST line. */
#define setup fw_setup
#define loop fw_loop
#include "mechy_arm_impl.h"
#undef setup
#undef loop

static uint32_t spin(uint16_t ms) {
  uint32_t n = 0;
  uint32_t t0 = millis();
  while (millis() - t0 < ms) {
    n++;
    __asm__ __volatile__("nop");
  }
  return n;
}

void setup() {
  fw_setup();
  Serial.flush();
  uint8_t t = TIMSK1;
  TIMSK1 = 0;
  uint32_t base = spin(200);
  TIMSK1 = t;
  uint32_t idle = spin(200);
  int32_t tgt[N_MOTORS];
  for (uint8_t m = 0; m < N_MOTORS; m++) tgt[m] = (int32_t)(V_MAX_STEPS[m] * 3.0f);
  float T;
  uint8_t st;
  start_segment(tgt, 0.01f, &T, &st);
  delay(1000);                                  /* well into cruise */
  int32_t p0[N_MOTORS], p1[N_MOTORS];
  read_pos(p0);
  uint32_t busy = spin(200);
  read_pos(p1);
  Serial.print(F("SELFTEST base="));
  Serial.print(base);
  Serial.print(F(" idle="));
  Serial.print(idle);
  Serial.print(F(" busy="));
  Serial.print(busy);
  Serial.print(F(" T="));
  Serial.print(T, 3);
  Serial.print(F(" rates="));
  for (uint8_t m = 0; m < N_MOTORS; m++) {
    if (m) Serial.print(',');
    Serial.print((long)((p1[m] - p0[m]) * 5));
  }
  Serial.print('\n');
  Serial.flush();
  cli();                                        /* simavr exits on sleep with interrupts off */
  SMCR = _BV(SE);
  __asm__ __volatile__("sleep");
}

void loop() {}
