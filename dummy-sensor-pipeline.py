import numpy as np
import time
import concurrent.futures
from readerwriterlock import rwlock
import sys, os

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from gui import GUI

class Bus():
    """Class that sets up a bus to pass information around with read/write locking"""
    def __init__(self):
        self.message = [0,0]
        self.lock = rwlock.RWLockWriteD() # sets up a lock to prevent simultanous reading and writing

    def write(self, message):
        with self.lock.gen_wlock():
            self.message = message

    def read(self):
        with self.lock.gen_rlock():
            message = self.message
        return message
    
class DummySensor():
    """Class that mimics a sensor by generating random integers. This would be the place to read from the different 
    sensors and publish that data over busses"""
    def __init__(self) -> None:
        self.data = 0.0

    def sensor_producer(self, sensor_bus:Bus, delay):
        self.read_sensor()
        sensor_bus.write(self.data)
        time.sleep(delay)

    def read_sensor(self):
        self.data = [np.random.randint(-5, 6), np.random.randint(-5, 6)]

class DummyInterpretor():
    """Class that reads data from the sensor bus, does some processing, and republishes on an interpretor bus.
    Currently just takes in the random integer from DummySensor and doubles it"""
    def __init__(self) -> None:
        self.doubled = 0.0

    def doubler_consumer_producer(self, sensor_bus:Bus, doubler_bus:Bus, delay):
        data = sensor_bus.read()
        self.doubler(data)
        doubler_bus.write(self.doubled)
        time.sleep(delay)

    def doubler(self, data):
        try: 
            self.doubled = data
        except TypeError:
            pass

class DummyDisplay():
    """Class that reads the interpreted data and displays it on a barebones GUI"""
    def __init__(self) -> None:

        sensors = ["Picarro Gas", "Picarro Water", "Laser Distance Sensor", "Abakus Particle Counter",
                        "Flowmeter SLI2000 (Green)", "Flowmeter SLS1500 (Black)", "Bronkhurst Pressure", "Melthead"]
        start_callbacks = [None]*len(sensors)
        stop_callbacks = [None]*len(sensors)

        self.gui = GUI(sensors, start_callbacks, stop_callbacks)
        self.x = 0

        self.ani1 = FuncAnimation(self.gui.f1, self.gui.animate, interval=1000, cache_frame_data=False)
        self.ani2 = FuncAnimation(self.gui.f2, self.gui.animate2, interval=1000, cache_frame_data=False)

    def display_consumer(self, interpretor_bus:Bus, delay):
        interp_data = interpretor_bus.read()
        self.gui.update_data1(self.x, interp_data[0])
        self.gui.update_data2(self.x, interp_data[1])
        self.x += 0.1
        
class DummyExecutor():
    """Class that handles passing the data around on all the busses. Still needs a clean shutdown."""
    def __init__(self) -> None:
        # Initialize the classes
        self.sensor = DummySensor()
        self.interpretor = DummyInterpretor()
        self.display = DummyDisplay()

        # Initialize the busses
        self.sensor_bus = Bus()
        self.interpretor_bus = Bus()

        # Set the delay times (sec)
        self.sensor_delay = 0.1
        self.interp_delay = 0.1
        self.display_delay = 0.1

        
    def execute(self):
        """Method to execute the sensor, interpretor, and display classes with threading. Calls the appropriate methods within
        those classes and passes them the correct busses and delay times."""

        while True:
            try:
                self.display.gui.run()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    eSensor = executor.submit(self.sensor.sensor_producer, self.sensor_bus, self.sensor_delay)
                    eInterpreter = executor.submit(self.interpretor.doubler_consumer_producer, self.sensor_bus, 
                                                    self.interpretor_bus, self.interp_delay)
                    eDisplay = executor.submit(self.display.display_consumer, self.interpretor_bus, self.display_delay)

                eSensor.result()
                eInterpreter.result()
                eDisplay.result()

            except KeyboardInterrupt:
                try:
                    sys.exit(130)
                except SystemExit:
                    os._exit(130)

if __name__ == "__main__":
    my_executor = DummyExecutor()
    my_executor.execute()