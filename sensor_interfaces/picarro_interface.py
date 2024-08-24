
# -------------
# Establishes serial communication with the Picarro spectrograph. Currently has only been tested on the G2401 model 
# that measures gas concentrations, but should work with any Picarro that supports a Remote Command Interface. The Picarro 
# must be properly configured (Picarro Utilities > Setup Tool > Port Manager) to enable the interface, see README for full docs
#
# Ali Jones
# 8/23/24
# -------------


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

class Picarro():
    def __init__(self, serial_port="COM3", baud_rate="19200") -> None:
        # Picarro communication codes
        self.QUERY = str("_Meas_GetConcEx\r").encode() # gets latest measurement and timestamp
        self.STATUS = str("_Instr_GetStatus\r").encode() # gets instrument status

        self.initialize_pyserial(serial_port, baud_rate)

    def __del__(self) -> None:
        """Deconstructor, closes the serial port when this object is destroyed"""
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
            logging.info(f"Connected to serial port {port} with baud {baud}")
        except SerialException:
            logging.info(f"Could not connect to serial port {port}")

    def _execute_command(self, command):
        """Method to write the command and read back one byte at a time until an end character is reached.
            There might be an existing method that does this, but nether readline() nor read_until() did the trick.
            
            Inputs - command (byte str with appropriate terminator)\n
            Returns - """
        # Write the command
        self.ser.write(command)
        # Read the command into a buffer until we get the closing character ("\r" in binary) or we timeout (>50 bytes read, check
            # if that's sufficient)
        buf = b''
        char = b''
        timeout = 0
        while char != b'\r' and timeout <= 50:
            char = self.ser.read(1)
            buf = buf + char
            timeout += 1

        # Check if there was an error (stored in the first 4 chars of the buffer)
        if buf[:4] == "ERR:":
            raise Exception(f"Error in Picarro communication: {buf}")
        else:
            return buf

    @log_on_end(logging.INFO, "Picarro queried")
    def query(self):
        """
        Queries the picarro to get the most recent measurement and timestamp. The first element of the query 
        is the time, and the rest are gas concentrations. As the Picarro is set up currently, they're
        in the order ["CO2", "CH4", "CO", "H2O"]

            Returns - timestamp (float, epoch time), output (str)
        """
        output = self._execute_command(self.QUERY).decode()
        timestamp = time.time()
        # Split along the semicolons
        output = output.split(";")
        
        return timestamp, output
    

if __name__ == "__main__":
    my_picarro = Picarro()
    # order of the gas measurements returned by query()
    #   I had to manually watch the picarro and the serial output to determine this order, not sure where it's specified
    gasses = ["CO2", "CH4", "CO", "H2O"]

    ## ------- UNIT TESTING  ------- ##
    stop = False
    while not stop:
        command = input("a: Query, x: Quit \n")
        if command == "a" or command == "A":
            timestamp, output = my_picarro.query()
            sample_time = output[0] # the time at which the measurement was sampled, probably different than timestamp
            print("Measurement time: ", sample_time)
            print("My timestamp: ", timestamp)
            for i, value in enumerate(output[1:]): # the gas concentrations
                print(f"{gasses[i]} Concentration: ", value)
        elif command == "x" or command == "X":
            stop = True
        else:
            print("Invalid entry. Please try again")
