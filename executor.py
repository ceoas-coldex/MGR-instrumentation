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
# Last updated 9/5/24
# -------------

import time
import concurrent.futures
import keyboard
import os, sys
import csv
import yaml

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

from gui import GUI
from main_pipeline.bus import Bus
from main_pipeline.sensor import Sensor
from main_pipeline.interpreter import Interpretor
from main_pipeline.display import Display

# Set up a logger for this module
logger = logging.getLogger("executor")
# Set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
logger.setLevel(logging.DEBUG)
# Create a handler that saves logs to the log folder named as the current date
fh = logging.FileHandler(f"logs\\{time.strftime('%Y-%m-%d', time.localtime())}.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
# Create a formatter to specify our log format
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
fh.setFormatter(formatter)

class Executor():
    """Class that handles passing the data around on all the busses."""
    @log_on_end(logging.INFO, "Executor class initiated", logger=logger)
    def __init__(self) -> None:
        # Set some intitial flags: don't start data collection or sensors, do start the GUI
        self.data_shutdown = True
        self.sensors_shutdown = True
        self.gui_shutdown = False
        
        # Initialize data management
        self.data_dir = "data" # Data storage directory, should yaml this
        self.load_sensor_names()
        
        # Initialize the sensors
        self.sensor = Sensor()
        self.sensor_status_dict = {}

        # Set up the GUI
        button_callbacks = self._set_gui_buttons()
        self.gui = GUI(sensor_button_callback_dict=button_callbacks)

        # Initialize the rest of the process
        self.interpretor = Interpretor()
        self.display = Display(self.gui)  # Pass the GUI and data saving filepath into the display class

        # Initialize the busses
        self.abakus_bus = Bus()
        self.flowmeter_sli2000_bus = Bus()
        self.flowmeter_sls1500_bus = Bus()
        self.laser_bus = Bus()
        self.picarro_gas_bus = Bus()
        self.main_interp_bus = Bus()

        # Set the delay times (sec)
        self.sensor_delay = 0.3
        self.interp_delay = 0.1
        self.display_delay = 0.3

    def __del__(self) -> None:
        """Destructor, makes sure the sensors shut down cleanly when this object is destroyed"""
        self._exit_all()
    
    def load_sensor_names(self):
        # Read in the sensor config file to grab a list of all the sensors we're working with
        try:
            with open("config/sensor_data.yaml", 'r') as stream:
                big_data_dict = yaml.safe_load(stream)
            self.sensor_names = big_data_dict.keys()
        except FileNotFoundError as e:
            logger.critical(f"Error in reading sensor data configuration file: {e}")
            raise Exception

    def init_sensors(self):
        """Method to take each sensor through its initialization"""
        # Initialize sensors, grab their initialization results...
        self.sensor_status_dict = self.sensor.initialize_sensors()
        # ...and update the shutdown flag
        self.sensors_shutdown = False

        return self.sensor_status_dict
    
    def clean_sensor_shutdown(self):
        """Method to cleanly shut down sensors"""
        # Shut down sensors, grab their shutdown results...
        self.sensor_status_dict = self.sensor.shutdown_sensors()
        # ...and update the shutdown flag
        self.sensors_shutdown = True

        return self.sensor_status_dict
    
    @log_on_start(logging.INFO, "Starting data collection", logger=logger)
    def start_data_collection(self):
        """Method that sets the flag to enter data collection mode"""
        self.data_shutdown = False

    @log_on_start(logging.INFO, "Stopping data collection", logger=logger)
    def stop_data_collection(self):
        """Method that sets the flag to exit data collection mode"""
        # If data collection hasn't already been shut down, shut it down
        if not self.data_shutdown:
            # Set the data_shutdown flag to True
            self.data_shutdown = True
            # probably save the data file here
            
            # Shutdown the threadpool executor
            self.executor.shutdown(wait=False, cancel_futures=True)

    def _exit_all(self):
        """Method to stop break GUI and data collection loops, called by the 'alt+q' hotkey"""
        self.clean_sensor_shutdown()
        self.gui_shutdown = True # Set the GUI shutdown flag to True
        self.stop_data_collection()
    
    def _set_gui_buttons(self):
        """Method that builds up a dictionary to be passed into the GUI. This dictionary holds the methods that start/stop/initialize
        sensor measurements, and will be used for button callbacks in the GUI.
        
        Could shoop some of this into a yaml, but I don't know if that makes things much clearer. Might just be more prone to key errors"""

        # Initialize an empty dictionary to hold the methods we're going to use as button callbacks. Sometimes
        # these don't exist (e.g the Picarro doesn't have start/stop, only query), so initialize them to empty dicts
        button_dict = {}
        for name in self.sensor_names:
            button_dict.update({name:{}})

        # Add the button text and the start/stop measurement methods for instruments that have those features: 
        # The Abakus, Flowmeters, and Laser Distance Sensor
        button_dict["Abakus Particle Counter"] = {"Start Abakus": self.sensor.abakus.initialize_abakus,
                                                "Stop Abakus": self.sensor.abakus.stop_measurement}

        button_dict["Laser Distance Sensor"] = {"Start Laser": self.sensor.laser.initialize_laser,
                                                "Stop Laser": self.sensor.laser.stop_laser}
        
        button_dict["Flowmeter"] = {"Start SLI2000": self.sensor.flowmeter_sli2000.initialize_flowmeter,
                                        "Start SLS1500": self.sensor.flowmeter_sls1500.initialize_flowmeter}
        
        # Finally, add a few general elements to the dictionary - one for initializing all sensors (self._init_sensors), 
        # one for starting (self._start_data_collection) and stopping (self._stop_data_collection) data collection 
        # and one for shutting down all sensors (self._clean_sensor_shutdown)
        button_dict.update({"All Sensors":{"Initialize All Sensors":self.init_sensors, "Shutdown All Sensors":self.clean_sensor_shutdown}})
        button_dict.update({"Data Collection":{"Start Data Collection":self.start_data_collection, "Stop Data Collection":self.stop_data_collection}})
        
        return button_dict
        
    def execute(self):
        """Method to execute the sensor, interpretor, and display classes with threading. Calls the appropriate methods within
        those classes and passes them the correct busses and delay times."""

        # Add a hotkey to break the loop
        keyboard.add_hotkey('alt+q', self._exit_all, suppress=True, trigger_on_release=True)
        
        # Eugh, two nested while loops. The first one boots up the GUI. Then, once data collection has been started, we begin querying
        # the sensors, processing the data, and displaying the final result.
        while not self.gui_shutdown:
            try:
                self.gui.run(0.1)
            except KeyboardInterrupt:
                try:
                    self.clean_sensor_shutdown()
                    sys.exit(130)
                except SystemExit:
                    self.clean_sensor_shutdown()
                    os._exit(130)
            # Note - once we enter ↓this loop, we no longer access ↑that loop. The nested loop doesn't mean we're calling gui.run() twice
            while not self.data_shutdown:
                self.gui.run(0)
                try:
                    with concurrent.futures.ThreadPoolExecutor() as self.executor:
                        eAbakus = self.executor.submit(self.sensor.abakus_producer, self.abakus_bus, self.sensor_delay)

                        eFlowMeterSLI2000 = self.executor.submit(self.sensor.flowmeter_sli2000_producer, self.flowmeter_sli2000_bus, self.sensor_delay)
                        eFlowMeterSLS1500 = self.executor.submit(self.sensor.flowmeter_sls1500_producer, self.flowmeter_sls1500_bus, self.sensor_delay)
                        eLaser = self.executor.submit(self.sensor.laser_producer, self.laser_bus, self.sensor_delay)
                        ePicarroGas = self.executor.submit(self.sensor.picarro_gas_producer, self.picarro_gas_bus, self.sensor_delay)
                        
                        eInterpretor = self.executor.submit(self.interpretor.main_consumer_producer, self.abakus_bus, self.flowmeter_sli2000_bus,
                                                    self.flowmeter_sls1500_bus, self.laser_bus, self.picarro_gas_bus, self.main_interp_bus, self.interp_delay)

                        eDisplay = self.executor.submit(self.display.display_consumer, self.main_interp_bus, self.display_delay)

                    # Block until we get a result - only need to do this with the highest level, I think, but could call 
                    # it for all of them if you want to be sure it's all getting processed
                    eDisplay.result()

                # If we got a keyboard interrupt (something Wrong happened), don't try to shut down the threads cleanly -
                # prioritize shutting down the sensors cleanly and killing the program
                except KeyboardInterrupt:
                    try:
                        self.clean_sensor_shutdown()
                        sys.exit(130)
                    except SystemExit:
                        self.clean_sensor_shutdown()
                        os._exit(130)
            
if __name__ == "__main__":
    my_executor = Executor()
    my_executor.execute()
