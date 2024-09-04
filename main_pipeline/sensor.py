# -------------
# The sensor class
# 
# Currently can't be run from here, since it's importing things from the sensor_interfaces package. Need to figure that out, run it from executor()
# -------------

# General imports
import serial
from serial import SerialException
import time
import yaml

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

logger = logging.getLogger(__name__) # set up a logger for this module
logger.setLevel(logging.DEBUG) # set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
ch = logging.StreamHandler() # create a handler
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Custom imports
try:
    from main_pipeline.bus import Bus   # If we're running this script from the executor file
except ImportError:
    from bus import Bus # Otherwise

# Load the sensor comms configuration file and grab the Picarro G2041 port and baud rate
with open("config/sensor_comms.yaml", 'r') as stream:
    comms_config = yaml.safe_load(stream)
test_port = comms_config["Picarro Gas"]["serial port"]
test_baud = comms_config["Picarro Gas"]["baud rate"]

# Check if we can connect to the Picarro, and if so import the real sensor classes
try:
    serial.Serial(port=test_port, baudrate=test_baud, timeout=5) 
    from sensor_interfaces.abakus_interface import Abakus
    from sensor_interfaces.flowmeter_interface import FlowMeter
    from sensor_interfaces.laser_interface import Dimetix
    from sensor_interfaces.picarro_interface import Picarro
    logger.info(f"Successfully connected to port {test_port}, using real hardware")
# Otherwise use shadow hardware
except SerialException:
    from sensor_interfaces.sim_instruments import Abakus, FlowMeter, Dimetix, Picarro
    logger.info(f"Couldn't find real hardware at port {test_port}, shadowing sensor calls with substitute functions")

class Sensor():
    """Class that reads from the different sensors and publishes that data over busses"""
    def __init__(self) -> None:
        # Initialize the sensors with the appropriate serial port and baud rate (set in config/sensor_comms.yaml, make sure the dictionary keys here match)
        self.abakus = Abakus(serial_port=comms_config["Abakus Particle Counter"]["serial port"], baud_rate=comms_config["Abakus Particle Counter"]["baud rate"])
        self.flowmeter_sli2000 = FlowMeter(serial_port=comms_config["Flowmeter SLI2000 (Green)"]["serial port"], baud_rate=comms_config["Flowmeter SLI2000 (Green)"]["baud rate"])
        self.flowmeter_sls1500 = FlowMeter(serial_port=comms_config["Flowmeter SLS1500 (Black)"]["serial port"], baud_rate=comms_config["Flowmeter SLS1500 (Black)"]["baud rate"])
        self.laser = Dimetix(serial_port=comms_config["Laser Distance Sensor"]["serial port"], baud_rate=comms_config["Laser Distance Sensor"]["baud rate"])
        self.gas_picarro = Picarro(serial_port=comms_config["Picarro Gas"]["serial port"], baud_rate=comms_config["Picarro Gas"]["baud rate"])
        self.water_picarro = Picarro(serial_port=comms_config["Picarro Water"]["serial port"], baud_rate=comms_config["Picarro Water"]["baud rate"])

        # Read in the sensor config file to grab a list of all the sensors we're working with
        with open("config/sensor_data.yaml", 'r') as stream:
            big_data_dict = yaml.safe_load(stream)
        self.sensor_names = big_data_dict.keys()

    def __del__(self) -> None:
        self.shutdown_sensors()

    @log_on_start(logging.INFO, "Initializing sensors", logger=logger)
    @log_on_end(logging.INFO, "Finished initializing sensors", logger=logger)
    def initialize_sensors(self):
        """
        Method to take each sensor through a sequence to check that it's on and getting valid readings.
        **If you're adding a new sensor, you probably need to modify this method**

        Returns - status of each sensor 
        """
        # Create a dictionary to store the result of initialization for each sensor
        sensor_init_dict = {}
        for name in self.sensor_names:
            sensor_init_dict.update({name:False})

        # Fill in the dictionary with the results of calling the sensor init functions
        sensor_init_dict["Abakus Particle Counter"] = self.abakus.initialize_abakus()

    
    @log_on_start(logging.INFO, "Shutting down sensors", logger=logger)
    @log_on_end(logging.INFO, "Finished shutting down sensors", logger=logger)
    def shutdown_sensors(self):
        """
        Method to stop measurements/exit data collection/turn off the sensors that need it; the rest don't have a shutdown feature.
        **If you're adding a new sensor, check if you need to modify this method**
        
        Shuts down - Abakus particle counter, Laser distance sensor
        """
        self.abakus.stop_measurement()
        self.laser.stop_laser()
    
    ## ------------------- ABAKUS PARTICLE COUNTER ------------------- ##
    def abakus_producer(self, abakus_bus:Bus, delay):
        """Method that writes Abakus data to its bus"""
        data = self.read_abakus()
        abakus_bus.write(data)
        time.sleep(delay)

    def read_abakus(self):
        """Method that gets data from the Abakus \n
            Returns - tuple (timestamp[float, epoch time], data_out[str, bins and counts])"""
        timestamp, data_out = self.abakus.query()
        return timestamp, data_out

    ## ------------------- FLOWMETER ------------------- ##
    def flowmeter_sli2000_producer(self, flowmeter_bus:Bus, delay):
        """Method that writes flowmeter SLI2000 data to its bus"""
        data = self.read_flowmeter(flowmeter_model="SLI2000")
        flowmeter_bus.write(data)
        time.sleep(delay)

    def flowmeter_sls1500_producer(self, flowmeter_bus:Bus, delay):
        """Method that writes flowmeter SLS1500 data to its bus"""
        data = self.read_flowmeter(flowmeter_model="SLS1500")
        flowmeter_bus.write(data)
        time.sleep(delay)

    def read_flowmeter(self, flowmeter_model):
        """
        Method that gets data from a flow meter, specified by the model number. 
        Querying is the same for both models, but processing is different.

            Returns - tuple (timestamp[float, epoch time], data_out([int], bytes)
        """
        if flowmeter_model == "SLI2000":
            timestamp, data_out = self.flowmeter_sli2000.query()
        elif flowmeter_model == "SLS1500":
            timestamp, data_out = self.flowmeter_sls1500.query()
        else:
            timestamp = 0.0
            data_out = [0]
        
        return timestamp, data_out
    
    # ------------------- DIMETIX LASER DISTANCE SENSOR ------------------- ##
    def laser_producer(self, laser_bus:Bus, delay):
        """Method that writes laser data to its bus"""
        data = self.read_laser()
        laser_bus.write(data)
        time.sleep(delay)

    def read_laser(self):
        """Method that gets data from the Dimetix laser \n
            Returns - tuple (timestamp [epoch time], data_out [str])"""
        timestamp, data_out = self.laser.query_distance()
        return timestamp, data_out
    
    ## ------------------- PICARRO ------------------- ##
    def picarro_gas_producer(self, picarro_bus:Bus, delay):
        """Method that writes Picarro gas concentration data to its bus"""
        data = self.read_picarro("GAS")
        picarro_bus.write(data)
        time.sleep(delay)

    def picarro_water_producer(self, picarro_bus:Bus, delay):
        """Method that writes Picarro water isotope data to its bus"""
        data = self.read_picarro("WATER")
        picarro_bus.write(data)
        time.sleep(delay)

    def read_picarro(self, picarro_model):
        """Method that gets data from a Picarro, specified by the model \n
            Returns - tuple (timestamp[float, epoch time], data_out[str])"""
        if picarro_model == "GAS":
            timestamp, data_out = self.gas_picarro.query()
        elif picarro_model == "WATER":
            timestamp, data_out = self.water_picarro.query()
        else:
            timestamp = [0.0]
            data_out = ["0"]

        return timestamp, data_out