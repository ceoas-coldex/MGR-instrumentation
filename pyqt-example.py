from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import time

from main_pipeline.bus import Bus
from main_pipeline.sensor import Sensor
from main_pipeline.interpreter import Interpretor
from main_pipeline.display import Display

class Worker(QRunnable):
    '''
    Worker thread
    '''

    @pyqtSlot()
    def run(self):
        '''
        Your code goes in this function
        '''
        print("Thread start")
        time.sleep(5)
        print("Thread complete")

class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.counter = 0

        layout = QVBoxLayout()

        self.l = QLabel("Start")
        b = QPushButton("Start Data Collection")
        b.pressed.connect(self.oh_no)

        c = QPushButton("Print Results")
        c.pressed.connect(self.change_message)

        layout.addWidget(self.l)
        layout.addWidget(b)

        self.sensor = Sensor()
        self.abakus_result = "hi"

        layout.addWidget(c)

        w = QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)

        self.show()

    def change_message(self):
        self.message = "OH NO"
        print(self.abakus_result)

    def oh_no(self):
        worker = Worker()
        self.threadpool.start(worker)

        self.message = "Pressed"

        while True:
            time.sleep(0.1)
            self.abakus_result = self.sensor.abakus.query()
            self.l.setText(self.message)
            QApplication.processEvents()


app = QApplication([])
window = MainWindow()
app.exec_()