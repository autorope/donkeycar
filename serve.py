#import settings

from donkey import whip
from donkey.predictors import keras
from donkey import recorders

p = keras.ConvolutionPredictor()
p.load('sidewalk')
r = recorders.FileRecorder()


w = whip.WhipServer(r, p)
w.start()