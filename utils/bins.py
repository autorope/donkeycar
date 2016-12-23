import math
def log_bin(a, has_negative=True):
    """ 
    Returns bin number (between 0 and 14) of a number
    num (between -100 and 100).

    If has_negative == True:  bin range = 0-14
    If has_negative == False: bin range = 0-7 
    
    """
    b = int(round(math.copysign(math.log(abs(a) + 1, 2.0), a)))
    if has_negative: 
        b = b + 7
    return b


def log_unbin(b, has_negative=True):
    if has_negative: 
        b = b - 7
        
    a = math.copysign(2 ** abs(b), b) - 1
    return a


def bin_telemetry(angle, throttle):
    #convert angle between -90 (left) and 90 (right) into a 15 bin array.
    a_arr = np.zeros(15, dtype='float')
    a_arr[log_bin(angle)] = 1
    
    #convert throttle between 0 (stopped) and 100 (full throttle) into a 5 bin array.
    t_arr = np.zeros(7, dtype='float')
    t_arr[log_bin(throttle, has_negative=False)] = 1    
     
    y = np.concatenate([a_arr, t_arr])
    
    #return array containing both angle and throttle bins.
    #y.shape = (15+6)
    return y



def unbin_telemetry(y):
    #convert binned telemetry array to angle and throttle
    a_arr = y[:15]
    t_arr = y[15:]
    
    angle = log_unbin(np.argmax(a_arr)) #not 90 so 0 angle is possible
    print(np.argmax(a_arr))
    throttle = log_unbin(np.argmax(t_arr), has_negative=False)
    
    return angle, throttle