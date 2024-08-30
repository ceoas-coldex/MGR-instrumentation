# -------------
# This is the main data processing pipeline. It has multiple classes - Sensor, Interpretor, Display - that handle 
# the sensing, interpreting, and displaying of the intrument data. Data is passed between them with the Bus class, 
# managed asynchronously with threads.
#
# It's set up in a producer/consumer framework, with methods that only output data (like sensors) as "producers"
# and those that only recieve data (like a display) as "consumers". There are also "consumer-producers", which 
# read /and/ write data. These generally take in sensor data, do some processing, and republish the processed data.
# 
# Ali Jones
# Last updated 8/23/24
# -------------

import numpy as np
import time
import concurrent.futures

import pandas as pd
import keyboard
import os, sys

from gui import GUI
from tkinter.font import Font, BOLD

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

logger = logging.getLogger("executor") # set up a logger for this module
logger.setLevel(logging.DEBUG) # set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
ch = logging.StreamHandler() # create a handler
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

from main_pipeline.bus import Bus
from main_pipeline.sensor import Sensor
from main_pipeline.interpretor import Interpretor
from main_pipeline.display import Display

class Executor():
    """Class that handles passing the data around on all the busses."""
    def __init__(self) -> None:
        # Allow us to enter the data collection loop
        self.data_collection = True
        self.sensors_on = True
        
        # Initialize the classes
        self.sensor = Sensor()
        self.interpretor = Interpretor()
        self.gui = GUI()
        self.display = Display(self.gui)  # Pass the GUI into the display class

        # Set what GUI buttons correspond to what functions (stop measurement, query, etc)
        self._set_gui_buttons()

        # Initialize the busses
        self.abakus_bus = Bus()
        self.flowmeter_sli2000_bus = Bus()
        self.flowmeter_sls1500_bus = Bus()
        self.laser_bus = Bus()
        self.picarro_gas_bus = Bus()
        self.main_interp_bus = Bus()

        # Set the delay times (sec)
        self.sensor_delay = 0.1
        self.interp_delay = 0.1
        self.display_delay = 0.1

    def clean_sensor_shutdown(self):
        """Method to cleanly shut down sensors, if they're active"""
        if self.sensors_on:
            del self.sensor
        self.sensors_on = False
    
    @log_on_start(logging.INFO, "Exiting data collection", logger=logger)
    def stop_data_collection(self):
        """Method to stop data collection, called by the 'alt+q' hotkey"""
        self.data_collection = False
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.clean_sensor_shutdown()
    
    def __del__(self) -> None:
        """Destructor, makes sure the sensors shut down cleanly when this object is destroyed"""
        self.clean_sensor_shutdown()
    
    def _set_gui_buttons(self):
        pass    
    
    def execute(self):
        """Method to execute the sensor, interpretor, and display classes with threading. Calls the appropriate methods within
        those classes and passes them the correct busses and delay times."""

        # Add a hotkey to break the loop
        keyboard.add_hotkey('alt+q', self.stop_data_collection, suppress=True, trigger_on_release=True)
        
        while self.data_collection == True:
            try:
                self.gui.run()
                with concurrent.futures.ThreadPoolExecutor() as self.executor:
                    eAbakus = self.executor.submit(self.sensor.abakus_producer, self.abakus_bus, self.sensor_delay)
                    eFlowMeterSLI2000 = self.executor.submit(self.sensor.flowmeter_sli2000_producer, self.flowmeter_sli2000_bus, self.sensor_delay)
                    eFlowMeterSLS1500 = self.executor.submit(self.sensor.flowmeter_sls1500_producer, self.flowmeter_sls1500_bus, self.sensor_delay)
                    eLaser = self.executor.submit(self.sensor.laser_producer, self.laser_bus, self.sensor_delay)
                    ePicarroGas = self.executor.submit(self.sensor.picarro_gas_producer, self.picarro_gas_bus, self.sensor_delay)
                    
                    eInterpretor = self.executor.submit(self.interpretor.main_consumer_producer, self.abakus_bus, self.flowmeter_sli2000_bus,
                                                self.flowmeter_sls1500_bus, self.laser_bus, self.picarro_gas_bus, self.main_interp_bus, self.interp_delay)

                    eDisplay = self.executor.submit(self.display.display_consumer, self.main_interp_bus, self.display_delay)

                eAbakus.result()
                eFlowMeterSLI2000.result()
                eFlowMeterSLS1500.result()
                eLaser.result()
                ePicarroGas.result()
                eInterpretor.result()
                eDisplay.result()

            # If we got a keyboard interrupt (something Wrong happened), don't try to shut down the threads cleanly -
            # prioritize shut down the sensors cleanly and killing the program
            except KeyboardInterrupt:
                try:
                    self.clean_sensor_shutdown()
                    sys.exit(130)
                except SystemExit:
                    self.clean_sensor_shutdown()
                    os._exit(130)
            
if __name__ == "__main__":
    my_executor = Executor()
    data_collection = True
    my_executor.execute()
    del my_executor
