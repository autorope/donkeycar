import numpy as np
import matplotlib.pyplot as plt

# Fixing random state for reproducibility

plt.ion()
plt.show()



x = np.array([1]) 
y = np.array([1]) 
dotcolor = np.array(['black'])
area = np.array([25])

counter = 1
while True:
    for i in range(counter):
        dotcolor[i] = 'black'
        area[i] = 6
    x = np.append(x, counter)
    y = np.append(y, counter)
    dotcolor = np.append(dotcolor,'red')
    area = np.append(area, 25)
    plt.scatter(x, y, s = area, c=dotcolor)
    plt.pause(1)
    counter += 1
