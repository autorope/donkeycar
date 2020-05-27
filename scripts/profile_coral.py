import argparse
from donkeycar.parts.coral import InferenceEngine
from PIL import Image
from donkeycar.utils import FPSTimer
import numpy as np

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--model', help='File path of Tflite model.', required=True)
  parser.add_argument(
      '--image', help='File path of the image to be recognized.', required=True)
  args = parser.parse_args()
  # Initialize engine.
  engine = InferenceEngine(args.model)
  # Run inference.
  img = Image.open(args.image)
  result = engine.Inference(np.array(img))
  print("inference result", result)

  timer = FPSTimer()
  while True:
    engine.Inference(np.array(img))
    timer.on_frame()

if __name__ == '__main__':
  main()