'''

Methods to create, use, save and load predictors. These
are used to control the vehicle autonomously.

'''

class BasePredictor():
    '''
    Base class to define common functions.
    '''
    def save(self):
        pass

    def load(self):
        pass


    def predict(self):
        angle = 0
        speed = 0

        #Do prediction magic

        return angle, speed
