import serial
from serial import SerialException
import csv
import keyboard
import time
import re
import pandas as pd
import numpy as np

# Abakus serial communication codes
LEAVE_RC_MODE = b'C0\r\n'
ENTER_RC_MODE = b'C1\r\n'
INTERRUPT_MEAS = b'C2\r\n'
START_MEAS = b'C5\r\n'
STOP_MEAS = b'C6\r\n'
QUERY = b'C12\r\n'

# set up Pyserial
arduino_port = "COM3"
baud = 38400
try:
    ser = serial.Serial(arduino_port, baud, timeout=5)
    print(f"Connected to serial port {arduino_port} with baud {baud}")
except SerialException:
    print(f"Could not connect to serial port {arduino_port}")

# Initiate and query
ser.write(ENTER_RC_MODE)
ser.write(START_MEAS)
print("Abakus measurement started")
# Query
ser.write(QUERY)
# Decode the serial message
get_data = ser.readline()
current_time = time.time()
data_out = get_data.decode('utf-8').strip()

# Data processing - from Abby's stuff, need to check in about
# do some regex pattern matching to isolate the data from the serial codes
regex = r'\b0\d{7}\b'
matches = re.findall(regex, data_out)
data_out = ' '.join([match.replace(' ', '')[:8] for match in matches])

output = pd.Series(data_out).str.split()
bins = output.str[::2] # grab every other element, staring at 0
counts = output.str[1::2] # grab every other element, starting at 1

# make it a dataframe
output = {'bins': bins, 'counts': counts}
output = pd.DataFrame(output)
output = pd.concat([output[col].explode().reset_index(drop=True) for col in output], axis=1)
output['time'] = current_time

# Stop
ser.write(INTERRUPT_MEAS)
ser.write(STOP_MEAS)
ser.write(LEAVE_RC_MODE)

print("Stopped Abakus measurement")
ser.close()

print(output)