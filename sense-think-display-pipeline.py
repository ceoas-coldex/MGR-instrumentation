import numpy as np
import time
import concurrent.futures
from readerwriterlock import rwlock

import serial
from serial import SerialException
import pandas as pd
import keyboard

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

logging_format = "%(asctime)s: %(message)s"
logging.basicConfig(format=logging_format, level=logging.INFO, datefmt ="%H:%M:%S")
logging.getLogger().setLevel(logging.DEBUG)


# Imports sensor classes for either real hardware or shadow hardware, depending on the situation
test_port = "COM3"
test_baud = 15200
try:
    serial.Serial(port=test_port, baudrate=test_baud, timeout=5) # CHECKS IF WE'RE CONNECTED TO HARDWARE, REPLACE W SOMETHING BETTER
    from sensor_interfaces.abakus_interface import Abakus
    from sensor_interfaces.flowmeter_interface import FlowMeter
    from sensor_interfaces.laser_interface import Dimetix
    logging.info(f"Successfully connected to port {test_port}, using real hardware")
except:
    from sim_instruments import Abakus, FlowMeter, Dimetix
    logging.info(f"Couldn't find real hardware at port {test_port}, shadowing sensor calls with substitute functions")

class Bus():
    """Class that sets up a bus to pass information around with read/write locking"""
    def __init__(self):
        self.message = None
        self.lock = rwlock.RWLockWriteD() # sets up a lock to prevent simultanous reading and writing

    def write(self, message):
        with self.lock.gen_wlock():
            self.message = message

    def read(self):
        with self.lock.gen_rlock():
            message = self.message
        return message
    
class Sensor():
    """Class that reads from the different sensors and publishes that data over busses"""
    def __init__(self) -> None:
        self.abakus = Abakus()
        self.flowmeter = FlowMeter()
        self.laser = Dimetix()

    def abakus_producer(self, abakus_bus:Bus, delay):
        """Method that writes Abakus data to its bus"""
        data = self.read_abakus()
        abakus_bus.write(data)
        time.sleep(delay)

    def read_abakus(self):
        """Method that gets data from the Abakus class
            Returns - tuple (timestamp[float, epoch time], data_out[str, bins and counts])"""
        timestamp, data_out = self.abakus.query()
        return timestamp, data_out

class Interpretor():
    """Class that reads data from the sensor bus, does some processing, and republishes on an interpretor bus.
    Currently just takes in the random integer from DummySensor and doubles it"""
    def __init__(self) -> None:
        pass

    def abakus_consumer_producer(self, abakus_bus:Bus, particle_count_bus:Bus, delay):
        timestamp, data_out = abakus_bus.read()
        abakus_df = self.process_abakus_data(timestamp, data_out)
        particle_count_bus.write(abakus_df)
        time.sleep(delay)
        
    def process_abakus_data(self, timestamp, data_out):
        """
        Function to processes the data from querying the Abakus. The first measurements come through with 
        more than the expected 32 channels (since the Abakus holds onto the last measurement from the last batch)
        so you should query the Abakus a couple times before starting data processing. We have a check for that here
        just in case.
            Returns - output (pd.df, processed timestamp, bins, and particle count/bin)"""
        # Data processing - from Abby's stuff originally
        output = pd.Series(data_out).str.split()
        bins = output.str[::2] # grab every other element, staring at 0
        counts = output.str[1::2] # grab every other element, starting at 1
        # Make it a dataframe
        output = {'bins': bins, 'counts': counts}
        output = pd.DataFrame(output)
        output = pd.concat([output[col].explode().reset_index(drop=True) for col in output], axis=1)
        output['time'] = timestamp
        # If we recieved the correct number of channels, print them. Otherwise, let the user know
        if len(output) == 32: 
            logging.info("Abakus data good, recieved 32 channels.")
        else:
            logging.info(f"Recieved {len(output)} channels instead of the expected 32. Returning as NAN")
            output["bins"] = np.nan
            output["counts"] = np.nan

        return output
    
    def doubler_consumer_producer(self, sensor_bus:Bus, doubler_bus:Bus, delay):
        data = sensor_bus.read()
        interp = self.doubler(data)
        doubler_bus.write(interp)
        time.sleep(delay)

    def doubler(self, data):
        doubled = data*2
        return doubled

class Display():
    """Class that reads the interpreted data and displays it. Will eventually be on the GUI, for now it 
    reads the interpretor bus and prints the data"""
    def __init__(self) -> None:
        pass

    def display_consumer(self, interpretor_bus:Bus, delay):
        interp_data = interpretor_bus.read()
        logging.info(f"Abakus data: \n{interp_data}")
        time.sleep(delay)

class Executor():
    """Class that handles passing the data around on all the busses. Still needs a clean shutdown."""
    def __init__(self) -> None:
        # Initialize the classes
        self.sensor = Sensor()
        self.interpretor = Interpretor()
        self.display = Display()

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
        while not keyboard.is_pressed("q"):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                eAbakus = executor.submit(self.sensor.abakus_producer, self.sensor_bus, self.sensor_delay)
                
                eInterpreter = executor.submit(self.interpretor.abakus_consumer_producer, self.sensor_bus, 
                                                self.interpretor_bus, self.interp_delay)
                eDisplay = executor.submit(self.display.display_consumer, self.interpretor_bus, self.display_delay)

            eAbakus.result()
            eInterpreter.result()
            eDisplay.result()

if __name__ == "__main__":
    my_executor = Executor()
    my_executor.execute()