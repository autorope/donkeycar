from donkey import whip
from donkey.predictors import base
from donkey import recorders

p = base.BasePredictor()
r = recorders.BaseRecorder()


w = whip.WhipServer(r, p)
w.start()