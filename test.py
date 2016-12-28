import settings

from donkey import whip
from donkey.predictors import base
from donkey import recorders

p = base.BasePredictor()
r = recorders.FileRecorder()


w = whip.WhipServer(r, p)
w.start()