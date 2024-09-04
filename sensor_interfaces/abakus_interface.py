import serial
from serial import SerialException
import csv
import keyboard
import time
import re
import pandas as pd
import numpy as np

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

logger = logging.getLogger(__name__) # set up a logger for this module
logger.setLevel(logging.DEBUG) # set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
ch = logging.StreamHandler() # create a handler
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

class Abakus():
    def __init__(self, serial_port="COM3", baud_rate=38400) -> None:
        """Class to communicate with the Abakus particle counter."""
        # Abakus serial communication codes
        self.LEAVE_RC_MODE = b'C0\r\n'
        self.ENTER_RC_MODE = b'C1\r\n'
        self.INTERRUPT_MEAS = b'C2\r\n'
        self.START_MEAS = b'C5\r\n'
        self.STOP_MEAS = b'C6\r\n'
        self.QUERY = b'C12\r\n'

        self.initialize_pyserial(serial_port, baud_rate)

    def __del__(self) -> None:
        """Deconstructor, closes the serial port when the object is destroyed"""
        self.stop_measurement()
        time.sleep(0.5)
        self.ser.close()

    def initialize_pyserial(self, port, baud):
        """
        Method to open the serial port at the specified baud. Also specifies a timeout to prevent infinite blocking.
        These values (except for timeout) MUST match the instrument. Typing "mode" in the Windows Command Prompt 
        gives information about serial ports, but sometimes the baud is wrong, so beware. Check sensor documentation.
        Inputs - port (str, serial port), baud (int, baud rate)
        """
        try:
            self.ser = serial.Serial(port, baud, timeout=5)
            logger.info(f"Connected to serial port {port} with baud {baud}")
        except SerialException:
            logger.info(f"Could not connect to serial port {port}")

    @log_on_start(logging.INFO, "Initializing Abakus")
    def initialize_abakus(self):
        # Try three times to query and get a valid output. Otherwise report back that initialization failed 
        try:
            self.start_measurement()
            for i in range(3):
                logger.info(f"Initialization attempt {i+1}/3")
                timestamp, data_out = self.query()
                output = data_out.split() # split into a list
                bins = [int(i) for i in output[::2]]
            
                if type(timestamp) == float and len(bins) == 32:
                    logger.info("Abakus initialized")
                    return True

        except Exception as e:
            logger.info(f"Exception in Abakus initialization: {e}")

        logger.info("Abakus initialization failed")
        return False
    
    @log_on_end(logger.INFO, "Abakus measurements started")
    def start_measurement(self):
        """Method to put the Abakus into remote control mode (disables keys on the instrument) and 
        start taking measurements. Does not recieve data"""
        self.ser.write(self.ENTER_RC_MODE)
        self.ser.write(self.START_MEAS)

    @log_on_end(logger.INFO, "Abakus measurements stopped")
    def stop_measurement(self):
        """Method to stop measurement and take the Abakus out of remote control mode"""
        self.ser.write(self.INTERRUPT_MEAS)
        self.ser.write(self.STOP_MEAS)
        self.ser.write(self.LEAVE_RC_MODE)

    @log_on_end(logger.INFO, "Abakus queried")
    def query(self):
        """Queries current values on the running measurement and decodes the serial message. 
            Returns - timestamp (float, epoch time), data_out (str, unprocessed string)"""
        # Send the query and read the returned serial data
        self.ser.write(self.QUERY)
        timestamp = time.time()
        response = self.ser.readline()
        # Decode the serial message
        data_out = response.decode('utf-8').strip()
        # do some regex pattern matching to isolate the data from the serial codes
        regex = r'\b0\d{7}\b'
        matches = re.findall(regex, data_out)
        data_out = ' '.join([match.replace(' ', '')[:8] for match in matches])
        return timestamp, data_out

if __name__ == "__main__":
    ## ------- DATA PROCESSING FUNCTION FOR TESTING  ------- ##
    def process_data_output(data_out, timestamp):
        """Function to processes the data from query(), for unit testing. 
                Sometimes the first couple measurements come through with more than the expected 32 channels, 
                Abby encountered this too by the looks of it. Remember to check for that."""
        # Data processing - from Abby's stuff, need to check in about
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
            print("Recieved 32 channels.")
            print(output)
        else:
            print(f"Recieved {len(output)} channels instead of the expected 32. Disregarding, please query again")
            
    ## ------- UI FOR TESTING  ------- ##
    my_abakus = Abakus()
    print("Testing Abakus serial communication\n")
    stop = False
    while not stop:
        command = input("a: Start measurement, b: Stop measurement, c: Query, x: Quit \n")
        if command == "a" or command == "A":
            my_abakus.start_measurement()
        elif command == "b" or command == "B":
            my_abakus.stop_measurement()
        elif command == "c" or command == "C":
            my_abakus.start_measurement()
            time.sleep(0.5)
            timestamp, output = my_abakus.query()
            process_data_output(output, timestamp)
        elif command == "x" or command == "X":
            stop = True
        else:
            print("Invalid entry. Try again")