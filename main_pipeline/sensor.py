# -------------
# The sensor class
# -------------

import serial
from serial import SerialException
import time

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

logger = logging.getLogger(__name__) # set up a logger for this module
logger.setLevel(logging.DEBUG) # set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
ch = logging.StreamHandler() # create a handler
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

from main_pipeline.bus import Bus

# Imports sensor classes for either real hardware or shadow hardware, depending on the situation
test_port = "COM3" # REPLACE WITH READING A .YAML FILE
test_baud = 15200
try:
    serial.Serial(port=test_port, baudrate=test_baud, timeout=5) 
    from sensor_interfaces.abakus_interface import Abakus
    from sensor_interfaces.flowmeter_interface import FlowMeter
    from sensor_interfaces.laser_interface import Dimetix
    from sensor_interfaces.picarro_interface import Picarro
    logger.info(f"Successfully connected to port {test_port}, using real hardware")
except:
    from sensor_interfaces.sim_instruments import Abakus, FlowMeter, Dimetix, Picarro
    logger.info(f"Couldn't find real hardware at port {test_port}, shadowing sensor calls with substitute functions")

    
class Sensor():
    """Class that reads from the different sensors and publishes that data over busses"""
    def __init__(self) -> None:
        ### SHOULD EITHER READ IN OR BE PASSED IN A .YAML FILE HERE THAT SPECIFIES PORTS AND BAUDS ###
        self.abakus = Abakus()
        self.flowmeter_sli2000 = FlowMeter(serial_port="COM6")
        self.flowmeter_sls1500 = FlowMeter(serial_port="COM7")
        self.laser = Dimetix()
        self.gas_picarro = Picarro(serial_port="COM3")
        self.water_picarro = Picarro(serial_port="COM4")

    def __del__(self) -> None:
        # self.abakus.__del__()
        pass
    
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
