from datetime import datetime
import donkeycar as dk
import re
import time

class RosBot:
    '''
    RosBot general purpose robot controller
    url: http://kittenbot.cc/

        blocks: [
            [' ', 'Stop', 'stop'],
            [' ', 'Run Motor %d.motorIdx at speed %d.motorPWM','runMotor', "M1", 100],
            [' ','pin Mode %n %d.pinSet','setPinmode',13,"input"],//设置pin状态
            [' ','digital write %n %d.pinMode','digitalwritePin',13,"high"],
            [' ','analog write %d.analogPin %n','analogwritePin',"13",100 ],
            ['r','digital read %n','digitalRead',11],
            ['r','analog read %d.Apin','analogRead',"A0"],
            ],
        menus: {
            onoff: ['ON', 'OFF'],
            led:['ALL','A','B','C','D'],
            motorIdx:["M1","M2","M3","M4","ALL"],
            motorPWM:[-255,-160,-100,0,100,160,255],
            pinSet:["input","output"],
            pinMode:["high","low"],
            analogPin:["13","10","9","5","3"],
            Apin:["A0","A1","A2","A3"],
    '''
    import threading

    rosbot_device = None
    rosbot_lock = threading.Lock()

    def __init__(self, channel, frequency = 60):
        import serial

        if RosBot.rosbot_device == None:
            RosBot.rosbot_device = serial.Serial('/dev/ttyUSB0', 115200, timeout = 0.01)

        self.connected = false
        self.notifyConnection = false
        self.flag = 0
        self.motorMap = {'M1':0, 'M2':1, 'M3':2, 'M4':3}
        self.channel = channel
        self.frequency = frequency


    def get_status(self):
        if connected == False:
            print("M0\n");    # check if host app online
            send_msg("M0\n")
            return status=1, msg="Disconnected"
        else:
            return status=2, msg="Connected"


    def set_moter(self, motor, speed):
        print("run motor "+motor+" "+speed+"\n")
        send_msg("M201 "+motorMap[motor]+' '+speed+"\r\n");


    def set_moter(self):
        print("motor stop\n");
        send_msg("M102"+"\n");


    def set_pin_mode(self, pin, pinSet):
       if pinSet == "input": 
           send_msg("M1 "+pin+' '+'0'+"\n")
       
       if pinSet=="output"
           send_msg("M1 "+pin+' '+'1'+"\n")


    def digital_write_pin(self, pin, pinMode):
       if pinMode == "high":
           send_msg("M2 "+pin+' '+'1'+"\n")

       if pinMode == "low"):
          send_msg("M2 "+pin+' '+'0'+"\n")


    def digital_read(self, pin):
       self.flag = send_msg("M13 "+pin+ " "+'1'+"\n")
       print("flag= "+self.flag+"\n")
       return self.flag 


    def analog_write_pin(self, apin. pin):
        send_msg("M4 "+apin+' '+pin+"\n")


    def analog_read(self, pin):
       self.flag = sendMsg("M13 "+pin+ " "+'2'+"\n")
       print("flag= "+self.flag+"\n")
       return self.flag


    def set_pulse(self, pulse):
        # Recalculate pulse width from the Adafruit values
        w = pulse * (1 / (self.frequency * 4096)) # in seconds
        w *= 1000 * 1000  # in microseconds

        with RosBot.rosbot_lock:
            RosBot.rosbot_device.write(("%c %.1f\n" % (self.channel, w)).encode('ascii'))

    def send_msg(self, msg):
        with RosBot.rosbot_lock:
            RosBot.rosbot_device.write("M102"+"\n")
        out = rosbot_readline()
        print("out="+out+"\n")
        return out

    def rosbot_readline(self):
        ret = None
        with RosBot.rosbot_lock:
            # expecting lines like
            # E n nnn n
            if RosBot.rosbot_device.inWaiting() > 8:
                ret = RosBot.rosbot_device.readline()

        if ret != None:
            ret = ret.rstrip()
	    print("ret= " + ret)

        return ret

class RosBotRCin:
    def __init__(self):
        self.inSteering = 0.0
        self.inThrottle = 0.0

        self.sensor = dk.parts.actuator.RosBot(0)

        RosBotRCin.LEFT_ANGLE = -1.0
        RosBotRCin.RIGHT_ANGLE = 1.0
        RosBotRCin.MIN_THROTTLE = -1.0
        RosBotRCin.MAX_THROTTLE =  1.0

        RosBotRCin.LEFT_PULSE = 496.0
        RosBotRCin.RIGHT_PULSE = 242.0
        RosBotRCin.MAX_PULSE = 496.0
        RosBotRCin.MIN_PULSE = 242.0


        self.on = True

    def map_range(self, x, X_min, X_max, Y_min, Y_max):
        '''
        Linear mapping between two ranges of values
        '''
        X_range = X_max - X_min
        Y_range = Y_max - Y_min
        XY_ratio = X_range/Y_range

        return ((x-X_min) / XY_ratio + Y_min)

    def update(self):
        rcin_pattern = re.compile('^I +([.0-9]+) +([.0-9]+).*$')

        while self.on:
            start = datetime.now()

            l = self.sensor.rosbot_readline()

            while l:
                # print("mw RosBotRCin line= " + l.decode('utf-8'))
                m = rcin_pattern.match(l.decode('utf-8'))

                if m:
                    i = float(m.group(1))
                    if i == 0.0:
                        self.inSteering = 0.0
                    else:
                        i = i / (1000.0 * 1000.0) # in seconds
                        i *= self.sensor.frequency * 4096.0
                        self.inSteering = self.map_range(i,
                                                         RosBotRCin.LEFT_PULSE, RosBotRCin.RIGHT_PULSE,
                                                         RosBotRCin.LEFT_ANGLE, RosBotRCin.RIGHT_ANGLE)

                    k = float(m.group(2))
                    if k == 0.0:
                        self.inThrottle = 0.0
                    else:
                        k = k / (1000.0 * 1000.0) # in seconds
                        k *= self.sensor.frequency * 4096.0
                        self.inThrottle = self.map_range(k,
                                                         RosBotRCin.MIN_PULSE, RosBotRCin.MAX_PULSE,
                                                         RosBotRCin.MIN_THROTTLE, RosBotRCin.MAX_THROTTLE)

                    # print("matched %.1f  %.1f  %.1f  %.1f" % (i, self.inSteering, k, self.inThrottle))
                l = self.sensor.rosbot_readline()

            stop = datetime.now()
            s = 0.01 - (stop - start).total_seconds()
            if s > 0:
                time.sleep(s)

    def run_threaded(self):
        return self.inSteering, self.inThrottle

    def shutdown(self):
        # indicate that the thread should be stopped
        self.on = False
        print('stopping RosBOtRCin')
        time.sleep(.5)

