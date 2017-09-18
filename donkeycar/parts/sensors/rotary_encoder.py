"""
Rotary Encoder
"""

import time

class RotaryEncoder():
    def __init__(self, mm_per_tick=0.306096, pin=27, poll_delay=0.0166, debug=False):
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN)
        GPIO.add_event_detect(pin, GPIO.RISING, callback=self.isr)

        # initialize the odometer values
        self.m_per_tick = mm_per_tick / 1000.0
        self.poll_delay = poll_delay
        self.meters = 0
        self.last_time = time.time()
        self.meters_per_second = 0
        self.counter = 0
        self.on = True
        self.debug = debug
    
    def isr(self, channel):
        self.counter += 1
        
    def update(self):
        # keep looping infinitely until the thread is stopped
        while(self.on):
                
            #save the ticks and reset the counter
            ticks = self.counter
            self.counter = 0
            
            #save off the last time interval and reset the timer
            start_time = self.last_time
            end_time = time.time()
            self.last_time = end_time
            
            #calculate elapsed time and distance traveled
            seconds = end_time - start_time
            distance = ticks * self.m_per_tick
            velocity = distance / seconds
            
            #update the odometer values
            self.meters += distance
            self.meters_per_second = velocity

            #console output for debugging
            if(self.debug):
                print('seconds:', seconds)
                print('distance:', distance)
                print('velocity:', velocity)

                print('distance (m):', round(self.meters, 4))
                print('velocity (m/s):', self.meters_per_second)

            time.sleep(self.poll_delay)

    def run_threaded(self):
        return self.meters, self.meters_per_second

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('stopping Rotary Encoder')
        print('top speed (m/s):', self.top_speed)
        time.sleep(.5)
        
        import RPi.GPIO as GPIO
        GPIO.cleanup() 