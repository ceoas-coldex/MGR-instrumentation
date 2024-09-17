#####################################################################################
#                                                                                   #
#                PLOT A LIVE GRAPH IN A PYQT WINDOW                                 #
#                EXAMPLE 1 (modified for extra speed)                               #
#               --------------------------------------                              #
# This code is inspired on:                                                         #
# https://matplotlib.org/3.1.1/gallery/user_interfaces/embedding_in_qt_sgskip.html  #
# and on:                                                                           #
# https://bastibe.de/2013-05-30-speeding-up-matplotlib.html                         #
#                                                                                   #
#####################################################################################

from __future__ import annotations
# from typing import *
import sys
import os
import traceback
import time
# from matplotlib.backends.qt_compat import QtCore, QtWidgets
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT  as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

from collections import deque

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handle worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        # Retrieve args/kwargs here; and fire processing using them
        self.fn(*self.args, **self.kwargs)

class ApplicationWindow(QtWidgets.QMainWindow):
    '''
    The PyQt5 main window.

    '''
    def __init__(self):
        super().__init__()
        # 1. Window settings
        # self.setGeometry(300, 300, 800, 400)
        self.setWindowTitle("Matplotlib live plot in PyQt")
        self.frm = QFrame(self)
        self.frm.setStyleSheet("QWidget { background-color: #eeeeec; }")
        self.lyt = QVBoxLayout()
        self.frm.setLayout(self.lyt)
        self.setCentralWidget(self.frm)

        self.threadpool = QThreadPool()

        # 2. Place the matplotlib figure
        self.plotting = False
        b = QPushButton("Start plotting")
        b.pressed.connect(self.start_plots)
        self.lyt.addWidget(b)

        self.plots = {"test":[]}
        for i in range(5):
            n = int(np.random.randint(1,3))
            x_init = [[0]]*n
            y_init = [[0]]*n
            print(f"init: {x_init, y_init}")
            fig = MyFigureCanvas(x_init, y_init, num_subplots=n)
            toolbar = NavigationToolbar(fig, self, False)
            self.plots["test"].append(fig)
            self.lyt.addWidget(toolbar, alignment=Qt.AlignHCenter)
            self.lyt.addWidget(fig, alignment=Qt.AlignHCenter)
            
            
        # Initiate the timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)
        
        # 3. Show
        self.show()
    
    def start_plots(self):
        self.plotting = True

    def update_plots(self):
        if self.plotting:
            for i, fig in enumerate(self.plots["test"]):
                fig.update_data()
                fig.update_canvas() # Any other args, kwargs are passed to the run function

                # Execute
                # self.threadpool.start(worker)


class MyFigureCanvas(FigureCanvas):
    """This is the FigureCanvas in which the live plot is drawn."""
    def __init__(self, x_init, y_init, num_subplots=1, x_range=60, buffer_length=5000) -> None:
        """
        :param x_init:          
        :param y_init:          Initial y-data
        :param x_range:         How much data we show on the x-axis, in x-axis units
        :param buffer_length: 

        """
        super().__init__(plt.Figure())
        
        # self.x_data = deque([], maxlen=buffer_length)
        # self.y_data = deque([], maxlen=buffer_length)

        self.x_data = x_init
        self.y_data = y_init
        self.x_range = x_range
        self.num_subplots = num_subplots

        # Store a figure axis for the number of subplots set
        self.axs = []
        for i in range(1, num_subplots+1):
            ax = self.figure.add_subplot(num_subplots, 1, i)
            self.axs.append(ax)
        self.draw()    

    def update_data(self, x_new=None, y_new=None):        
        if x_new is None:
            new_x = self.x_data[0][-1]+1
            for i in range(self.num_subplots):
                self.x_data[i].append(new_x)
        else:
            self.x_data = x_new

        if y_new is None:
            for i in range(self.num_subplots):
                self.y_data[i].append(get_next_datapoint())
        else:
            self.y_data = y_new

    def update_canvas(self) -> None:
        """Method to update the plots based on the buffers stored in self.x_data and self.y_data"""

        for i, ax in enumerate(self.axs):
            for artist in ax.lines:
                artist.remove()
            ax.plot(self.x_data[i], self.y_data[i])
            xlim = ax.get_xlim()
            if (xlim[1] - xlim[0]) >= self.x_range:
                ax.set_xlim([self.x_data[i][-1] - self.x_range, self.x_data[i][-1] + 1])

        self.draw()

        # Faster code but can't get the x-axis updating to work
        # ---------
        # self._line_.set_ydata(self.y_data)
        # self._line_.set_xdata(self.x_data)
        # self.ax.draw_artist(self.ax.patch)
        # self.ax.draw_artist(self._line_)
        # self.ax.set_ylim(ymin=min(self.y_data), ymax=min(self.y_data))
        # self.ax.set_xlim(xmin=self.x_data[0], xmax=self.x_data[-1])
        # self.draw()
        # self.update()
        # self.flush_events()

# Data source
# ------------
n = np.linspace(0, 499, 500)
d = 50 + 25 * (np.sin(n / 8.3)) + 10 * (np.sin(n / 7.5)) - 5 * (np.sin(n / 1.5))
i = 0
def get_next_datapoint():
    global i
    i += 1
    if i > 499:
        i = 0
    return float(d[i])

if __name__ == "__main__":
    qapp = QtWidgets.QApplication(sys.argv)
    app = ApplicationWindow()
    qapp.exec_()