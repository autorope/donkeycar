/* 
 * quadrature_encoder.ino
 * 
 * This does not use any libraries.
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

#define USE_ENCODER_INTERRUPTS
#define DUAL_ENCODERS

#ifdef DUAL_ENCODERS
    //
    // Note that if this is for a differential drive configuration
    // then the encoders are generally oriented oppositely, so when
    // one is turning clockwise the other is turning counter-clockwise.
    // Therefore we want the data and clock pins to be hooked up oppositely
    // for each encoder.  This can be achieved by reversing the connections
    // on the right encoder, so that the data pin of the encoder is
    // assigned the ENCODER_2_PIN_A and the clock pin of the encoder
    // is assigned to ENCODER_2_PIN_B.
    //
    #define ENCODER_PIN_A   (2)      // clock input pin for first encoder (left wheel)
    #define ENCODER_PIN_B   (4)      // data input pin for first encoder
    #define ENCODER_2_PIN_A (3)      // input pin for second encoder (right wheel, see above)
    #define ENCODER_2_PIN_B (5)      // input pin for second encoder
#else
    #define ENCODER_PIN_A   (2)      // clock input pin for first encoder
    #define ENCODER_PIN_B   (3)      // data input pin for first encoder
#endif

#define POLL_DELAY_MICROS (100UL)  // microseconds between polls

//
// state for an encoder pin
//
struct EncoderState {
  uint8_t pin_clock;     // CLOCK pin
  uint8_t pin_data;      // DATA pin
  uint8_t transition;    // last two (from and to) quadrature cycle steps as nibble bit field
  int8_t transitions;    // count of valid quadrature cycle transitions
  volatile long ticks;   // current tick count (count of full cycles)
};


// list of encoders
static EncoderState encoders[] = {
  {ENCODER_PIN_A, ENCODER_PIN_B, 0x03, 0, 0L},
  #ifdef ENCODER_2_PIN_A
    {ENCODER_2_PIN_A, ENCODER_2_PIN_B, 0x03, 0, 0L},
  #endif
};

#define ENCODER_COUNT (sizeof(encoders) / sizeof(EncoderState))

boolean continuous = false; // true to send continuously, false to only send on demand
unsigned long sendAtMs = 0; // next send time in continuous mode
unsigned long delayMs = 0;  // time between sends in continuous mode


#ifdef USE_ENCODER_INTERRUPTS
  typedef void (*gpio_isr_type)();

  //
  // count the interrupts.
  // When clock is low (we interrupt on high to low transition):
  // - if data pin is high, this is aclockwise turn.
  // - if data pin is low, this is a counter-clockwise turn.
  //
  void encode_0() {
    if (digitalRead(encoders[0].pin_data)) {
      encoders[0].ticks += 1;
    } else {
      encoders[0].ticks -= 1;
    }
  }

  #ifdef ENCODER_2_PIN_A
    void encode_1() {
      if (digitalRead(encoders[1].pin_data)) {
        encoders[1].ticks += 1;
      } else {
        encoders[1].ticks -= 1;
      }
    }
  #endif

  gpio_isr_type _isr_routines[] = {
      encode_0,
      #ifdef ENCODER_2_PIN_A
        encode_1
      #endif
  };
#endif


//
// Poll the encoder and increment ticks
// on stable transitions.
//
// The method debounces noisy inputs,
// looking for valid quadrature transitions 
// on the two encoder pins.  A full quadrature
// clockwise cycle is:
//
// step 0: clk = 1, data = 1
// step 1: clk = 0, data = 1
// step 2: clk = 0, data = 0
// step 3: clk = 1, data = 0
// step 0: clk = 1, data = 1
//
// We can count the transition between steps as +1.
// There are 4 transitions between steps, so a 
// full quadrature cycle has +4 transitions.
// 
// So when we are on step 0 we can check the 
// transition count and if it is 4, then 
// we have gone clockwise one full cycle (one tick),
// so we add one to the total ticks.
// 
// If the transition count is not 4, then there
// has been one or more invalid transitions 
// caused by switch bouncing.  In this case 
// we do not count the tick.
//
// In anycase we clear the transition count
// so we can track the next quadrature cycle.
//
// A counter clockwise cycle would go in reverse,
// and we would count each counter clockwise 
// transition as -1.  If we get to step 0 and
// the transition count is -4, then we have
// gone one full quadrature cycle counter-clockwise,
// so we subtract one tick form the total.
//
void pollEncoder(EncoderState &encoder) {
  #ifdef USE_ENCODER_INTERRUPTS
      if (NOT_AN_INTERRUPT == digitalPinToInterrupt(encoder.pin_clock)) {
        Serial.print("Pin ");
        Serial.print(encoder.pin_clock);
        Serial.println(" must be an interrupt capable pin when compiled with USE_ENCODER_INTERRUPTS");
      }
  #else  
    static int8_t TRANSITION_DIRECTION[] = {0,-1,1,0,1,0,0,-1,-1,0,0,1,0,1,-1,0};

    uint8_t current_state = (digitalRead(encoder.pin_clock) << 1) | digitalRead(encoder.pin_data);

    //
    // encoder from(clk | data) and to(clk | data) as a nibble
    // and use it to look up the direction of that transition
    //
    encoder.transition = ((encoder.transition & 0x03) << 2) | current_state;
    encoder.transitions += TRANSITION_DIRECTION[encoder.transition];

    //
    // When clock and data pins are high,
    // then we are at the end of one quadrature
    // cycle and at the beginning of the next.
    // If we had 4 valid transitions, count the tick,
    // otherwise there was an invalid transition (a bounce), 
    // so we do not count the tick.
    //
    if (0x03 == current_state) {
      if (4 == encoder.transitions) {
        encoder.ticks += 1; // we went 1 cycle clockwise
      } else if (-4 == encoder.transitions) {
        encoder.ticks -= 1;
      }
      encoder.transitions = 0;
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

void readEncoders(long ticks[ENCODER_COUNT]) {
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
    pinMode(encoders[i].pin_clock, INPUT);
    pinMode(encoders[i].pin_data, INPUT);
    #ifdef USE_ENCODER_INTERRUPTS
      //
      // if the pin is interrupt capable, then use interrupts
      //
      if (NOT_AN_INTERRUPT != digitalPinToInterrupt(encoders[i].pin_clock)) {
        attachInterrupt(digitalPinToInterrupt(encoders[i].pin_clock), _isr_routines[i], FALLING);
      }
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
