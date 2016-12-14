import io
import time
from picamera import PiCamera


def capture_loop():
    while True:
        # Create an in-memory stream
        my_stream = io.BytesIO()
        with PiCamera() as camera:
            camera.start_preview()
            # Camera warm-up time
            time.sleep(2)
            camera.capture(my_stream, 'jpeg')
        print('captured')
        time.sleep(1)







if __name__ == '__main__':

    t = threading.Thread(target=capture_loop)
    t.daemon = True #to close thread on Ctrl-c
    t.start()
