### 7-26-24: no data_output dataframe
### 7-26-24: removed Classes
### 7-26-24: add Abakus plot-working!...need to add flow logic. double check first data is saving correctly 
### 7-29-24: added in flow meter plot and tracker
### 7-29-24: added download csv and save graphs and insert note. ValueError: cannot convert float NaN to integer error occurs. When .exe built, does this stop software?
### 7-30-24: Add working directory. Testing stability over time
### 8-5-24: Added break and notes column to concentration file

### build and test

import tkinter as tk
from tkinter import Button, Label
import serial
import sqlite3 as sql
import pandas as pd
from datetime import datetime
import re
import time as time_
import threading
import os

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import numpy as np

# working_directory = r'T:\Disciplines, Programs and Workgroups\Brook Lab\Abakus\Code'
working_directory = r'C:\\Users\\alicl\\Documents\\GitHub'
os.chdir(working_directory)

# Global variables
window = None
counter_label = None
runid_label = None
break_entered_note = None
ser = None
serialIDfm = None
df_flow = pd.DataFrame(columns=['run_id', 'date', 'time', 'flow_rate', 'loop_count'])
data_output = pd.DataFrame(columns=['run_id', 'bins', 'counts', 'time', 'date', 'loop_count'])
loop_count = 0
run_id = 1
regex = r'\b0\d{7}\b'
stop = False
sum_counts = 0
current_flow_rate = 0
conn = None
cursor = None
data_list = []
flowRate = 0
dfs = []
first_run_completed = False
output = pd.DataFrame()
start_time = None

def setup_ui():
    global window, counter_label, runid_label, break_entered_note, fig, ax1, ax2, canvas, ani, flow_label, entry, note_entered, time_label

    ### Labels
    
    time_label = Label(window, text='Time Elapsed: 0 seconds')
    time_label.grid(columnspan=3, row=6, column=0, pady=10)
    
    counter_label = Label(window, text=f'Particle Counts: {sum_counts}')
    counter_label.grid(columnspan=3, row=1, column=0, pady=10)
    
    flow_label = Label(window, text=f'Flow Rate: {current_flow_rate}')
    flow_label.grid(columnspan=3, row=5, column=0, pady=10)
    
    runid_label = Label(window, text='Run ID: Press START to show')
    runid_label.grid(columnspan=3, row=0, column=0, pady=10)
    
    break_entered_note = Label(window, text="Last Break:")
    break_entered_note.grid(row=2, column=2, pady=10, sticky="w") 
    
    input_label = Label(window, text="Insert Note:")
    input_label.grid(row=3, column=2, sticky="w") 
    
    note_entered = Label(window, text = "Last note entered:")
    note_entered.grid(row=5, column=2, sticky="w") 

    ### Buttons

    button_start = Button(window, text="START", padx=30, pady=20, command=button_start_command)
    button_start.grid(columnspan=3, row=2, column=0)

    button_stop = Button(window, text="STOP", padx=33, pady=20, command=close_serial_ports)
    button_stop.grid(columnspan=3, row=3, column=0)
    
    button_break = Button(window, text="Break", padx=15, pady=5, command=ice_break)
    button_break.grid(row=1, column=2, sticky="w")
    
    button_save_graph = Button(window, text="Save Graphs", command=save_graphs)
    button_save_graph.grid(columnspan=3, row=9, column=0)
    
    button_csv = Button(window, text="Download CSV", command = download_data)
    button_csv.grid(columnspan=3, row=9, column=1)
    
    #### Plots
    
    fig = Figure(figsize=(16, 4))
    ax1 = fig.add_subplot(211)  
    ax2 = fig.add_subplot(212) 
    
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.grid(row=8, column=0, columnspan=3, sticky="w") 
    
    ani = animation.FuncAnimation(fig, update_plots, interval=3000, cache_frame_data=False) #change interval to 1000?
    plt.show()
    
    ### Entry
    entry = tk.Entry(window, width=30)
    entry.grid(row=4, column=2, sticky="w")
    entry.bind("<Return>", insert_note)
    
    window.title("Dust Data Collection")

def button_start_command():
    global run_id, start_time
    if open_serial_ports():
        run_id = int(time_.time())
        runid_label.config(text=f'Run ID: {run_id}') 
        start_collecting_data()
        increment_counter()
        update_counts_plot()
        flow_rate_tracker()
        update_flow_plot()
        update_elapsed_time()
        
        start_time = time_.time()
        

def update_elapsed_time():
    global start_time
    #if start_time:
    if not stop:
      try:
        elapsed_time = int(time_.time() - start_time)
        time_label.config(text=f'Time Elapsed: {elapsed_time} seconds')
        window.after(1500, update_elapsed_time) #changed from 1000
      except Exception as e:
        print(f"An error occurred in update_elapsed_time: {str(e)}")
        window.after(1500, update_elapsed_time) #changed from 1000

def open_serial_ports():
    global ser, serialIDfm
    try:
        if ser is None or not ser.is_open:
            ser = serial.Serial('COM4', 38400, timeout=1)
            print("Connected to COM4 with baud 38400")
            ser.write(b'C0\r\n')  # initiate
            ser.write(b'C1\r\n')
            ser.write(b'C5\r\n')
            print("Initiated")

        if serialIDfm is None or not serialIDfm.is_open:
            serialIDfm = serial.Serial('COM3', 115200, timeout=1)
            print("Connected to COM3 with baud 115200")
            start = bytes([0x7e, 0x0, 0x33, 0x2, 0x0, 0x64, 0x66, 0x7e])
            serialIDfm.write(start)

            get = bytes([0x7e, 0x0, 0x35, 0x1, 0x0, 0xc9, 0x7e])
            serialIDfm.write(get)
            response1 = serialIDfm.readline()

        return True

    except serial.SerialException as e:
        print("Error: ", e)
        return False


def collect_abakus():
    global data_list, loop_count, output, filtered_data

    conn = sql.connect('Dust.db', check_same_thread=False)
    cursor = conn.cursor()

    while not stop:
        try:
            loop_count += 1
            ser.write(b'C12\r\n')  # query
            output = ser.readline()
            output = output.decode('utf-8').strip()

            matches = re.findall(regex, output)
            output = ' '.join([match.replace(' ', '')[:8] for match in matches])
            output = pd.Series(output)

            output = output.str.split()
            bins = output.str[::2] 
            counts = output.str[1::2] 
            output = {'bins': bins, 'counts': counts}
            output = pd.DataFrame(output)

            output = pd.concat([output[col].explode().reset_index(drop=True) for col in output], axis=1)

            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            current_date = now.strftime("%Y-%m-%d")

            output['time'] = current_time
            output['date'] = current_date
            output['run_id'] = run_id
            output['loop_count'] = loop_count

            data_list.append(output) #test
        
            output['bins'] = output['bins'].astype(int)
            output['counts'] = output['counts'].astype(int)

            filtered_data = output[output['loop_count'] == loop_count]

            if filtered_data is not None and len(filtered_data) == 32 and not filtered_data.isnull().values.any():
                if loop_count > 1:
                    filtered_data.to_sql('AbakusData', conn, if_exists='append', index=False)
                    conn.commit()
            else:
                print("Ignoring invalid data.")

        except Exception as e:
            print(f"An error occurred: {str(e)}")

        time_.sleep(1.5)

    conn.close()
    
####Flow meter
def parseFlowData(rawdata):
    try:
        adr = rawdata[1]
        cmd = rawdata[2]
        state = rawdata[3]
        if state != 0:
            print('Bad reply from flow meter.')
        length = rawdata[4]
        rxdata8 = rawdata[5:5 + length]
        chkRx = rawdata[5 + length]

        chk = hex(adr + cmd + length + sum(rxdata8))  # convert integer to hexadecimal
        chk = chk[-2:]  # extract the last two characters of the string
        chk = int(chk, 16)  # convert back to an integer base 16 (hexadecimal)
        chk = chk ^ 0xFF  # binary check
        if chkRx != chk:
            print('Bad checksum.')

        rxdata16 = []
        if length > 1:
            i = 0
            while i < length:
                rxdata16.append(bytepack(rxdata8[i], rxdata8[i + 1]))  # convert to a 16-bit integer w/ little-endian byte order
                i = i + 2  # +2 for pairs of bytes

        return adr, cmd, state, length, rxdata16, chkRx

    except IndexError:
        print("IndexError: List index out of range. Skipping this data.")
        return None


def bytepack(byte1, byte2):
	# concatenates 2 uint8 bytes to uint16
	# AND takes 2's complement if negative
	binary16 = (byte1 << 8) | byte2
	return binary16

def twos(binary):
	# takes two's complement of binary input if negative
	# returns input if not negative
	if (binary & (1 << 15)):
		n = -((binary ^ 0xFFFF) + 1)
	else:
		n = binary
	return n
    

def collect_flow_meter():
    global dfs, df_new, loop_count
    conn = sql.connect('Dust.db', check_same_thread=False)
    cursor = conn.cursor()

    while not stop:
        try:
          get = bytes([0x7e, 0x0, 0x35, 0x1, 0x0, 0xc9, 0x7e])
          serialIDfm.write(get)
          response = serialIDfm.readline()
          byte_list = [byte for byte in response]
          rawdata = [int(byte) for byte in byte_list]
          result = parseFlowData(rawdata)
  
          if result is not None:
              adr, cmd, state, length, rxdata, chkRx = result
              ticks = twos(rxdata[0])
              scaleFactor = 5  
              flowRate = (ticks / scaleFactor) / 1000  # Convert ticks to mL/min
  
              now = datetime.now()
              current_time = now.strftime("%H:%M:%S")
              current_date = now.strftime("%Y-%m-%d")
  
              # Create a new DataFrame for each iteration so only most recent incoming data is added to sql table
              df_new = pd.DataFrame([(run_id, current_date, current_time, flowRate, loop_count)], columns=['run_id', 'date', 'time', 'flow_rate', 'loop_count'])
  
              dfs.append(df_new)
  
              df_new.to_sql('FlowData', conn, if_exists='append', index=False, index_label='id')
              conn.commit()

        except ValueError as ve:
          print("ValueError:", ve)
        except IndexError as ie:
            print("IndexError:", ie)
        except Exception as e:
            print("Other Exception:", e)

        except Exception as e:
            print(f"An error occurred: {str(e)}")

        time_.sleep(1)

    conn.close()


def flow_rate_tracker():
    global current_flow_rate
    if not stop:
      try:
          current_flow_rate = round(df_new.at[0, 'flow_rate'],3)
          flow_label.config(text=f'Flow Rate: {current_flow_rate}')
      except Exception as e:
        print(f"Error occured in flow_rate_tracker: {str(e)}")
      window.after(2000, flow_rate_tracker)
		
   
def start_collecting_data():
    global stop
    stop = False
    threading.Thread(target=collect_abakus, daemon=True).start()
    threading.Thread(target=collect_flow_meter, daemon=True).start()
    

def increment_counter():
    global sum_counts, first_run_completed
    if not stop:
        try:
            if loop_count == 1:
                window.after(1000, increment_counter)
                return
            
            sum_counts = output['counts'].astype(int).sum()
            counter_label.config(text=f'Particle Counts: {sum_counts}')
        
        except Exception as e:
            print(f"An error occurred in increment_counter: {str(e)}")
        
        window.after(1000, increment_counter)


def close_serial_ports():
    global stop, ser, serialIDfm

    try:
        stop = True
        if ser is not None and ser.is_open:
            ser.write(b'C6\r\n')  # stop
            ser.write(b'C0\r\n')  # exit
            ser.close()
        
        if serialIDfm is not None and serialIDfm.is_open:
            serialIDfm.close()
    except serial.SerialException as e:
        print("Error: ", e)

def ice_break():
    global cursor, conn, run_id

    query_a = f'''
    UPDATE AbakusData
    SET break = 'True'
    WHERE time = (SELECT MAX(time) FROM AbakusData WHERE run_id = {run_id})
    AND run_id = {run_id}'''
    cursor.execute(query_a)
    conn.commit()

    query_f = f'''
    UPDATE FlowData
    SET break = 'True'
    WHERE time = (SELECT MAX(time) FROM FlowData WHERE run_id = {run_id})
    AND run_id = {run_id}'''
    cursor.execute(query_f)
    conn.commit()
    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    break_entered_note.config(text=f'Last break: {current_time}')


#### Plotting   

def update_counts_plot():
    
    try:
        if not data_list:
            print("Error: data_list is empty or None.")
            return
    
        data_output = pd.concat(data_list, ignore_index=True)
    
        if data_output.empty:
            print("Error: Concatenated data_output is empty.")
            return
    
        filtered_data = data_output[data_output['loop_count'] > 1]  # Filter out negative counts
        data_output_grouped = filtered_data.groupby('time')['counts'].sum().reset_index()
        data_output_grouped['time'] = pd.to_datetime(data_output_grouped['time'], format='%H:%M:%S')
        time_abakus = data_output_grouped['time']
    
        data_output_grouped['lag_counts'] = data_output_grouped['counts'].shift(1)
        new_counts = abs(data_output_grouped['counts'] - data_output_grouped['lag_counts'])
    
        time_diff = (data_output_grouped['time'] - data_output_grouped['time'].shift(1)).dt.total_seconds()
        adj_counts = new_counts / time_diff
    
        ax1.plot(time_abakus, adj_counts, color="black")
        ax1.set_ylabel("Counts per query")
        ax1.set_title("Particle Counts Over Time")
        ax1.set_xticklabels([])
    
        canvas.draw_idle()
        canvas.flush_events()
        
    except Exception as e:
        print(f"An error occurred in update_counts_plot: {str(e)}")

def update_flow_plot():
    try:
      times = [df['time'] for df in dfs]
      times_as_strings = [str(series[0]) for series in times]
      flow_rates = [df['flow_rate'] for df in dfs]
      flow_rates_as_floats = [series.iloc[0] for series in flow_rates]
      
      num_displayed_ticks = 10
      step_size = max(1, len(times_as_strings) // num_displayed_ticks) 
      x_ticks = times_as_strings[::step_size]
  
      
      ax2.plot(times_as_strings, flow_rates_as_floats, color="black")
      ax2.set_xlabel("Time")
      ax2.set_xticks(x_ticks)
      ax2.set_ylabel("Flow rate (ml/min)")
      ax2.set_title("Flow Rate Over Time")
  
      canvas.draw_idle()
      canvas.flush_events()
    except Exception as e:
      print(f"An error occurred in update_flow_plot: {str(e)}")


def update_plots(frame):
    update_counts_plot()
    update_flow_plot()
    canvas.draw_idle()

def set_sql_conn(): 
    global conn, cursor
    conn = sql.connect('Dust.db', check_same_thread=False)
    cursor = conn.cursor()

def get_sql_data():
    ### Concentrations file 
    cursor.execute("""
    	SELECT
      t1.run_id,
    	t1.date,
    	t1.time as time_flow,
    	t1.counts,
    	t1.flow_rate,
    	t1.new_counts,
    	t1.concentration,
    	t1.time_diff,
    	t1.new_counts/t1.time_diff as adj_counts,
    	(t1.new_counts/t1.time_diff)/t1.flow_rate as adj_concentration,
    	t1.loop_count,
    	t1.notes,
    	t1.break
    
    	FROM (
    		SELECT
          a.run_id,
          f.time,
    			a.date,
    			SUM(a.counts) as counts,
    			f.flow_rate,
    			ABS(SUM(a.counts) - LAG(SUM(a.counts), 1, 0) OVER (PARTITION BY a.date)) as new_counts,
    			ABS((SUM(a.counts) - LAG(SUM(a.counts), 1, 0) OVER (PARTITION BY a.date)) / f.flow_rate) as concentration,
    			STRFTIME('%s', a.time) - STRFTIME('%s', LAG(a.time) OVER (ORDER BY a.time)) AS time_diff,
    			a.loop_count,
    			a.notes,
    			a.break
    		FROM AbakusData a
    		LEFT JOIN FlowData f ON f.run_id = a.run_id AND a.loop_count = f.loop_count
    		WHERE a.run_id = (SELECT MAX(a.run_id) FROM AbakusData a)
    		GROUP BY a.run_id, f.time, a.date, a.loop_count, a.notes, a.break
    	) t1
     """)

    summed_counts = cursor.fetchall()
    summed_counts_df = pd.DataFrame(summed_counts, columns=[column[0] for column in cursor.description])

    now = datetime.now()
    todays_date = now.strftime("%Y-%m-%d")
    
    file_conc = f"Concentrations_{todays_date}.csv"

    i = 2
    while os.path.exists(file_conc):
        file_conc = f"Concentrations_{todays_date}_{i}.csv"
        i += 1
    
    summed_counts_df.to_csv(file_conc, index=False)

    ### Abakus file
    cursor.execute("SELECT * FROM AbakusData WHERE run_id = (SELECT MAX(run_id) FROM AbakusData)") 

    data_output_sql = cursor.fetchall()
    data_output_sql = pd.DataFrame(data_output_sql, columns=[column[0] for column in cursor.description])

    file_abakus = f"Abakus_{todays_date}.csv"

    i = 2
    while os.path.exists(file_abakus):
        file_abakus = f"Abakus_{todays_date}_{i}.csv"
        i += 1
    
    data_output_sql.to_csv(file_abakus, index=False)

    ### Flow meter file
    cursor.execute("SELECT * FROM FlowData WHERE run_id = (SELECT MAX(run_id) FROM FlowData)")

    df_flow_sql = cursor.fetchall()
    df_flow_sql = pd.DataFrame(df_flow_sql, columns=[column[0] for column in cursor.description])

    file_flow = f"FlowMeter_{todays_date}.csv"

    i = 2
    while os.path.exists(file_flow):
        file_flow = f"FlowMeter_{todays_date}_{i}.csv"
        i += 1
    
    df_flow_sql.to_csv(file_flow, index=False)
    
    tk.messagebox.showinfo("Abakus File", "Download Complete")
    
def download_data():
  set_sql_conn()
  get_sql_data()
  
def save_graphs():
  fig.savefig(f'Abakus and Flow Plot_{run_id}.png')
  
def insert_note(event=None):
  global note_entered
  
  input_note = entry.get()

  note_a = f'''
    UPDATE AbakusData
    SET notes = '{input_note}'
    WHERE time = (SELECT MAX(time) FROM AbakusData WHERE run_id = {run_id})
    AND run_id = {run_id}'''
  cursor.execute(note_a)
  conn.commit()

  note_f = f'''
    UPDATE FlowData
    SET notes = '{input_note}'
    WHERE time = (SELECT MAX(time) FROM FlowData WHERE run_id = {run_id})
    AND run_id = {run_id}'''
  cursor.execute(note_f)
  conn.commit()

  now = datetime.now()
  current_time = now.strftime("%H:%M:%S")
  note_entered.config(text=f'Last note entered: {input_note}')
  
#########################################################################################################
  
if __name__ == "__main__":
    window = tk.Tk()
    set_sql_conn()
    setup_ui()
    window.mainloop()
