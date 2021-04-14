# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.animation import FuncAnimation

# fig, ax = plt.subplots()
# xdata, ydata = [], []
# ln, = plt.plot([], [], 'ro')

# def init():
#     ax.set_xlim(0, 128)
#     ax.set_ylim(0, 100)
#     return ln,

# def update():
#     xdata = np.random.random_sample() * 100
#     ydata = np.random.random_sample() * 100
#     ln.set_data(xdata, ydata)
#     return ln,

# ani = FuncAnimation(fig, update,interval=50,init_func=init, blit=True)
# plt.show()

# import matplotlib.pyplot as plt
# import numpy as np
# import time

# x = 2
# y = 2

# # You probably won't need this if you're embedding things in a tkinter plot...
# plt.ion()

# fig = plt.figure()
# ax = fig.add_subplot(1,1,1)
# line1, = ax.plot(x, y) # Returns a tuple of line objects, thus the comma

# while True:
#     for i in range(10):
#         print(i)
#         line1.set_ydata(i)
#         line1.set_xdata(2*i)
#         fig.canvas.draw()
#         fig.canvas.flush_events()
#         time.sleep(0.1)

# import matplotlib.pyplot as plt
# import numpy as np

# plt.ion()
# for i in range(50):
#     print(i)
#     plt.scatter(i,i)
#     plt.draw()
#     plt.pause(0.0001)
#     plt.clf()
import pyformulas as pf
import matplotlib.pyplot as plt
import numpy as np
import time

fig = plt.figure()

canvas = np.zeros((480,640))
screen = pf.screen(canvas, 'Sinusoid')

start = time.time()
while True:
    now = time.time() - start

    x = np.linspace(now-2, now, 100)
    y = np.sin(2*np.pi*x) + np.sin(3*np.pi*x)
    plt.xlim(now-2,now+1)
    plt.ylim(-3,3)
    plt.plot(x, y, c='black')

    # If we haven't already shown or saved the plot, then we need to draw the figure first...
    fig.canvas.draw()

    image = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
    image = image.reshape(fig.canvas.get_width_height()[::-1] + (3,))

    screen.update(image)

#screen.close()