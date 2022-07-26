import time
import serial

class TFMini:
    """
    Class for TFMini and TFMini-Plus distance sensors.
    See wiring and installation instructions at https://github.com/TFmini/TFmini-RaspberryPi

    Returns distance in centimeters. 
    """

    def __init__(self, port="/dev/serial0", baudrate=115200, poll_delay=0.01, init_delay=0.1):
        self.ser = serial.Serial(port, baudrate)
        self.poll_delay = poll_delay

        self.dist = 0
        self.strength = 0

        if self.ser.is_open == False:
            self.ser.close() # in case it is still open, we do not want to open it twice
            self.ser.open()

        print("Init TFMini")
        time.sleep(init_delay)

    def update(self):
        while self.ser.is_open:
            self.poll()
            if self.poll_delay > 0:
                time.sleep(self.poll_delay)

    def poll(self):
        try:
            count = self.ser.in_waiting
            if count > 8:
                recv = self.ser.read(9)   
                self.ser.reset_input_buffer() 

                if recv[0] == 0x59 and recv[1] == 0x59:     
                    dist = recv[2] + recv[3] * 256
                    strength = recv[4] + recv[5] * 256

                    if strength > 0:
                        self.dist = dist
                        self.strength = strength

                    self.ser.reset_input_buffer()

        except Exception as e:
            print(e)


    def run_threaded(self):
        return self.dist

    def run(self):
        self.poll()
        return self.dist

    def shutdown(self):
        self.ser.close()

if __name__ == "__main__":
    lidar = TFMini(poll_delay=0.1)

    for i in range(100):
        data = lidar.run()
        print(i, data)

    lidar.shutdown()