/*

Two Channel RC receiver conversion

Takes input from two RC receiver channels and converts them to INT form
and broadcasts them out the serial port.
*/

// Download and install RXInterrupt library from:
// https://github.com/simondlevy/RXInterrupt
#include <RXInterrupt.h>
// TODO: Try modifying RXlibrary to use more precise micros delay
// Will require importing the follwoing library into RXInterupt and then modifying
// the code appropriately. 
// TODO: Replace /2.0 with *0.50 throughtout eRCaGuy library for better performance
// https://github.com/ElectricRCAircraftGuy/eRCaGuy_TimerCounter

// How fast the Arduino should attempt to transmit the serial data
// Recommend twice as fast as default Donkey Car polling of 20Hz emperically.
// Feel free to play with this number.
int Hz = 40;

int delayMs = 1000/Hz;
short last[2] = {1350,1350}; // assumed 0 position
short startup = 0;

void setup()
{
  // Aurduino based on ATmega328P or ATmega168 have external 
  // interupts only on digital pins 2 & 3  

  // For the donkey car project, I've put Throttle on Pin 2 and Steering on Pin 3
  // Pin 2 and 3 is more backwards compatible with various Arduino Boards and is also
  // compatible with Teensy. (All Digital Pins on Teeensy have interrupts, but only 2 & 3 do
  // on many 16mhz Arduino boards.
  int pins[2] = {2, 3};

  // perform the RXInterupt initialization for the set of pins
  // @param   array   An array of pin numbers
  // @param   int     Number of elements in the array
  initChannels(pins, 2);
  
  Serial.begin(57600);
  Serial.println("Initialized pins 2 & 3");
}
            
void loop()
{
  short values[2];
  short out[2];
  // @param   array   An empty array to place the updated values into
  // @param   int     Number of elements in the array.
  updateChannels(values, 2);

  // do a tiny bit of smoothing
  for (int i=0;i<2;i++) {
    out[i] = last[i] + values[i];
    out[i] *= 0.50;
    last[i] = values[i];
  }

  if (startup > 5) {

   // outputs "[throttle angle]\n" in usPulse lengths. [1350,1350] for example
    Serial.print(out[0]);   // throttle
    Serial.print(" ");      // delimited by a space
    Serial.println(out[1]); // angle
    
    // sleep for some amount of time. This Should be faster than Donkey Car's polling time
    // which as of 2018-01-02 was 20Hz. I used "twice as fast" and is seems to work well
  } else {
    // ignore the first 5 values
    startup ++;
  }
  delay(delayMs);
}
