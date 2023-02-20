/* 
 * mono_encoder.ino
 * 
 * Read one or two single-channel encoders,
 * Ticks are counted for each transition
 * from open-to-closed and closed-to-open.
 * 
 * For example, a 20 slot optical rotary encoder
 * will have be 40 ticks per revolution.
 * 
 * The sketch implements the r/p/c command protocol
 * for on-demand sending of encoder value
 * and continuous sending with provided delay.
 * See the comment in the loop below for details.
 * commands are send one per line (ending in '\n')
 * 'r' command resets position to zero
 * 'p' command sends position immediately
 * 'c' command starts/stops continuous mode
 *     - if it is followed by an integer,
 *       then use this as the delay in ms
 *       between readings.
 *     - if it is not followed by an integer
 *       then stop continuous mode
 *
 * Sends the encoder ticks and a timestamp
 * as a comma delimited pair:
 * "{ticks},{ticksMs}"

 * In a dual encoder setup the second encoder values
 * as separated from the first by a semicolon:
 * "{ticks},{ticksMs};{ticks},{ticksMs}"
 * 
 * If USE_ENCODER_INTERRUPTS is defined then ticks
 * will be maintained with interrupt service routines.
 * In this case the pins must be interrupt capable.
 * On the Arduino Uno/Nano pins 2 and 3 are interrupt
 * capable, so the sketch uses those two pins by default.
 * If your board uses different pins then modify the sketch
 * before downloading to your microcontroller board.  
 * The advantage of this mode is that is can a high rate
 * of ticks as one would see with a high resolution encoder.
 * The disadvantage is that is does a poor job of debouncing,
 * so it is not appropriate for mechanical encoders.
 *
 * If USE_ENCODER_INTERRUPTS is NOT defined, then polling
 * will be used to maintain the tick count.  The code 
 * implements a robust debouncing technique.  
 * The advantage of this mode is the debounce logic;
 * it can robustly count ticks even from a noisy
 * mechanical encoder like a KY-040 rotary encoder.
 * The disadvantage is that this cannot handle high rates
 * of ticks as would be delivered by a high resolution optical
 * encoder.
 *
 * The method debounces noisy inputs,
 * looking for stable transitions from
 * open-to-closed and closed-to-open by polling
 * the encoder pin and building a 16 bit value.
 * We start by looking for a stable closed-to-open
 * transition, which will be a 1 followed by 15 zeroes.
 * Then we change to look for the open-to-closed transition,
 * which is a zero reading followed by 15 ones.
 *
 * Given a polling delay of 100 microseconds, the
 * minimum time for a stable reading is
 * 100 microseconds * 16 bits = 1.6 milliseconds.
 * That then would allow for a maximum read rate of
 * 1000 / 1.6 = 625 ticks per second.
 * For high resolution encoders, that may be too slow.
 * In that case, reduce the POLL_DELAY_MICROS to
 * suit your encoder and use case.
 */
#include <Arduino.h>

#define ENCODER_PIN   (2)          // input pin for first encoder
#define ENCODER_2_PIN (3)          // input pin for second encoder
#define POLL_DELAY_MICROS (100UL)  // microseconds between polls
#define USE_ENCODER_INTERRUPTS (1) // if defined then use interrupts to read ticks
                                   // otherwise use polling.

//
// state for an encoder pin
//
struct EncoderState {
  int pin;                     // gpio pin number
  volatile long ticks;         // current tick count; do NOT read this directly, use readEncoders()
  uint16_t readings;           // history of last 16 readings
  uint16_t transition;         // value of last 16 readings for next stable state transition 
  unsigned long pollAtMicros;  // time of next poll
};

// list of encoders
static EncoderState encoders[] = {
  {ENCODER_PIN, 0L, 0, 0x8000, 0UL},
  #ifdef ENCODER_2_PIN
    {ENCODER_2_PIN, 0L, 0, 0x8000, 0UL},
  #endif
};

#define ENCODER_COUNT (sizeof(encoders) / sizeof(EncoderState))

boolean continuous = false; // true to send continuously, false to only send on demand
unsigned long sendAtMs = 0; // next send time in continuous mode
unsigned long delayMs = 0;  // time between sends in continuous mode

#ifdef USE_ENCODER_INTERRUPTS
  typedef void (*gpio_isr_type)();

  //
  // count the interrupts
  //
  void encode_0() {
    ++encoders[0].ticks;
  }

  #ifdef ENCODER_2_PIN
    void encode_1() {
      ++encoders[1].ticks;
    }
  #endif

  gpio_isr_type _isr_routines[ENCODER_COUNT] = {
      encode_0,
      #ifdef ENCODER_2_PIN
        encode_1
      #endif
  };
#endif



//
// Poll the encoder and increment ticks
// on stable transitions.
//
void pollEncoder(EncoderState &encoder) {
  #ifdef USE_ENCODER_INTERRUPTS
      if (NOT_AN_INTERRUPT == digitalPinToInterrupt(encoder.pin)) {
        Serial.print("Pin ");
        Serial.print(encoder.pin);
        Serial.println(" must be an interrupt capable pin when compiled with USE_ENCODER_INTERRUPTS");
      }
  #else  
    unsigned long nowMicros = micros();
    if (nowMicros >= encoder.pollAtMicros) {
      //
      // shift state left and add new reading
      //
      encoder.readings = (encoder.readings << 1) | digitalRead(encoder.pin);

      //
      // if readings match target transition
      // then count the ticks and 
      // start looking for the next target transion
      //
      if (encoder.readings == encoder.transition) {
        encoder.ticks += 1;
        encoder.transition = ~encoder.transition;  // invert transition
      }

      encoder.pollAtMicros = nowMicros + POLL_DELAY_MICROS;
    }
  #endif
}


void pollEncoders() {
  for(uint8_t i = 0; i < ENCODER_COUNT; i += 1) {
    pollEncoder(encoders[i]);
  }
}

//
// reset tick counters to zero
//
void resetEncoders() {
  // turn off interrupts so we can
  // write mutable shared state atomically
  #ifdef USE_ENCODER_INTERRUPTS
     noInterrupts();
  #endif

  for(uint8_t i = 0; i < ENCODER_COUNT; i += 1) {
    encoders[i].ticks = 0;
  }

  // turn back on interrupts
  #ifdef USE_ENCODER_INTERRUPTS
    interrupts();
  #endif
}


void readEncoders(long (&ticks)[ENCODER_COUNT]) {
  // turn off interrupts so we can
  // read mutable shared state atomically
  #ifdef USE_ENCODER_INTERRUPTS
     noInterrupts();
  #endif

  for(uint8_t i = 0; i < ENCODER_COUNT; i += 1) {
    ticks[i] = encoders[i].ticks;
  }

  // turn back on interrupts
  #ifdef USE_ENCODER_INTERRUPTS
    interrupts();
  #endif
}


//
// write ticks to serial port
// as a string tuple with ticks and tickMs separate by a comma
//
//   "{ticks},{ticksMs}"
//
void writeTicks(unsigned long ticksMs) {
  long ticks[ENCODER_COUNT];
  readEncoders(ticks);

  Serial.print(ticks[0]);
  Serial.print(',');
  Serial.print(ticksMs);
  for(uint8_t i = 1; i < ENCODER_COUNT; i += 1) {
    Serial.print(";");
    Serial.print(ticks[i]);
    Serial.print(',');
    Serial.print(ticksMs);
  }
  Serial.println("");
}


void setup() {
  // set all encoder pins to inputs
  for(uint8_t i = 0; i < ENCODER_COUNT; i += 1) {
    pinMode(encoders[i].pin, INPUT);
    #ifdef USE_ENCODER_INTERRUPTS
      attachInterrupt(digitalPinToInterrupt(encoders[i].pin), _isr_routines[i], FALLING);
    #endif
  }
  Serial.begin(115200);
}


void loop() {
  //
  // poll each encoder's ticks
  //
  pollEncoders();
  unsigned long ticksMs = millis();

  //
  // commands are send one per line (ending in '\n')
  // 'r' command resets position to zero
  // 'p' command sends position immediately
  // 'c' command starts/stops continuous mode
  //     - if it is followed by an integer,
  //       then use this as the delay in ms
  //       between readings.
  //     - if it is not followed by an integer
  //       then stop continuous mode
  //
  if (Serial.available() > 0) {
    String newcommand = Serial.readStringUntil('\n');
    newcommand.trim();

    if (newcommand == "r") {
      //
      // reset tick counters to zero
      //
      resetEncoders();
    }
    else if (newcommand == "p") {
      //
      // send current ticks immediately
      //
      writeTicks(ticksMs);
    }
    else if (newcommand.startsWith("c")) {
      //
      // continous mode start or stop
      //
      if (1 == newcommand.length()) {
        //
        // stop continuous mode
        //
        continuous = false;
      } else {
        //
        // convert characters after 'c' to an integer
        // and use this as the delay in milliseconds
        //
        String intString = newcommand.substring(1);
        if (isDigit(intString.charAt(0))) {
          delayMs = (unsigned long)intString.toInt();
          continuous = true;
        }
      }
    } else {
      // unknown command
    }
  }
    
  //
  // we are in continuous mode, 
  // then send the ticks when
  // the delay expires
  //
  if (continuous) {
    if (ticksMs >= sendAtMs) {
      sendAtMs = ticksMs + delayMs;
      writeTicks(ticksMs);
    }
  }
}

