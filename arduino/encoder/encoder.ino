/* 
 * Based on teensy Encoder Library Basic Example
 * http://www.pjrc.com/teensy/td_libs_Encoder.html
 * 
 * Adds command for on-demand sending of encoder value
 * and continuous sending with provided delay.
 * Returns timestamp along with encoder ticks.
 *
 * This example code is in the public domain.
 */

#include <Encoder.h>

//
// Change these two numbers to the pins connected to your encoder.
//   Best Performance: both pins have interrupt capability
//   Good Performance: only the first pin has interrupt capability
//   Low Performance:  neither pin has interrupt capability
//
// NOTE: avoid using pins with LEDs attached
//
Encoder myEnc(2, 3);

boolean continuous = false; // true to send continuously, false to only send on demand
unsigned long sendAtMs = 0; // next send time in continuous mode
unsigned long delayMs = 0;  // time between sends in continuous mode

long ticks  = 0;            // current tick cound
unsigned long ticksMs = 0;  // time of current tick count

//
// write ticks to serial port
// as a string tuple with ticks and tickMs separate by a comma
//
//   "{ticks},{ticksMs}"
//
void writeTicks() {
  Serial.print(ticks);
  Serial.print(',');
  Serial.println(ticksMs);
}

void setup() {
  Serial.begin(115200);
}

void loop() {
  //
  // read encoder ticks
  // do this continously (don't delay)
  // in case encoder is in polled mode.
  //
  ticks = myEnc.read();
  ticksMs = millis();

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
      // reset counter to zero
      //
      myEnc.write(0);
      ticks = 0;
    }
    else if (newcommand == "p") {
      //
      // send current ticks immediately
      //
      writeTicks();
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
      writeTicks();
    }
  }

}
