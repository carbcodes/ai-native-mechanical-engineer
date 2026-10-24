/*
 * mechy_arm.ino - firmware for the Mechy 4-joint catching arm.
 *
 * Hardware: 4 NEMA 17 steppers on A4988 step/dir drivers, one homing sensor per joint (limit
 * switch or hall index, see config.h HOME_KIND),
 * Arduino Uno + CNC Shield V3 or Arduino Mega 2560 + RAMPS 1.4 (pins in config.h, which
 * `mechy control gen` writes from params.yaml, hw/motors.yaml and hw/drivers.yaml). No libraries.
 *
 * Motion: a MOVE gives 4 joint angles and an arrival time. The firmware converts joint angles
 * to motor steps (joint->motor mapping for belt pass-through, gear ratios, microsteps), then
 * runs ONE trapezoidal profile s(t) shared by all four motors, so they start and arrive
 * together. Timer1 interrupts at TICK_HZ; each tick advances a virtual master axis of
 * max|steps| steps (Q24 fixed-point rate), and every motor steps by Bresenham against the
 * master, so the step counts are exact. The rate is updated every TICKS_PER_UPDATE ticks
 * (1 kHz) from the precomputed accel / cruise / decel phases. If the requested time would
 * exceed any motor's speed cap (V_MAX_STEPS) or acceleration cap (A_MAX_STEPS), the move is
 * stretched to the shortest feasible time and the reply says so (OK MOVE T=... stretched=1).
 *
 * Step-rate ceiling (16 MHz AVR, Uno or Mega): one step per motor per tick at most, so the
 * hard ceiling is TICK_HZ (20 kHz) per motor. Measured on simavr (ATmega328P, 16 MHz): with
 * all 4 motors at ~2-4 k steps/s the interrupt takes ~28% of the CPU; a tick that steps
 * costs ~650 of the 800 cycles available, one that does not ~110. So a realistic ceiling
 * with all 4 motors stepping is ~8-10 k steps/s per motor (about half the CPU), with
 * ~1 tick (50 us) of step jitter. The interrupt is off while no move runs. config.h caps each motor at max_step_rate_hz from hw/drivers.yaml
 * (4000 by default), which leaves the main loop plenty of time for serial parsing.
 * 16 microsteps at 10 rev/s would need 32 k steps/s per motor: not possible on an Uno.
 *
 * Serial protocol (115200 baud, one ASCII line per command, optional "*HH" XOR checksum):
 *   HOME | MOVE q0 q1 q2 q3 t | STOP | STATUS | SETPOS q0 q1 q2 q3 | ENABLE 0|1 | PING
 * Replies: OK <cmd> ..., DONE MOVE, DONE HOME, ERR <code> ..., STATUS key=value ...
 * Joint angles are radians in the mechy_core convention (q1 = shoulder elevation above
 * horizontal; q2, q3 relative to the previous link; positive = up).
 */

#include <Arduino.h>
#include <util/delay.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "config.h"

#define Q24 16777216UL
#define UPDATE_HZ ((float)TICK_HZ / (float)TICKS_PER_UPDATE)
#define MIN_RATE_Q24 ((uint32_t)(2.0f * (float)Q24 / (float)TICK_HZ))    /* 2 steps/s floor: never stall */
#define MECHY_LINE_MAX 96
#define DEBOUNCE_READS 3
#define READY_MOVE_S 2.0f

static const uint8_t DIR_PINS[N_MOTORS] = {DIR0_PIN, DIR1_PIN, DIR2_PIN, DIR3_PIN};
static const uint8_t SWITCH_PINS[N_MOTORS] = {SWITCH0_PIN, SWITCH1_PIN, SWITCH2_PIN, SWITCH3_PIN};

/* ------------------------------------------------------------------ segment (ISR state) */
volatile uint8_t seg_active = 0;
volatile int32_t motor_pos[N_MOTORS];          /* motor steps, logical direction */
volatile int32_t seg_d[N_MOTORS];              /* |steps| of each motor this segment */
volatile int8_t seg_sign[N_MOTORS];
volatile int32_t seg_err[N_MOTORS];
volatile int32_t seg_dmax = 0;
volatile int32_t seg_done = 0;
volatile uint32_t seg_acc = 0, seg_rate = 0, seg_rate_raw = 0, seg_drate = 0, seg_peak = 0;
volatile uint32_t seg_k = 0, seg_n_acc = 0, seg_n_dec = 0, seg_n_total = 0;
volatile uint8_t seg_tick_left = TICKS_PER_UPDATE;

/* ------------------------------------------------------------------ main-loop state */
enum { ST_IDLE = 0, ST_MOVING, ST_HOMING, ST_ESTOP };
enum { H_SEEK1 = 0, H_SEEK2, H_CLEAR, H_BACKOFF, H_SLOW, H_EXIT, H_READY };
static uint8_t state = ST_IDLE;
static uint8_t homed = 0;
static uint8_t enabled = 0;
static float q_offset[N_MOTORS];               /* joint offsets set by homing / SETPOS */
static uint8_t h_idx = 0, h_phase = H_SEEK1;
static uint8_t est_valid = 0;                  /* bit j: q_offset[j] is a usable position estimate */
static int8_t h_sdir = 1;                      /* direction of the first sweep */
static float h_s = 0, h_L2 = 0, h_e1 = 0;      /* sensor (joint rad), second sweep, first edge (raw) */
static uint8_t sw_count[N_MOTORS];
static uint8_t rel_count = 0;
static char line_buf[MECHY_LINE_MAX];
static uint8_t line_len = 0;
static uint8_t line_overflow = 0;

static const char *const STATE_NAMES[] = {"IDLE", "MOVING", "HOMING", "ESTOP"};

/* ------------------------------------------------------------------ step interrupt */
ISR(TIMER1_COMPA_vect) {
  if (!seg_active) { TIMSK1 &= ~_BV(OCIE1A); return; }
  if (--seg_tick_left == 0) {
    seg_tick_left = TICKS_PER_UPDATE;
    /* midpoint rates: accel (k + 1/2) * drate, cruise peak, decel (n_total - k - 1/2) * drate,
       kept incremental (no 32-bit multiply, so the ISR saves few registers) */
    uint32_t k = ++seg_k;
    uint32_t r = seg_rate_raw;
    if (k < seg_n_acc) r += seg_drate;
    else if (k < seg_n_dec) r = seg_peak;
    else if (k == seg_n_dec) r = seg_peak - (seg_drate >> 1);
    else r = r > seg_drate ? r - seg_drate : 0;
    seg_rate_raw = r;                          /* the floor below must not accumulate */
    if (r < MIN_RATE_Q24) r = MIN_RATE_Q24;
    if (r > Q24) r = Q24;
    seg_rate = r;
  }
  uint32_t acc = seg_acc + seg_rate;
  if (acc < Q24) { seg_acc = acc; return; }
  seg_acc = acc - Q24;

  const int32_t dm = seg_dmax;
  uint8_t s = 0;
  int32_t e;
  e = seg_err[0] + seg_d[0]; if (e >= dm) { e -= dm; s |= 1; motor_pos[0] += seg_sign[0]; } seg_err[0] = e;
  e = seg_err[1] + seg_d[1]; if (e >= dm) { e -= dm; s |= 2; motor_pos[1] += seg_sign[1]; } seg_err[1] = e;
  e = seg_err[2] + seg_d[2]; if (e >= dm) { e -= dm; s |= 4; motor_pos[2] += seg_sign[2]; } seg_err[2] = e;
  e = seg_err[3] + seg_d[3]; if (e >= dm) { e -= dm; s |= 8; motor_pos[3] += seg_sign[3]; } seg_err[3] = e;
  if (s & 1) STEP0_PORT |= _BV(STEP0_BIT);
  if (s & 2) STEP1_PORT |= _BV(STEP1_BIT);
  if (s & 4) STEP2_PORT |= _BV(STEP2_BIT);
  if (s & 8) STEP3_PORT |= _BV(STEP3_BIT);
  _delay_us(STEP_PULSE_US);                    /* A4988 needs >= 1 us high */
  STEP0_PORT &= ~_BV(STEP0_BIT);
  STEP1_PORT &= ~_BV(STEP1_BIT);
  STEP2_PORT &= ~_BV(STEP2_BIT);
  STEP3_PORT &= ~_BV(STEP3_BIT);
  if (++seg_done >= dm) {
    seg_active = 0;
    TIMSK1 &= ~_BV(OCIE1A);                    /* no interrupt load while idle */
  }
}

/* ------------------------------------------------------------------ helpers */
static void read_pos(int32_t out[N_MOTORS]) {
  uint8_t sreg = SREG;
  cli();
  for (uint8_t i = 0; i < N_MOTORS; i++) out[i] = motor_pos[i];
  SREG = sreg;
}

static void stop_now(void) {
  uint8_t sreg = SREG;
  cli();
  seg_active = 0;
  TIMSK1 &= ~_BV(OCIE1A);
  SREG = sreg;
}

static void set_enable(uint8_t on) {
  for (uint8_t i = 0; i < N_ENABLE_PINS; i++) digitalWrite(ENABLE_PINS[i], on ? LOW : HIGH);  /* EN is active low */
  enabled = on;
}

static uint8_t switch_raw(uint8_t j) {
  uint8_t v = digitalRead(SWITCH_PINS[j]);
#if SWITCH_ACTIVE_LOW
  return v == LOW;
#else
  return v == HIGH;
#endif
}

/* debounced: true after DEBOUNCE_READS consecutive pressed reads */
static uint8_t switch_hit(uint8_t j) {
  if (switch_raw(j)) {
    if (sw_count[j] < 255) sw_count[j]++;
  } else {
    sw_count[j] = 0;
  }
  return sw_count[j] >= DEBOUNCE_READS;
}

static uint8_t estop_active(void) {
#if ESTOP_PIN >= 0
  return digitalRead(ESTOP_PIN) == LOW;
#else
  return 0;
#endif
}

/* joint angles from motor steps: q = Minv * theta - offset */
static void current_q(float q[N_MOTORS]) {
  int32_t p[N_MOTORS];
  float th[N_MOTORS];
  read_pos(p);
  for (uint8_t m = 0; m < N_MOTORS; m++) th[m] = (float)p[m] / STEPS_PER_RAD[m];
  for (uint8_t j = 0; j < N_MOTORS; j++) {
    float s = 0;
    for (uint8_t m = 0; m < N_MOTORS; m++) s += MAP_MINV[j][m] * th[m];
    q[j] = s - q_offset[j];
  }
}

/* motor step targets for joint angles q: steps = round(SPR * M * (q + offset)) */
static void q_to_steps(const float q[N_MOTORS], int32_t out[N_MOTORS]) {
  for (uint8_t m = 0; m < N_MOTORS; m++) {
    float th = 0;
    for (uint8_t j = 0; j < N_MOTORS; j++) th += MAP_M[m][j] * (q[j] + q_offset[j]);
    out[m] = lroundf(th * STEPS_PER_RAD[m]);
  }
}

/*
 * Plan and start one synchronised trapezoid to absolute motor step targets.
 * Mirrors mechy/control/profile.py plan(). Returns 0 when nothing moves.
 */
static uint8_t start_segment(const int32_t target[N_MOTORS], float T_req, float *T_out, uint8_t *stretched) {
  int32_t cur[N_MOTORS], D[N_MOTORS];
  uint32_t A[N_MOTORS];
  uint32_t dmax = 0;
  read_pos(cur);
  for (uint8_t i = 0; i < N_MOTORS; i++) {
    D[i] = target[i] - cur[i];
    A[i] = (uint32_t)labs(D[i]);
    if (A[i] > dmax) dmax = A[i];
  }
  *T_out = 0;
  *stretched = 0;
  if (dmax == 0) return 0;

  float Vs = 1e30f, As = 1e30f;
  for (uint8_t i = 0; i < N_MOTORS; i++) {
    if (!A[i]) continue;
    float v = V_MAX_STEPS[i] / (float)A[i], a = A_MAX_STEPS[i] / (float)A[i];
    if (v < Vs) Vs = v;
    if (a < As) As = a;
  }
  float Tmin = (sqrtf(As) <= Vs) ? 2.0f / sqrtf(As) : 1.0f / Vs + Vs / As;
  if (Tmin < 2.0f / UPDATE_HZ) Tmin = 2.0f / UPDATE_HZ;
  float T = T_req > Tmin ? T_req : Tmin;

  uint32_t n_total = (uint32_t)ceilf(T * UPDATE_HZ - 1e-6f);
  if (n_total < 2) n_total = 2;
  uint32_t n_acc = 1;
  float peak_tick = 0, drate_tick = 0;
  for (uint16_t iter = 0; iter < 2000; iter++, n_total++) {
    /* accel updates n_acc: n_total - n_acc >= U / Vs (speed), n_acc (n_total - n_acc) >= U^2 / As */
    float nt = (float)n_total;
    float hif = nt - UPDATE_HZ / Vs;
    if (hif > 0.5f * nt) hif = 0.5f * nt;
    long hi_n = (long)floorf(hif + 1e-4f);
    float disc = nt * nt - 4.0f * UPDATE_HZ * UPDATE_HZ / As;
    if (disc < 0 || hi_n < 1) continue;
    long lo_n = (long)ceilf(0.5f * (nt - sqrtf(disc)) - 1e-4f);
    if (lo_n < 1) lo_n = 1;
    if (lo_n > hi_n) continue;
    long na = lroundf(nt / 3.0f);
    if (na < lo_n) na = lo_n;
    if (na > hi_n) na = hi_n;
    n_acc = (uint32_t)na;
    peak_tick = (float)dmax / ((float)(n_total - n_acc) * (float)TICKS_PER_UPDATE);
    drate_tick = peak_tick / (float)n_acc;
    uint8_t ok = peak_tick <= 1.0f;
    for (uint8_t i = 0; i < N_MOTORS && ok; i++) {
      if (!A[i]) continue;
      float f = (float)A[i] / (float)dmax;
      if (f * peak_tick * TICK_HZ > V_MAX_STEPS[i] * 1.0001f) ok = 0;
      if (f * drate_tick * TICK_HZ * UPDATE_HZ > A_MAX_STEPS[i] * 1.0001f) ok = 0;
    }
    if (ok) break;
  }

  for (uint8_t i = 0; i < N_MOTORS; i++) {
    seg_d[i] = (int32_t)A[i];
    seg_sign[i] = D[i] >= 0 ? 1 : -1;
    seg_err[i] = (int32_t)(dmax / 2);
    uint8_t fwd = D[i] >= 0;
    if (DIR_INVERT[i]) fwd = !fwd;
    digitalWrite(DIR_PINS[i], fwd ? HIGH : LOW);
  }
  seg_dmax = (int32_t)dmax;
  seg_done = 0;
  seg_acc = 0;
  seg_peak = (uint32_t)(peak_tick * (float)Q24) + 1;
  seg_drate = (uint32_t)(drate_tick * (float)Q24) + 1;
  seg_n_total = n_total;
  seg_n_acc = n_acc;
  seg_n_dec = n_total - n_acc;
  seg_k = 0;
  uint32_t r0 = seg_drate >> 1;
  seg_rate_raw = r0;
  seg_rate = r0 < MIN_RATE_Q24 ? MIN_RATE_Q24 : r0;
  seg_tick_left = TICKS_PER_UPDATE;
  delayMicroseconds(2);                        /* DIR setup time before the first STEP */
  uint8_t sreg = SREG;
  cli();
  TCNT1 = 0;
  TIFR1 = _BV(OCF1A);                          /* drop a stale compare match */
  seg_active = 1;
  TIMSK1 |= _BV(OCIE1A);
  SREG = sreg;

  *T_out = (float)n_total / UPDATE_HZ;
  *stretched = *T_out > T_req + 1.0f / UPDATE_HZ + 1e-5f;   /* more than rounding up to a whole update */
  return 1;
}

/* move joint j by dist (rad) in joint space (mapped motors move together) at speed (rad/s) */
static void jog_joint(uint8_t j, float dist, float speed) {
  int32_t cur[N_MOTORS], tgt[N_MOTORS];
  float T;
  uint8_t st;
  read_pos(cur);
  for (uint8_t m = 0; m < N_MOTORS; m++) tgt[m] = cur[m] + lroundf(MAP_M[m][j] * dist * STEPS_PER_RAD[m]);
  start_segment(tgt, fabsf(dist) / speed, &T, &st);
}

/* ------------------------------------------------------------------ replies */
static void reply_err(const char *code, const char *detail) {
  Serial.print(F("ERR "));
  Serial.print(code);
  if (detail && detail[0]) {
    Serial.print(' ');
    Serial.print(detail);
  }
  Serial.print('\n');
}

static void reply_err_joint(const char *code, uint8_t j) {
  Serial.print(F("ERR "));
  Serial.print(code);
  Serial.print(F(" joint="));
  Serial.print((int)j);
  Serial.print('\n');
}

static void print_status(void) {
  float q[N_MOTORS];
  int32_t p[N_MOTORS];
  current_q(q);
  read_pos(p);
  Serial.print(F("STATUS state="));
  Serial.print(STATE_NAMES[state]);
  Serial.print(F(" homed="));
  Serial.print((int)homed);
  Serial.print(F(" q="));
  for (uint8_t j = 0; j < N_MOTORS; j++) {
    if (j) Serial.print(',');
    Serial.print(q[j], 4);
  }
  Serial.print(F(" steps="));
  for (uint8_t m = 0; m < N_MOTORS; m++) {
    if (m) Serial.print(',');
    Serial.print((long)p[m]);
  }
  Serial.print(F(" sw="));
  for (uint8_t j = 0; j < N_MOTORS; j++) Serial.print(switch_raw(j) ? '1' : '0');
  Serial.print('\n');
}

/* ------------------------------------------------------------------ homing */
/*
 * Per joint (HOME_ORDER), with the other joints held:
 *  1. Sweep at HOME_FAST. Limit switch (KIND 0): toward HOME_DIR for HOME_TRAVEL. Index sensor
 *     (KIND 1): the sensor's joint angle s is known (HOME_POS, minus the homed joints' share when it
 *     reads a motor angle). With a position estimate (homed before), sweep toward s for |s - q| +
 *     HOME_MARGIN (then back across the whole range); without one, first toward the side of s with
 *     the smaller range (so the worst overrun past a limit is that side + HOME_MARGIN), then back
 *     for the first sweep + the other side + HOME_MARGIN. Both sweeps are bounded; nothing found ->
 *     ERR HOME_FAIL (a dead sensor can still drive a joint up to the larger side past s).
 *  2. Clear: move against HOME_DIR until the sensor releases (<= HOME_WINDOW + HOME_BACKOFF), then
 *     HOME_BACKOFF further, so the slow pass always crosses the sensor in HOME_DIR.
 *  3. Slow pass in HOME_DIR. Limit switch: the first edge is HOME_POS. Index: keep going to the
 *     far edge; the window centre (mean of both edges) is HOME_POS (symmetric debounce cancels).
 */
static void home_done_joint(uint8_t j, float raw_at_sensor);   /* fwd: used by home_begin_joint */

static void home_fail(uint8_t j) {
  stop_now();
  state = ST_IDLE;
  homed = 0;
  reply_err_joint("HOME_FAIL", j);
}

/* debounced release: true after DEBOUNCE_READS consecutive open reads */
static uint8_t switch_released(uint8_t j) {
  if (!switch_raw(j)) {
    if (rel_count < 255) rel_count++;
  } else {
    rel_count = 0;
  }
  return rel_count >= DEBOUNCE_READS;
}

/* joint angle with joint j's offset removed (offsets of other joints kept) */
static float raw_q(uint8_t j) {
  float q[N_MOTORS];
  current_q(q);
  return q[j] + q_offset[j];
}

/* where joint j's sensor sits, as a joint angle (other joints' current estimates) */
static float home_target(uint8_t j) {
  if (HOME_COORD[j] == 255) return HOME_POS[j];
  uint8_t k = HOME_COORD[j];
  float q[N_MOTORS];
  current_q(q);
  float s = HOME_POS[j];
  for (uint8_t i = 0; i < N_MOTORS; i++)
    if (i != j) s -= MAP_M[k][i] * q[i];
  return s / MAP_M[k][j];
}

static void home_clear(uint8_t j) {
  rel_count = 0;
  jog_joint(j, -HOME_DIR[j] * (HOME_WINDOW + HOME_BACKOFF), HOME_FAST);
  h_phase = H_CLEAR;
}

static void home_begin_joint(void) {
  uint8_t j = HOME_ORDER[h_idx];
  if (HOME_KIND[j] == 2) {            /* no sensor (e.g. ref_arm's passive wrist): just mark */
    home_done_joint(j, raw_q(j));
    return;
  }
  sw_count[j] = 0;
  h_s = home_target(j);
  if (switch_raw(j)) { home_clear(j); return; }
  float L1;
  if (HOME_KIND[j] == 0) {
    h_sdir = HOME_DIR[j];
    L1 = HOME_TRAVEL[j];
    h_L2 = 0;
  } else {
    if (est_valid & (1 << j)) {
      float d = h_s - (raw_q(j) - q_offset[j]);
      h_sdir = d >= 0 ? 1 : -1;
      L1 = fabsf(d) + HOME_MARGIN;
      h_L2 = L1 + (Q_MAX[j] - Q_MIN[j]) + HOME_MARGIN;   /* the estimate may be off: whole range */
    } else {
      float lo = h_s - Q_MIN[j], hi = Q_MAX[j] - h_s;
      if (lo < 0) lo = 0;
      if (hi < 0) hi = 0;
      if (fabsf(lo - hi) < 1e-3f) h_sdir = HOME_DIR[j];
      else h_sdir = lo < hi ? 1 : -1;
      L1 = (h_sdir > 0 ? lo : hi) + HOME_MARGIN;
      /* sweep 1 failing means the joint started on the other side of s: at most the far side away */
      h_L2 = L1 + (h_sdir > 0 ? hi : lo) + HOME_MARGIN;
    }
  }
  jog_joint(j, h_sdir * L1, HOME_FAST);
  h_phase = H_SEEK1;
}

static void home_done_joint(uint8_t j, float raw_at_sensor) {
  q_offset[j] = raw_at_sensor - h_s;
  est_valid |= (uint8_t)(1 << j);
  if (++h_idx < N_MOTORS) {
    home_begin_joint();
  } else {
    int32_t tgt[N_MOTORS];
    float T;
    uint8_t st;
    q_to_steps(READY_POSE, tgt);
    start_segment(tgt, READY_MOVE_S, &T, &st);
    h_phase = H_READY;
  }
}

static void home_step(void) {
  uint8_t j = HOME_ORDER[h_idx];
  switch (h_phase) {
    case H_SEEK1:
    case H_SEEK2:
      if (switch_hit(j)) {
        stop_now();
        home_clear(j);
      } else if (!seg_active) {
        if (h_phase == H_SEEK1 && h_L2 > 0) {
          jog_joint(j, -h_sdir * h_L2, HOME_FAST);
          h_phase = H_SEEK2;
        } else {
          home_fail(j);
        }
      }
      break;
    case H_CLEAR:
      if (switch_released(j)) {
        stop_now();
        jog_joint(j, -HOME_DIR[j] * HOME_BACKOFF, HOME_FAST);
        h_phase = H_BACKOFF;
      } else if (!seg_active) {
        home_fail(j);                          /* never released: stuck sensor */
      }
      break;
    case H_BACKOFF:
      if (!seg_active) {
        if (switch_raw(j)) { home_fail(j); break; }
        sw_count[j] = 0;
        jog_joint(j, HOME_DIR[j] * (2.0f * HOME_BACKOFF + (HOME_KIND[j] ? HOME_WINDOW : 0.0f)), HOME_SLOW);
        h_phase = H_SLOW;
      }
      break;
    case H_SLOW:
      if (switch_hit(j)) {
        if (HOME_KIND[j] == 0) {
          stop_now();
          home_done_joint(j, raw_q(j));
        } else {
          h_e1 = raw_q(j);
          rel_count = 0;
          h_phase = H_EXIT;                    /* keep moving to the far edge */
        }
      } else if (!seg_active) {
        home_fail(j);
      }
      break;
    case H_EXIT:
      if (switch_released(j)) {
        stop_now();
        home_done_joint(j, 0.5f * (h_e1 + raw_q(j)));
      } else if (!seg_active) {
        home_fail(j);
      }
      break;
    case H_READY:
      if (!seg_active) {
        homed = 1;
        state = ST_IDLE;
        Serial.print(F("DONE HOME\n"));
      }
      break;
  }
}

/* ------------------------------------------------------------------ commands */
static uint8_t parse_floats(char *rest, float *out, uint8_t n) {
  for (uint8_t i = 0; i < n; i++) {
    char *tok = strtok(rest, " ");
    rest = NULL;
    if (!tok) return 0;
    char *end;
    out[i] = (float)strtod(tok, &end);
    if (end == tok || *end) return 0;
  }
  return strtok(NULL, " ") == NULL;
}

static uint8_t hexval(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return 255;
}

static void handle_line(char *line) {
  char *star = strchr(line, '*');
  if (star) {
    uint8_t c = 0;
    for (char *p = line; p < star; p++) c ^= (uint8_t)*p;
    uint8_t h = hexval(star[1]), l = hexval(star[2]);
    if (h == 255 || l == 255 || star[3] != 0 || ((h << 4) | l) != c) { reply_err("CHECKSUM", ""); return; }
    *star = 0;
  }
  char *cmd = strtok(line, " ");
  if (!cmd) return;
  float a[5];

  if (!strcmp(cmd, "PING")) {
    Serial.print(F("OK PONG\n"));
  } else if (!strcmp(cmd, "STATUS")) {
    print_status();
  } else if (!strcmp(cmd, "STOP")) {
    stop_now();
    if (state == ST_HOMING) homed = 0;
    if (state != ST_ESTOP) state = ST_IDLE;
    Serial.print(F("OK STOP\n"));
  } else if (!strcmp(cmd, "ENABLE")) {
    if (!parse_floats(NULL, a, 1)) { reply_err("PARSE", "ENABLE 0|1"); return; }
    if (a[0] == 0) { stop_now(); if (state != ST_ESTOP) state = ST_IDLE; homed = 0; }
    set_enable(a[0] != 0);
    Serial.print(F("OK ENABLE\n"));
  } else if (state == ST_ESTOP) {
    reply_err("ESTOP", "release the e-stop and reset the board");
  } else if (!strcmp(cmd, "HOME")) {
    if (state != ST_IDLE) { reply_err("BUSY", ""); return; }
    if (!enabled) set_enable(1);
    homed = 0;                                 /* offsets stay: they are the position estimate */
    h_idx = 0;
    state = ST_HOMING;
    Serial.print(F("OK HOME\n"));
    home_begin_joint();
  } else if (!strcmp(cmd, "MOVE")) {
    if (!parse_floats(NULL, a, 5) || !(a[4] > 0)) { reply_err("PARSE", "MOVE q0 q1 q2 q3 t"); return; }
    if (state != ST_IDLE) { reply_err("BUSY", ""); return; }
    if (!homed) { reply_err("NOT_HOMED", ""); return; }
    for (uint8_t j = 0; j < N_MOTORS; j++) {
      if (!(a[j] >= Q_MIN[j] && a[j] <= Q_MAX[j])) { reply_err_joint("LIMIT", j); return; }
    }
    if (!enabled) set_enable(1);
    int32_t tgt[N_MOTORS];
    float T;
    uint8_t st;
    q_to_steps(a, tgt);
    uint8_t moving = start_segment(tgt, a[4], &T, &st);
    Serial.print(F("OK MOVE T="));
    Serial.print(T, 4);
    Serial.print(F(" stretched="));
    Serial.print((int)st);
    Serial.print('\n');
    if (moving) state = ST_MOVING;
    else Serial.print(F("DONE MOVE\n"));
  } else if (!strcmp(cmd, "SETPOS")) {
    if (!parse_floats(NULL, a, 4)) { reply_err("PARSE", "SETPOS q0 q1 q2 q3"); return; }
    if (state != ST_IDLE) { reply_err("BUSY", ""); return; }
    float q[N_MOTORS];
    for (uint8_t j = 0; j < N_MOTORS; j++) q_offset[j] = 0;
    current_q(q);
    for (uint8_t j = 0; j < N_MOTORS; j++) q_offset[j] = q[j] - a[j];
    homed = 1;
    est_valid = 0x0F;
    Serial.print(F("OK SETPOS\n"));
  } else {
    reply_err("UNKNOWN", cmd);
  }
}

static void poll_serial(void) {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      line_buf[line_len] = 0;
      if (line_overflow) reply_err("PARSE", "line too long");
      else if (line_len) handle_line(line_buf);
      line_len = 0;
      line_overflow = 0;
    } else if (line_len < MECHY_LINE_MAX - 1) {
      line_buf[line_len++] = c;
    } else {
      line_overflow = 1;
    }
  }
}

/* ------------------------------------------------------------------ setup / loop */
void setup() {
  for (uint8_t i = 0; i < N_MOTORS; i++) {
    pinMode(DIR_PINS[i], OUTPUT);
    pinMode(SWITCH_PINS[i], SWITCH_ACTIVE_LOW ? INPUT_PULLUP : INPUT);
    motor_pos[i] = 0;
    q_offset[i] = 0;
    sw_count[i] = 0;
  }
  pinMode(STEP0_PIN, OUTPUT);
  pinMode(STEP1_PIN, OUTPUT);
  pinMode(STEP2_PIN, OUTPUT);
  pinMode(STEP3_PIN, OUTPUT);
  for (uint8_t i = 0; i < N_ENABLE_PINS; i++) pinMode(ENABLE_PINS[i], OUTPUT);
#if ESTOP_PIN >= 0
  pinMode(ESTOP_PIN, INPUT_PULLUP);
#endif
  set_enable(1);
  Serial.begin(SERIAL_BAUD);

  cli();                                       /* Timer1: CTC, no prescaler, TICK_HZ */
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;
  OCR1A = (uint16_t)(F_CPU / TICK_HZ - 1);
  TCCR1B |= (1 << WGM12) | (1 << CS10);       /* compare interrupt is enabled per segment */
  sei();

  Serial.print(F("MECHY READY variant=" MECHY_VARIANT " board=" MECHY_BOARD " proto="));
  Serial.print(PROTOCOL_VERSION);
  Serial.print('\n');
}

void loop() {
  poll_serial();
  if (state != ST_ESTOP && estop_active()) {
    stop_now();
    state = ST_ESTOP;
    homed = 0;
    reply_err("ESTOP", "");
    return;
  }
  if (state == ST_MOVING && !seg_active) {
    state = ST_IDLE;
    Serial.print(F("DONE MOVE\n"));
  } else if (state == ST_HOMING) {
    home_step();
  }
}
