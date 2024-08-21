# imports
import math
import serial
import time
import tkinter as tk
import tkinter.messagebox
import sys
from ast import Load
from ctypes import *
from array import array
import numpy as np
import random
import sqlite3 as sql
import pandas as pd
import time as time_
from datetime import datetime, date, time, timedelta
import os

conn = sql.connect('Dust.db')

cursor_l = conn.cursor()

cursor_l.execute('''
	CREATE TABLE IF NOT EXISTS LaserDistanceData (
  	coretop_cm DECIMAL(6,4),
		date DATE,
		time TIME
	)

''')

# Setup and Global variables
sys.path.append('T:\Disciplines, Programs and Workgroups\Brook Lab\Abakus\Code')

# this dictionary is the lone location to name and insert data into the picarro data stream
#    down lower the values of each sensor are populated but this defines the name that will be in the h5 files

#auxillary_data = {"coretop_cm": 0} 
auxillary_data = pd.DataFrame(columns=['date', 'time', 'coretop_cm'])

dimetix_comm = serial.Serial(port='COM1',
                           baudrate=19200,
                           bytesize=serial.SEVENBITS,
                           parity=serial.PARITY_EVEN,
                           stopbits=serial.STOPBITS_ONE,
                           timeout=0)

dimetix_ON = False
dimetix_make_continuous_measurements = False
laser_temperature = 9999
dimetix_raw = 0
coretop_cm = -1

tk_window_timer = None
tk_dimetix_continuous_timer = 0

# def close_window(event):
#     dimetix_comm.write('s0c' + "\r\n")
#     window.destroy()

"""Dimetix Laser distance meter notes
    The 'data_string' dictates the type of data and the frequency of measurements.
    The options are:
        s0o = turn laser on and leave it on
        s0c = turn laser off and leave it off
        s0g = get a single measurement
        s0h = turn on tracking measurements
        s0f = turn on tracking with buffer
        s0q = get most recent measurement, buffering must be on
        s0t = get temperature measurement
"""

def dimetix_distance(dimetix_raw):
    coretop_cm = float(dimetix_raw)/100
    laser_distance_text.config(text="Distance (cm): " + str(coretop_cm))
    #auxillary_data['coretop_cm'] = coretop_cm

def dimetix_on():
    global dimetix_ON
    dimetix_comm.write(b"s0o\r\n")
    time_.sleep(1)
    dimetix_ON = True

def dimetix_off():
    global dimetix_ON
    global tk_dimetix_continuous_timer
    dimetix_comm.write(b"s0c\r\n")
    dimetix_ON = False
    window.after_cancel(tk_dimetix_continuous_timer)

# def dimetix_single_measurement():
#     dimetix_comm.write(b's0g\r\n')
#     time_.sleep(1)
#     dimetix_raw = dimetix_comm.read(24)
#     dimetix_raw = dimetix_raw[7:].strip()
#     try:
#         coretop_cm = float(dimetix_raw)/100
#     except ValueError:
#         coretop_cm = 0
#     laser_distance_text.config(text="Distance (cm): " + str(coretop_cm))
#     auxillary_data['coretop_cm'] = coretop_cm
    
data_list = []
def dimetix_continuous_distance():
    global dimetix_ON
    global coretop_cm
    global tk_dimetix_continuous_timer
    global auxillary_data
    global current_date, current_time
    if dimetix_ON:
        dimetix_comm.write(b"s0q\r\n")
        dimetix_raw = dimetix_comm.read(24)
        dimetix_raw = dimetix_raw[7:].strip()
        dimetix_raw = dimetix_raw[:-2]
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S") 
            current_date = now.strftime("%Y-%m-%d")
    
            coretop_cm = float(dimetix_raw)/100
            
            new_data = {'date': current_date, 'time': current_time, 'coretop_cm': coretop_cm}
            data_list.append(new_data)
            
            auxillary_data = pd.DataFrame(data_list)

            auxillary_data.to_sql('LaserDistanceData', conn, if_exists='append', index=False)
            conn.commit()
        except ValueError:
            coretop_cm = 0
        laser_distance_text.config(text="Distance (cm): " + str(coretop_cm))
        # auxillary_data['coretop_cm'] = coretop_cm
    else:
        dimetix_on()
        dimetix_comm.write(b"s0f+500\r\n")
    tk_dimetix_continuous_timer = window.after(100, dimetix_continuous_distance)
        

def dimetix_temperature():
    global laser_temperature
    dimetix_comm.write(b"s0t\r\n")
    time_.sleep(1)
    dimetix_raw = dimetix_comm.read(24)
    dimetix_raw = dimetix_raw[3:].strip()
    print(dimetix_raw)
    try:
        laser_temperature = float(dimetix_raw)/10
    except ValueError:
        laser_temperature = 9999
    laser_temperature_text.config(text="Laser temperature (*C): " + str(laser_temperature))

# 
# def set_auxillary_data():
#     for key, value in auxillary_data.items():
#         aux.setData(key, value)


def download_data():
  
    working_directory = r'T:\Disciplines, Programs and Workgroups\Brook Lab\Abakus\Code'
    os.chdir(working_directory)
    
    min_time = auxillary_data['time'].min()
    max_time = auxillary_data['time'].max()

    query = f'''SELECT * FROM LaserDistanceData WHERE date = '{current_date}' AND time BETWEEN '{min_time}' AND '{max_time}' '''

    cursor_l.execute(query)

    distance_sql = cursor_l.fetchall()
    distance_df = pd.DataFrame(distance_sql, columns=[column[0] for column in cursor_l.description])

    file_distance = f"LaserDistance_{current_date}.csv"

    i = 2
    while os.path.exists(file_distance):
        file_distance = f"LaserDistance_{current_date}_{i}.csv"
        i += 1

    distance_df.to_csv(file_distance, index=False)

    tkinter.messagebox.showinfo("Distance File", "Download Complete")

    
    
# App Window

# Appearance
BOARDER_THICKNESS = 1
BACKGROUND_COLOR = "#B1DDC6"
STATUS_BACKGROUND_COLOR = "#B1DDC6"
FONT = "Arial"
TITLE_FONT = (FONT, 16, "bold")
SUBTITLE_FONT = (FONT, 12, "bold")
HEADER_FONT = (FONT, 12, "bold")
TABLE_FONT = (FONT, 12, "normal")
HEADER_PADX = 20
TABLE_PADX = 20

window = tk.Tk()
window.title("Laser Distance Sensor")
#window.geometry("1200x800")
window.config(padx=20, pady=20)

# Layout


# laser frame grid 
laser_frame = tk.Frame(window, padx=10, pady=10,
                       highlightbackground='black',
                       highlightthickness=BOARDER_THICKNESS)
laser_frame.grid(row=1, column=1)

laser_frame_title = tk.Label(laser_frame, text="Laser Distance Meter", font=SUBTITLE_FONT)

laser_button_frame = tk.Frame(laser_frame)

laser_on_button = tk.Button(laser_button_frame, text="Align Laser", command=dimetix_on)
laser_off_button = tk.Button(laser_button_frame, text="Laser OFF", command=dimetix_off)

#laser_single_measurement_button = tk.Button(laser_frame, text="Get Single Measurement", command=dimetix_single_measurement)
laser_continuous_button = tk.Button(laser_frame, text="Get continuous distance measurements", command=dimetix_continuous_distance)
laser_temperature_button = tk.Button(laser_frame, text="Get laser temperature", command=dimetix_temperature)
laser_distance_text = tk.Label(laser_frame, text="Distance (cm): " + str(coretop_cm))
laser_temperature_text = tk.Label(laser_frame, text="Laser temperature (*C): " + str(laser_temperature))

laser_frame_title.grid(row=0, column=0, sticky="W")
laser_continuous_button.grid(row=1, column=0, padx=5, pady=5)

laser_distance_text.grid(row=1, column=1)
#laser_single_measurement_button.grid(row=2, column=0, padx=5, pady=5)
laser_continuous_button.grid(row=4, column=0, padx=5, pady=5)
laser_button_frame.grid(row=5, column=0, padx=5, pady=5)
laser_on_button.pack(side="left")
laser_off_button.pack(side="left")
laser_temperature_button.grid(row=3, column=0)
laser_temperature_text.grid(row=3, column=1)

button_csv = tk.Button(laser_frame, text="Download CSV", command = download_data)
button_csv.grid(row=7, column=0)


# Keep window alive
window.mainloop()

dimetix_comm.close()

########### check data
query = f'select * from LaserDistanceData'
cursor_l.execute(query) 
distance_sql = cursor_l.fetchall()

distance_df = pd.DataFrame(distance_sql, columns = [column[0] for column in cursor_l.description])
distance_df.tail(10)
