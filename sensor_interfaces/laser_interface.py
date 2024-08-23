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

logging_format = "%(asctime)s: %(message)s"
logging.basicConfig(format=logging_format, level=logging.INFO, datefmt ="%H:%M:%S")
logging.getLogger().setLevel(logging.DEBUG)

class Dimetix():
    def __init__(self, serial_port="COM8", baud_rate=19200) -> None:
        """Class to communicate with the dimetix laser distance sensor."""
        # Dimetix communication codes
        self.LASER_ON = b's0o\r\n'
        self.LASER_OFF = b's0c\r\n'
        self.ONE_MEAS = b's0g\r\n'
        self.TRACKING_MEAS_ON = b's0h\r\n'
        self.TRACKING_BUFFER_ON = b"s0f+500\r\n"
        self.QUERY = b's0q\r\n' # gets the most recent measuremt, buffering must be on. Not sure how it differs from ONE_MEAS
        self.TEMP = b's0t\r\n'

        self.initialize_pyserial(serial_port, baud_rate)

    def __del__(self) -> None:
        """Deconstructor, turns off the laser and closes the serial port when the object is destroyed"""
        self.stop_laser()
        time.sleep(0.5)
        self.ser.close()

    def initialize_pyserial(self, port, baud):
        """
        Method to open the serial port at the specified baud. These values MUST match the instrument. 
        Typing "mode" in the Windows Command Prompt gives information about serial ports, but sometimes
        the baud is wrong, so beware. Check sensor documentation.
        Inputs - port (str, serial port), baud (int, baud rate)
        """
        try:
            self.ser = serial.Serial(port, baud, timeout=5, 
                                     bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE)
            logging.info(f"Connected to serial port {port} with baud {baud}")
        except SerialException:
            logging.info(f"Could not connect to serial port {port}")
    
    @log_on_end(logging.INFO, "Dimetix laser turned on")
    def start_laser(self):
        self.ser.write(self.LASER_ON)
        time.sleep(1)
        # self.ser.write(self.TRACKING_BUFFER_ON)
        # self.ser.write(self.TRACKING_MEAS_ON)

    @log_on_end(logging.INFO, "Dimetix laser turned off")
    def stop_laser(self):
        self.ser.write(self.LASER_OFF)

    @log_on_end(logging.INFO, "Dimetix laser queried distance")
    def query_distance(self):
        # Get the most recent measurement from the laser sensor
        self.ser.write(self.ONE_MEAS)
        time.sleep(1)
        timestamp = time.time()
        response = self.ser.readline().decode()
        # Decode the response
        output = response[7:].strip()
        return timestamp, output
    
    @log_on_end(logging.INFO, "Dimetix laser queried temperature")
    def query_temperature(self):
        # Get the temperature from the laser sensor
        self.ser.write(self.TEMP)
        time.sleep(1)
        temp_raw = self.ser.readline().decode()
        print(temp_raw)
        # Decode the response
        try:
            temp_raw = temp_raw[3:].strip()
            temp_c = float(temp_raw)/10
        except ValueError as e:
            logging.error(f"Error in converting temp reading to float: {e}")
            temp_c = 9999 # maybe this should be NAN?
        logging.info(f"Laser temperature {temp_c}°C")
            
if __name__ == "__main__":
    ## ------- DATA PROCESSING FUNCTION FOR TESTING  ------- ##
    def process_distance(data_out, timestamp):
        try:
            output_cm = float(data_out) / 100
        except ValueError as e:
            logging.error(f"Error in converting distance reading to float: {e}")
            output_cm = 0
        logging.info(f"Laser distance {output_cm}cm")

    ## ------- UI FOR TESTING  ------- ##
    my_laser = Dimetix()
    print("Testing serial communication\n")
    stop = False
    while not stop:
        command = input("a: Start measurement, b: Stop measurement, c: Query, x: Quit \n")
        if command == "a" or command == "A":
            my_laser.start_laser()
        elif command == "b" or command == "B":
            my_laser.stop_laser()
        elif command == "c" or command == "C":
            # time.sleep(5)
            timestamp, output = my_laser.query_distance()
            process_distance(output, timestamp)
            time.sleep(5)
            my_laser.query_temperature()
        elif command == "x" or command == "X":
            stop = True
        else:
            print("Invalid entry. Try again")