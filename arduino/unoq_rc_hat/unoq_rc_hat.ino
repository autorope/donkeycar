/*
 * unoq_rc_hat - donkeycar drive train on the Arduino UNO Q's MCU.
 *
 * The equivalent of the DIY Robocars RC hat (zlite/donkeyhat), but on the
 * UNO Q's STM32U585 instead of an RP2040, and talking to Linux over the
 * Arduino router bridge instead of a UART.  The MCU owns the real-time work:
 * it reads the RC receiver and emits the servo and ESC pulses.  Linux does
 * vision and inference.
 *
 * Why the bridge and not a serial port: /dev/ttyHS1 is the SoC-to-MCU UART
 * and is already at 115200, but arduino-router holds it exclusively and also
 * drives MCU reset over gpiochip1.  Taking it would mean disabling the router
 * and losing App Lab, so RPC it is.  A round trip measures ~5.8ms, which is
 * why RC input is *pushed* up rather than polled: only the output direction
 * pays for it.
 *
 * Pin choice is not arbitrary.  analogWrite() cannot produce servo pulses at
 * all -- it calls pwm_set_pulse_dt(), and the devicetree fixes every PWM pin
 * at 500Hz -- so this calls Zephyr's pwm_set_dt() directly, which sets period
 * and pulse together.  That works only on timers that can actually reach a
 * 20ms frame.  D2 (TIM2, 32-bit counter, 31ns step) and D5 (TIM1, 2.5MHz,
 * 400ns step) both can, and both were confirmed against a real servo.  D3,
 * D9 and D10 must NOT be used: their 16-bit counters cannot hold a 20ms frame
 * at 32MHz, and the driver does not reject the request -- it returns success
 * and emits the wrong waveform.
 *
 * Bridge interface
 *   provided:  set_pulse(steering_us, throttle_us) -> int   0 on success
 *              get_rc()                            -> "st, th, mode, age_ms"
 *              get_last_pulse()                    -> "st, th, tripped"
 *              set_failsafe(bool)                  -> int   arm/disarm
 *   notified:  rc_input(steering_us, throttle_us, mode_us) at ~40Hz
 */
#include <Arduino_RouterBridge.h>
#include <zephyr/drivers/pwm.h>

/* ---------- output ---------- */

#define SPEC(i) PWM_DT_SPEC_GET_BY_IDX(DT_PATH(zephyr_user), i)

static const struct pwm_dt_spec steering_pwm = SPEC(0);   /* D2 / TIM2_CH2 */
static const struct pwm_dt_spec throttle_pwm = SPEC(2);   /* D5 / TIM1_CH4 */
static const int STEERING_PIN = 2;
static const int THROTTLE_PIN = 5;

static const uint32_t FRAME_US   = 20000;   /* 50Hz servo frame */
static const uint16_t PULSE_MIN  = 500;     /* clamp: never command outside */
static const uint16_t PULSE_MAX  = 2500;    /* a servo's electrical range */
static const uint16_t PULSE_MID  = 1500;

/* ---------- RC input ---------- */

/* Three channels, as the RC hat reads: steering, throttle, mode switch.
 * Any GPIO can take an edge interrupt; these avoid D2/D5 and the I2C pins. */
static const int RC_PINS[3] = {3, 4, 6};

static volatile uint32_t rc_rise[3]   = {0, 0, 0};
static volatile uint16_t rc_width[3]  = {0, 0, 0};
static volatile uint32_t rc_stamp[3]  = {0, 0, 0};

/* A pulse outside this is noise, not an RC frame. */
static const uint16_t RC_MIN = 800;
static const uint16_t RC_MAX = 2200;

static inline void rc_edge(int i) {
  if (digitalRead(RC_PINS[i]) == HIGH) {
    rc_rise[i] = micros();
  } else {
    uint32_t w = micros() - rc_rise[i];
    if (w >= RC_MIN && w <= RC_MAX) {
      rc_width[i] = (uint16_t)w;
      rc_stamp[i] = millis();
    }
  }
}

/* attachInterrupt takes a bare function pointer, hence one thunk per channel */
static void rc_edge_0() { rc_edge(0); }
static void rc_edge_1() { rc_edge(1); }
static void rc_edge_2() { rc_edge(2); }

/* ---------- failsafe ---------- */

/*
 * If the host stops commanding -- crash, hung drive loop, ssh session died --
 * an untethered car should stop rather than hold its last throttle.  Steering
 * is deliberately left alone: centring it mid-corner is not obviously safer,
 * and the throttle is what makes the car dangerous.
 */
static const uint32_t FAILSAFE_MS = 500;
static bool     failsafe_armed    = true;
static uint32_t last_command_ms   = 0;
static bool     failsafe_tripped  = false;

/* Last values actually written to the timers, so the host can verify that
 * clamping and the failsafe did what they claim. */
static uint16_t applied_steering = PULSE_MID;
static uint16_t applied_throttle = PULSE_MID;

static inline uint16_t clamp_pulse(int us) {
  if (us < PULSE_MIN) return PULSE_MIN;
  if (us > PULSE_MAX) return PULSE_MAX;
  return (uint16_t)us;
}

static int write_pulse(const struct pwm_dt_spec *spec, uint16_t us) {
  if (!pwm_is_ready_dt(spec)) return -1000;
  int rc = pwm_set_dt(spec, PWM_USEC(FRAME_US), PWM_USEC(us));
  if (rc == 0) {
    if (spec == &steering_pwm) applied_steering = us;
    else if (spec == &throttle_pwm) applied_throttle = us;
  }
  return rc;
}

/* ---------- bridge surface ---------- */

int set_pulse(int steering_us, int throttle_us) {
  uint16_t st = clamp_pulse(steering_us);
  uint16_t th = clamp_pulse(throttle_us);
  int rc_s = write_pulse(&steering_pwm, st);
  int rc_t = write_pulse(&throttle_pwm, th);
  last_command_ms  = millis();
  failsafe_tripped = false;
  return (rc_s != 0) ? rc_s : rc_t;
}

/* Polling fallback, and useful for debugging without a notify handler.
 * age_ms is how stale the newest RC frame is; large or growing means no
 * receiver is connected or it has lost its transmitter. */
String get_rc() {
  noInterrupts();
  uint16_t a = rc_width[0], b = rc_width[1], c = rc_width[2];
  uint32_t newest = rc_stamp[0];
  if (rc_stamp[1] > newest) newest = rc_stamp[1];
  if (rc_stamp[2] > newest) newest = rc_stamp[2];
  interrupts();
  uint32_t age = (newest == 0) ? 999999 : (millis() - newest);
  return String(a) + ", " + String(b) + ", " + String(c) + ", " + String(age);
}

/* "steering_us, throttle_us, failsafe_tripped" as actually applied. */
String get_last_pulse() {
  return String(applied_steering) + ", " + String(applied_throttle) + ", "
       + String(failsafe_tripped ? 1 : 0);
}

int set_failsafe(bool armed) {
  failsafe_armed = armed;
  return 0;
}

/* ---------- main ---------- */

static const uint32_t PUSH_INTERVAL_MS = 25;   /* 40Hz, as the RC hat used */
static uint32_t last_push_ms = 0;

void setup() {
  /* analogWrite applies the channel pinctrl that routes the pad to its timer.
   * The core keeps that helper private, so prime both pins through it once
   * before driving them with pwm_set_dt. */
  analogWrite(STEERING_PIN, 0);
  analogWrite(THROTTLE_PIN, 0);
  write_pulse(&steering_pwm, PULSE_MID);
  write_pulse(&throttle_pwm, PULSE_MID);

  for (int i = 0; i < 3; i++) pinMode(RC_PINS[i], INPUT);
  attachInterrupt(RC_PINS[0], rc_edge_0, CHANGE);
  attachInterrupt(RC_PINS[1], rc_edge_1, CHANGE);
  attachInterrupt(RC_PINS[2], rc_edge_2, CHANGE);

  Bridge.begin();
  Bridge.provide("set_pulse",    set_pulse);
  Bridge.provide("get_rc",       get_rc);
  Bridge.provide("get_last_pulse", get_last_pulse);
  Bridge.provide("set_failsafe", set_failsafe);

  last_command_ms = millis();
}

void loop() {
  uint32_t now = millis();

  if (now - last_push_ms >= PUSH_INTERVAL_MS) {
    last_push_ms = now;
    noInterrupts();
    uint16_t a = rc_width[0], b = rc_width[1], c = rc_width[2];
    interrupts();
    Bridge.notify("rc_input", (int)a, (int)b, (int)c);
  }

  if (failsafe_armed && !failsafe_tripped &&
      (now - last_command_ms) > FAILSAFE_MS) {
    write_pulse(&throttle_pwm, PULSE_MID);
    failsafe_tripped = true;
  }

  delay(1);
}
