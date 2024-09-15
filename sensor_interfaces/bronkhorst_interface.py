import serial
from serial import SerialException
import time
import yaml

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

# Set up a logger for this module
logger = logging.getLogger(__name__)
# Set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
logger.setLevel(logging.DEBUG)
# Create a handler that saves logs to the log folder named as the current date
# fh = logging.FileHandler(f"logs\\{time.strftime('%Y-%m-%d', time.localtime())}.log")
fh = logging.StreamHandler()
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
# Create a formatter to specify our log format
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
fh.setFormatter(formatter)

class Bronkhorst():
    def __init__(self, serial_port="COM3", baud_rate="38400") -> None:
        # Bronkhorst communication codes
        self.GET_MEAS = b':06030401210120\r\n'
        self.GET_SETPOINT = b':06030401210121\r\n'
        self.GET_MEAS_SETPOINT = b':0A80048121012101210120\r\n'

        self.SEND_SETPOINT = b'06030101213E80\r\n'
        self.GET_TEMP = b':06800421472147\r\n'

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
            self.ser = serial.Serial(port, baud, timeout=0.5)
            logger.info(f"Connected to serial port {port} with baud {baud}")
        except SerialException:
            logger.warning(f"Could not connect to serial port {port}")

    def query(self):
        """
        Method to query the Bronkhorst, need to check in with the folks about what data we want specifically
        because we can chain the queries.
            
            Returns - timestamp (float, epoch time), output (bytestr)
        """

        self.ser.write(self.GET_MEAS)
        output = self.ser.read_until(b'\r\n').decode()
        timestamp = time.time()
        
        return timestamp, output
    
if __name__ == "__main__":
    ## ------- DATA PROCESSING FUNCTION FOR TESTING  ------- ##
    def mantissa_to_int(mantissa_str):
        """Method to convert the mantissa of the IEEE floating point to its decimal representation"""
        # Variable to be our exponent as we loop through the mantissa
        power = -1
        # Variable to store the decimal value of mantissa
        mantissa = 0
        # Iterate through binary number and convert it from binary
        for i in mantissa_str:
            mantissa += (int(i)*pow(2, power))
            power -= 1
            
        return (mantissa + 1)

    def hex_to_ieee754_dec(hex_str:str) -> float:
        """
        Method to convert a hexadecimal string (e.g what is returned from the Bronkhorst) into an IEEE floating point. It's gnarly,
        more details https://www.mimosa.org/ieee-floating-point-format/ and https://www.h-schmidt.net/FloatConverter/IEEE754.html
        
        In short, the IEEE 754 standard formats a floating point as N = 1.F x 2E-127, 
        where N = floating point number, F = fractional part in binary notation, E = exponent in bias 127 representation.

        The hex input corresponds to a 32 bit binary:
                Sign | Exponent  |  Fractional parts of number
                0    | 00000000  |  00000000000000000000000
            Bit: 31   | [30 - 23] |  [22        -         0]

        Args - 
            - hex_str (str, hexadecmial representation of binary string)

        Returns -
            - dec (float, number in decimal notation)
        """

        # Convert to integer, keeping its hex representation
        ieee_32_hex = int(hex_str, 16)
        # Convert to 32 bit binary
        ieee_32 = f'{ieee_32_hex:0>32b}'
        # The first bit is the sign bit
        sign_bit = int(ieee_32[0])
        # The next 8 bits are exponent bias in biased form
        exponent_bias = int(ieee_32[1:9], 2)
        # Subtract 127 to get the unbiased form
        exponent_unbias = exponent_bias - 127
        # Next 23 bits are the mantissa
        mantissa_str = ieee_32[9:]
        mantissa_int = mantissa_to_int(mantissa_str)
        # Finally, convert to decimal
        dec = pow(-1, sign_bit) * mantissa_int * pow(2, exponent_unbias)

        return dec
    
    def process_output(output, timestamp):
        """Method to process Bronkhorst output. Will change this when I chain/modify the query(), 
        I /really/ didn't want to write a general function for any potential bronkhorst return"""

        # For a single (unchained) query, the data is stored in the last 4 (measure or setpoint) or 8 (temp or fmeasure)
        # bytes of the string. Slice that out here:
        data = output[11:]
        print(int(data, 16))
        print(timestamp)

    ## ------- UI FOR TESTING  ------- ##
    with open("config/sensor_comms.yaml", 'r') as stream:
        comms_config = yaml.safe_load(stream)
    port = comms_config["Bronkhorst Pressure"]["serial port"]
    baud = comms_config["Bronkhorst Pressure"]["baud rate"]
    my_bronkhorst = Bronkhorst(serial_port=port, baud_rate=baud)

    print("Testing serial communication\n")
    stop = False
    while not stop:
        command = input("a: Initialize bronkhorst, c: Query, x: Quit \n")
        if command == "a" or command == "A":
            my_bronkhorst.initialize_bronkhorst()
        elif command == "c" or command == "C":
            timestamp, output = my_bronkhorst.query()
            process_output(output, timestamp)
        elif command == "d" or command == "D":
            timestamp, output = my_bronkhorst.query()
        elif command == "x" or command == "X":
            stop = True
        else:
            print("Invalid entry. Try again")




