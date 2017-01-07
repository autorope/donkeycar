import time

class BaseVehicle:
    def __init__(self,
                 drive_loop_delay = .2,
                 camera=None,
                 steering_actuator=None,
                 throttle_actuator=None,
                 pilot=None):

        self.drive_loop_delay = drive_loop_delay #how long to wait between loops

        #these need tobe updated when vehicle is defined
        self.camera = camera
        self.steering_actuator = steering_actuator
        self.throttle_actuator = throttle_actuator
        self.pilot = pilot


    def start(self):

        start_time = time.time()
        angle = 0
        throttle = 0

        #basic drive loop
        while True:
            now = time.time()
            milliseconds = int( (now - start_time) * 1000)

            #get image array image from camera
            img_arr = self.camera.capture_arr()

            angle, throttle = self.pilot.decide( img_arr,
                                                 angle, 
                                                 throttle,
                                                 milliseconds)

            self.steering_actuator.update(angle)
            pulse =  self.throttle_actuator.update(throttle)
            print(pulse)


            #print current car state
            print('angle: %s   throttle: %s' %(angle, throttle) )           
            time.sleep(self.drive_loop_delay)
