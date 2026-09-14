/*
 * Diagnostic sketch for donkeycar on the Arduino UNO Q.
 *
 * The UNO-shaped header pins belong to the STM32U585, not the Qualcomm SoC,
 * so a PCA9685 wired to the header SDA/SCL is invisible to Linux /dev/i2c-*.
 * This sketch scans the MCU's I2C buses and exposes the result to the Linux
 * side over the router bridge, so we can find which bus the board is on.
 *
 * On this variant the devicetree declares
 *     i2cs = <&i2c2>, <&i2c4>, <&i2c3>
 * which the Wire library maps to Wire, Wire1, Wire2 in that order.  Which of
 * them reaches the header is what we are trying to establish, so scan all.
 *
 * Bridge functions provided:
 *   i2c_scan()      -> "Wire:0x40|Wire1:none|Wire2:none"
 *   ping(int)       -> the same int, for measuring round-trip latency
 */
#include <Arduino_RouterBridge.h>
#include <Wire.h>

static String scan_one(arduino::ZephyrI2C &bus, const char *label) {
  String out = String(label) + ":";
  bool found = false;
  for (uint8_t addr = 0x08; addr < 0x78; addr++) {
    bus.beginTransmission(addr);
    if (bus.endTransmission() == 0) {
      if (found) out += ",";
      out += "0x";
      if (addr < 0x10) out += "0";
      out += String(addr, HEX);
      found = true;
    }
  }
  if (!found) out += "none";
  return out;
}

String i2c_scan() {
  String result = scan_one(Wire, "Wire");
  result += "|" + scan_one(Wire1, "Wire1");
  result += "|" + scan_one(Wire2, "Wire2");
  return result;
}

// Echo, so the Linux side can measure a real MCU round trip.
int ping(int value) {
  return value;
}

void setup() {
  Wire.begin();
  Wire1.begin();
  Wire2.begin();

  Bridge.begin();
  Bridge.provide("i2c_scan", i2c_scan);
  Bridge.provide("ping", ping);
}

void loop() {}
