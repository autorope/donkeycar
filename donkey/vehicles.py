import time

class BaseVehicle:
    def __init__(self):

        self.drive_loop_delay = .2 #how long to wait between loops

        #these need tobe updated when vehicle is defined
        self.camera = None
        self.steering_actuator = None
        self.throttle_actuator = None
        self.pilot = None


    def start(self):

        start_time = time.time()
        angle = 0
        throttle = 0

        #basic drive loop
        while True:
            now = time.time()
            milliseconds = int( (now - start_time) * 1000)

            #get PIL image from camera
            img = self.camera.capture_img()

            angle, throttle = self.pilot.decide( img,
                                                 angle, 
                                                 throttle,
                                                 milliseconds)

            self.steering_actuator.update(angle)
            pulse =  self.throttle_actuator.update(throttle)
            print(pulse)


            #print current car state
            print('angle: %s   throttle: %s' %(angle, throttle) )           
            time.sleep(self.drive_loop_delay)
