/*
 * Can the Uno Q's MCU emit servo-grade PWM (50Hz frame, 1-2ms pulse) on the
 * header pins, without a PCA9685?
 *
 * analogWrite() cannot: it calls pwm_set_pulse_dt(), which takes the period
 * from the devicetree, and the overlay fixes that at 500Hz.  But Zephyr's
 * pwm_set_dt() sets period AND pulse, so the limit is only what each timer
 * can reach given its devicetree prescaler and counter width.
 *
 * Overlay prescalers: TIM1=63, TIM8=63, TIM2/3/4/5=4.  Counter widths differ
 * (TIM2 and TIM5 are 32-bit on STM32U5, the rest 16-bit), so rather than
 * trust arithmetic on an assumed timer clock, ask the driver.
 *
 * Reports Zephyr's return code per pin: 0 means a real 50Hz servo signal is
 * programmed and present on the pin.
 */
#include <Arduino_RouterBridge.h>
#include <zephyr/drivers/pwm.h>

/* Index into the overlay's zephyr_user 'pwms' array. */
#define SPEC(i) PWM_DT_SPEC_GET_BY_IDX(DT_PATH(zephyr_user), i)

struct Candidate {
  const char *name;   /* Arduino pin label */
  int         pin;    /* Arduino pin number, for analogWrite pinctrl priming */
  struct pwm_dt_spec spec;
};

static Candidate candidates[] = {
  {"D2/TIM2_CH2",   2, SPEC(0)},
  {"D3/TIM3_CH3",   3, SPEC(1)},
  {"D5/TIM1_CH4",   5, SPEC(2)},
  {"D7/TIM8_CH4N",  7, SPEC(4)},
  {"D9/TIM4_CH3",   9, SPEC(6)},
  {"D13/TIM1_CH1N",13, SPEC(10)},
};

/* Try to program `period_us` frame with `pulse_us` pulse. Returns Zephyr rc. */
static int try_servo(Candidate &c, uint32_t period_us, uint32_t pulse_us) {
  /* analogWrite applies the channel pinctrl that routes the pad to the
   * timer; the core keeps that helper private, so prime it this way. */
  analogWrite(c.pin, 0);
  if (!pwm_is_ready_dt(&c.spec)) return -1000;
  return pwm_set_dt(&c.spec, PWM_USEC(period_us), PWM_USEC(pulse_us));
}

String pwm_probe() {
  String out;
  for (auto &c : candidates) {
    int rc50 = try_servo(c, 20000, 1500);   /* 50Hz, 1.5ms - standard servo */
    int rc60 = try_servo(c, 16667, 1500);   /* 60Hz, as the RC hat used */
    out += String(c.name) + " 50Hz=" + String(rc50) + " 60Hz=" + String(rc60) + "\n";
    /* leave the pin idle rather than holding a servo command */
    pwm_set_dt(&c.spec, PWM_USEC(20000), 0);
  }
  return out;
}

/* Timer resolution per pin: how fine a pulse step is achievable, and whether
 * a 20ms frame fits the counter.  Servo control wants <= ~5us steps. */
String pwm_resolution() {
  String out;
  for (auto &c : candidates) {
    uint64_t cps = 0;
    int rc = pwm_get_cycles_per_sec(c.spec.dev, c.spec.channel, &cps);
    out += String(c.name) + " rc=" + String(rc) + " cycles/sec=" + String((uint32_t)cps);
    if (rc == 0 && cps) {
      /* ns per cycle = 1e9/cps ; counts in a 20ms frame */
      uint32_t ns_per_cycle = (uint32_t)(1000000000ULL / cps);
      uint32_t counts_20ms  = (uint32_t)(cps / 50);
      out += " step=" + String(ns_per_cycle) + "ns counts_per_20ms=" + String(counts_20ms);
    }
    out += "\n";
  }
  return out;
}

/* Live control, so a pulse width can be confirmed against a real servo. */
int set_servo_us(int index, int us) {
  if (index < 0 || index >= (int)(sizeof(candidates)/sizeof(candidates[0]))) return -2000;
  return try_servo(candidates[index], 20000, us);
}

/* Does a nonsensical period get rejected?  If not, rc==0 proves nothing
 * about whether the requested waveform is actually on the pin. */
String pwm_validates() {
  String out;
  for (auto &c : candidates) {
    analogWrite(c.pin, 0);
    int rc_1s  = pwm_set_dt(&c.spec, PWM_USEC(1000000), PWM_USEC(1500));
    int rc_10s = pwm_set_dt(&c.spec, PWM_MSEC(10000),   PWM_USEC(1500));
    out += String(c.name) + " period_1s=" + String(rc_1s)
        +  " period_10s=" + String(rc_10s) + "\n";
    pwm_set_dt(&c.spec, PWM_USEC(20000), 0);
  }
  return out;
}

void setup() {
  Bridge.begin();
  Bridge.provide("pwm_probe", pwm_probe);
  Bridge.provide("pwm_resolution", pwm_resolution);
  Bridge.provide("pwm_validates", pwm_validates);
  Bridge.provide("set_servo_us", set_servo_us);
}

void loop() {}
