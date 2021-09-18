/* 
 * mono_encoder.ino
 * 
 * Read a single-channel encoder,
 * debounce the input.  Ticks 
 * are counted for each transition
 * from open-to-closed and closed-to-open.
 * 
 * For example, a 20 slot optical rotary encoder
 * will have be 40 ticks per revolution.
 * 
 * Implements the r/p/c command protocol 
 * for on-demand sending of encoder value
 * and continuous sending with provided delay.
 * See the comment in the loop below for details.
 * 
 * Sends the encoder ticks and a timestamp
 * as a comma delimited pair: ticks,timeMs
 *
 */
#include <arduino.h>
 
#define ENCODER_PIN  2             // input pin for first encoder
#define ENCODER_2_PIN 3            // input pin for second encoder
#define POLL_DELAY_MICROS (100UL)  // microseconds between polls

//
// state for an encoder pin
//
struct EncoderState {
  int pin;                     // gpio pin number
  long ticks;                  // current tick count
  uint16_t readings;           // history of last 16 readings
  uint16_t transition;         // value of last 16 readings for next stable state transition 
  unsigned long pollAtMicros;  // time of next poll
};

// list of encoders
EncoderState encoders[2] = {
  {ENCODER_PIN, 0L, 0, 0x8000, 0UL},
  #ifdef ENCODER_2_PIN
    {ENCODER_2_PIN, 0L, 0, 0x8000, 0UL},
  #endif
};

#define ENCODER_COUNT (sizeof(encoders) / sizeof(EncoderState))

boolean continuous = false; // true to send continuously, false to only send on demand
unsigned long sendAtMs = 0; // next send time in continuous mode
unsigned long delayMs = 0;  // time between sends in continuous mode



//
// Poll the encoder and increment ticks
// on stable transitions.
//
// The method debounces noisy inputs,
// looking for stable transitions from
// open-to-closed and closed-to-open by polling
// the encoder pin and building a 16 bit value.
// We start by looking for a stable closed-to-open 
// transition, which will be a 1 followed by 15 zeroes.
// Then we change to look for the open-to-closed transition,
// which is a zero reading followed by 15 ones.
//
// Given a polling delay of 100 microseconds, the 
// minimum time for a stable reading is 
// 100 microseconds * 16 bits = 1.6 milliseconds.
// That then would allow for a maximum read rate of
// 1000 / 1.6 = 625 ticks per second.
// For high resolution encoders, that may be too slow.
// In that case, reduce the POLL_DELAY_MICROS to 
// suit your encoder and use case.
//
void pollEncoder(EncoderState &encoder) {
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
}
void pollEncoders() {
  for(int i = 0; i < ENCODER_COUNT; i += 1) {
    pollEncoder(encoders[i]);
  }
}

//
// reset tick counters to zero
//
void resetEncoders() {
  for(int i = 0; i < ENCODER_COUNT; i += 1) {
    encoders[i].ticks = 0;
  }
}


//
// write ticks to serial port
// as a string tuple with ticks and tickMs separate by a comma
//
//   "{ticks},{ticksMs}"
//
void writeTicks(unsigned long ticksMs) {
  Serial.print(encoders[0].ticks);
  Serial.print(',');
  Serial.print(ticksMs);
  for(int i = 1; i < ENCODER_COUNT; i += 1) {
    Serial.print(";");
    Serial.print(encoders[i].ticks);
    Serial.print(',');
    Serial.print(ticksMs);
  }
  Serial.println("");
}


void setup() {
  // set all encoder pins to inputs
  for(int i = 0; i < ENCODER_COUNT; i += 1) {
    pinMode(encoders[i].pin, INPUT);
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

