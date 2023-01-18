/* 
 * quadrature_encoder.ino
 * 
 * Based on teensy Encoder Library Basic Example
 * http://www.pjrc.com/teensy/td_libs_Encoder.html,
 * 
 * In Arduino IDE, user the library manager to 
 * choose Encoder by Paul Stoffregan v1.4.2
 * 
 * Note that use of interrupt capable pins will increase
 * performance (see `Hardware Requirements` section in
 * the above link).  The Arduino Uno/Nano and other
 * microcontrollers based on the AtMega 328 chip
 * have only two available pins that are interrupt
 * capable; on the Uno/Nano they are pins D2 and D3.
 * The defaults in the sketch use one of these for each
 * of two encoders if `DUAL_ENCODERS` is defined, otherwise
 * it uses both for a single encoder.
 * If you have a different microcontroller
 * then see your datasheet for which pins are interrupt
 * capable.
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
 * as a comma delimited pair: ticks,timeMs
 * In a dual encoder setup the second encoder values
 * as separated from the first by a semicolon: ticks,timeMs;ticks,timeMs
 *
 */
#include <Arduino.h>

// This optional setting causes Encoder to use more optimized code,
// It must be defined before Encoder.h is included.
#define ENCODER_OPTIMIZE_INTERRUPTSß

// Encoder by Paul Stoffregan v1.4.2
#include <Encoder.h>

#define DUAL_ENCODERS

#ifdef DUAL_ENCODERS
    //
    // Note that if this is for a differential drive configuration
    // then the encoders are generally oriented oppositely, so when
    // one is turning clockwise the other is turning counter-clockwise.
    // Therefore we want the data and clock pins to be hooked up oppositely
    // for each encoder.  This can be achieved by reversing the connections
    // on the right encoder, so that the data pin of the encoder is
    // assigned the ENCODER_2_CLK_PIN and the clock pin of the encoder
    // is assigned to ENCODER_2_DT_PIN.
    //
    #define ENCODER_CLK_PIN   (2)      // clock input pin for first encoder (left wheel)
    #define ENCODER_DT_PIN    (4)      // data input pin for first encoder
    #define ENCODER_2_CLK_PIN (3)      // input pin for second encoder (right wheel, see above)
    #define ENCODER_2_DT_PIN  (5)      // input pin for second encoder
#else
    #define ENCODER_CLK_PIN   (2)      // clock input pin for first encoder
    #define ENCODER_DT_PIN    (3)      // data input pin for first encoder
#endif

#define POLL_DELAY_MICROS (100UL)  // microseconds between polls

//
// state for an encoder pin
//
struct EncoderState {
  Encoder *encoder;            // quadrature encoder instance
  long ticks;                  // current tick count
};

// list of encoders
EncoderState encoders[2] = {
  {new Encoder(ENCODER_DT_PIN, ENCODER_CLK_PIN), 0L},
  #ifdef ENCODER_2_CLK_PIN
    {new Encoder(ENCODER_2_DT_PIN, ENCODER_2_CLK_PIN), 0L},
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
  encoder.ticks = encoder.encoder->read();
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
    encoders[i].encoder->write(0);
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
