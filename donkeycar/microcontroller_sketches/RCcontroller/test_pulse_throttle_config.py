import serial
from time import sleep
import donkeycar as dk

# This takes input from an Arduino Uno which is converting
# the RC receiver pulses into a INT value
# The Arduino blindly sends them to the buffer, currently
# at twice the hz of this script. (40 hz).

# attach to the Arduino
dev = '/dev/ttyACM0' # Arduino Due, Uno
#dev = '/dev/ttyUSB0' # Arduino Duemilanove


Hz          = 20    # update frequency
num_chan    = 2
# load the config file. Set to RC_CENTER, RC_LOW, and RC_HIGH to apprporiate
# values. Use raw_pulse_feed.py for determining these values.
cfg = dk.load_config()

#             [throttle,steering]
low         = cfg.RC_LOW    # minimum pulse value
high        = cfg.RC_HIGH   # maximum pulse value
center      = cfg.RC_CENTER   # center value (determined manually)
deadband    = cfg.RC_DEAD
tolerance   = cfg.RC_TOLERANCE

ser = serial.Serial(dev,57600)
print("Initialized Serial")

# convert this scripts hz to a decimal sleep value
sleep_time = 1000/float(Hz)/1000.0


def getLatestStatus():
    ''' This clears the buffer and returns only the last value
        This is faster than polling the arduino for the latest value
    '''
    status = b''
    while ser.inWaiting() > 0:
        # read and discard any values except the most recent.
        # when Arduino Hz = 2x python Hz this results in 1 to 2
        # discarded results
        status = ser.readline()

    # return it as an array
    # raw format = b'1234 1234\r\n' from the Arduino
    try:
        vel_angle_raw = status.strip().decode("utf-8").split(" ")
    except Exception:
        # unable to decode the values from the Arduino. Typically happens
        # at startup when the serial connection is being started and lasts
        # a few cycles. Junk in the trunk..
        vel_angle_raw = ['0' for x in range(num_chan)]
    return vel_angle_raw


def mapIn(usValue_ary):
    '''
    Takes a tuple of int values representing usPulses per channel and converts it to a float range between
    -1 and +1 per channel
    
    :param usValue_ary:     an array of INTs [1360,1350] for example representing [steering, throttle]
    :return:                an array of floats like [0.23, -0.75]
    '''
    return_value = [0 for x in usValue_ary]
    for i in range(len(usValue_ary)):
        value = usValue_ary[i]
        if (value < low[i]):
            # the value is less than the low value.
            if (value < (low[i]-tolerance)):
                # the value is below even the tolerance value
                # return 0 as NOP
                return 0
            # else return the thresholded lower value
            value = low[i]

        if (value > high[i]):
            # likewise, if the value is higher than the defined high, check to see
            # if it is within a tolerance
            if (value > (high[i]+tolerance)):
                return 0
            # otherwise return the thresholded high value
            value = high[i]

        # now our pulses are constrained to a range defined by the per channel HIGH and LOW usPulse values
        # Lets convert them to a -1 to + 1 range compatible with DonkeyCar
        lowDeadBand  = center[i] - deadband
        highDeadBand = center[i] + deadband

        if (value < lowDeadBand):
            # convert to a value between -1 and 0
            return_value[i] = (value - lowDeadBand) / float(lowDeadBand - low[i])
        elif (value > highDeadBand):
            # convert to a vlaue between 0 and +1
            return_value[i] = (value -highDeadBand) / float(high[i] - highDeadBand)
        else:
            # else we're in the deadband, just return 0
            return_value[i] = 0
    # return the tuple of converted values.
    return return_value

while True:
    # While forever, get the most recent command the
    # arduino has sent
    vel_angle_raw = getLatestStatus()

    if len(vel_angle_raw)==2:
        # if there are two values, convert to INT
        usPulse_ary = list(map(int,vel_angle_raw))
        print(usPulse_ary,mapIn(usPulse_ary))
    # wait Hz amount of time to recover next command
    sleep(sleep_time)
