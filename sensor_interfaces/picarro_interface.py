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

baud = 19200
port = "COM3"

try:
    ser = serial.Serial(port=port, baudrate=baud, timeout=5)
    print(f"Connected to serial port {port} with baud {baud}")
except SerialException:
    print(f"Could not connect to serial port {port}")

get_meas = str("_Meas_GetConcEx\r").encode()

def ExecCmd(Command):
    #send the command with the appropriate <CR> terminator...
    ser.write(Command)
    #and collect the response...
    buf = b''
    # print(buf)
    while True:
        c = ser.read(1) # reading one byte at a time
        if c == b'\r': # until a <CR> is read
            # print("break character read")
            break # and then stop the reading loop
        else:
            # print("building buffer")
            # print(c)
            buf = buf+c
            # buf = buf + c # build the response (w/o <CR>)
    #Check if there is an error (first 4 chars = "ERR")...
    if buf[:4] == "ERR:":
    #There was an error - raise an exception with the message...
        # print("error")
        raise Exception(buf)
    else:
    #No error - return the response string (w/o <CR>)...
        # print("returning buffer")
        return buf

gasses = ["CO2", "CH4", "CO", "H2O"]
while not keyboard.is_pressed("q"):
    try:
        # print("Attempting to query measurement")
        ret = ExecCmd(get_meas).decode()
        print(ret)
        print(type(ret))
        # parse the data string with semicolon
        ret = ret.split(";")
        sampleTime = ret[0] # time is always the first element
        print("Time = ", sampleTime)
        for i, value in enumerate(ret[1:]): # conc always starts from the second element
            print(f"{gasses[i]} Concentration = ", value)
        time.sleep(0.5)
    except Exception as e:
        print(f"exception: {e}")
        time.sleep(1.0)

ser.close()

