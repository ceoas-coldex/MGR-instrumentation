import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 6*np.pi, 100)
y = np.sin(x)

fig = plt.figure()
ax1 = fig.add_subplot(211)
ax1.plot(x, y, 'r-') 

ax2 = fig.add_subplot(212)
# ax2.plot([], [], 'b--')

# ax2.set_xlim([0, 6*np.pi])

# You probably won't need this if you're embedding things in a tkinter plot...
plt.ion()
plt.show()

for phase in np.linspace(0, 10*np.pi, 500):
    line1, = ax1.get_lines() # Returns a tuple of line objects, thus the comma
    # line2, = ax2.get_lines()

    line1.set_xdata(x)
    line1.set_ydata(np.sin(x + phase))
    
    ax2.clear()
    ax2.plot(x, np.sin(x + phase))

    # fig.canvas.draw()
    # fig.canvas.flush_events()
    # plt.show()