import numpy as np
import time
import pandas as pd

import tkinter as tk
from tkinter import *
from tkinter.ttk import Notebook, Sizegrip, Separator
from tkinter.font import Font, BOLD

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class GUI():
    def __init__(self, sensors:list, start_callbacks=None, stop_callbacks=None):
        # Make the window and set some size parameters
        self.root = tk.Tk()
        self.root.title("Sample MGR GUI")
        self.root.geometry('1000x700')
        
        self.grid_width = 150
        self.grid_height = 50

        # Make some default fonts
        self.bold16 = Font(self.root, family="Helvetica", size=16, weight=BOLD)

        # Grab the names of the sensors
        self.sensor_names = sensors
       
        # Set up the data grid that will eventually contain sensor status / control, fow now it's empty
        status_grid_frame = Frame(self.root)
        self.make_status_grid_loop(status_grid_frame, names=self.sensor_names, callbacks=None)

        # make a dict of matplotlib figures to put in the notebook
        self.f1 = plt.figure(1)
        self.a = self.f1.add_subplot(111)
        self.f2 = plt.figure(2)
        self.a2 = self.f2.add_subplot(111)

        # Set up data streaming
        self.data_streaming_windows = []

        data_streaming_frame = Frame(self.root, bg="purple")
        self.make_data_stream_notebook(data_streaming_frame)
        self.one_stream(self.f1, self.data_streaming_windows[0])
        self.one_stream(self.f2, self.data_streaming_windows[1])
    

        # initialize fake data
        self.index = 0
        self.index2 = 0
        self.xdata1 = []
        self.ydata1 = []
        self.xdata2 = []
        self.ydata2 = []

        # initialize real data buffers
        self.abakus_buffer = {"time (epoch)": [0.0], "total counts": [0]}
        self.flowmeter_sli2000_buffer = {"time (epoch)": [0.0], "flow (uL/min)": [0.0]}
        self.flowmeter_sls1500_buffer = {"time (epoch)": [0.0], "flow (mL/min)": [0.0]}
        self.laser_buffer = {"time (epoch)": [0.0], "distance (cm)": [0.0], "temperature (°C)": [99.99]}
        self.picarro_gas_buffer = {"time (epoch)":[0.0], "sample time":[0.0], "CO2":[0.0], "CH4":[0.0], "CO":[0.0], "H2O":[0.0]}
        
        # make some buttons! One toggles the other on/off, example of how to disable buttons 
        # and do callbacks with arguments
        b1 = self.pack_button(data_streaming_frame, callback=None, loc='bottom')
        b2 = self.pack_button(data_streaming_frame, callback=lambda: self.toggle_button(b1), loc='bottom', text="I toggle the other button")
                
        # add a sizegrip to the bottom
        sizegrip = Sizegrip(self.root)
        sizegrip.pack(side="bottom", expand=False, fill=BOTH, anchor=SE)

        # pack the frames
        status_grid_frame.pack(side="left", expand=True, fill=BOTH)
        data_streaming_frame.pack(side="right", expand=True, fill=BOTH)

    ## --------------------- HELPER FUNCTIONS: BUFFER UPDATE --------------------- ##

    def update_picarro_gas_buffer(self, new_dict:dict):
        old_keys = self.picarro_gas_buffer.keys()
        new_keys = new_dict.keys()
        assert(old_keys != new_keys, "picarro dictionary keys don't match")

        for key in old_keys:
            self.picarro_gas_buffer[key] = new_dict[key]

    def update_abakus_buffer(self, time, counts):
        self.abakus_buffer["time (epoch)"].append(float(time))
        self.abakus_buffer["total counts"].append(int(counts))
    
    ## --------------------- LAYOUT --------------------- ##
    
    def pack_button(self, root, callback, loc:str="right", text="I'm a button :]"):
        """General method that creates and packs a button inside the given root"""
        button = Button(root, text=text, command=callback)
        button.pack(side=loc)
        return button
  
    ## --------------------- LIVE PLOTTING --------------------- ##
    
    def get_data(self):
        self.xdata1.append(self.index)
        self.ydata1.append(np.random.randint(0, 5))
        self.index += 1

    def get_data2(self):
        self.xdata2.append(self.index2)
        self.ydata2.append(np.random.randint(-5, 5))
        self.index2 += 1
    
    def animate(self, i):
        self.get_data()
        self.a.clear()
        self.a.plot(self.xdata1, self.ydata1)

    def animate2(self, i):
        # self.get_data2()
        self.a2.clear()
        to_plot = np.array(self.abakus_buffer["total counts"])+np.random.rand()
        print(to_plot)
        self.a2.plot(to_plot)
        
    def one_stream(self, f, root):
        canvas = FigureCanvasTkAgg(f, root)
        canvas.draw()
        time.sleep(0.1)
        canvas.get_tk_widget().grid(row=1, column=0) 

    def make_data_stream_notebook(self, root):
        notebook = Notebook(root)
        for name in self.sensor_names:
            window = Frame(notebook)
            window.grid()
            label = Label(window, text=name+" Data", font=self.bold16)
            label.grid(column=0, row=0)
            notebook.add(window, text=name)
            self.data_streaming_windows.append(window)
    
        notebook.pack(padx = 5, pady = 5, expand = True)

    ## --------------------- "STATUS" GRID --------------------- ##
   
    def make_status_grid_cell(self, root, col, row, colspan=1, rowspan=1, color='white'):
        """Method to make one frame of the grid at the position given"""        
        frame = Frame(root, relief='ridge', borderwidth=2.5, bg=color, highlightcolor='blue')
        # place in the position we want and make it fill the space (sticky)
        frame.grid(column=col, row=row, columnspan=colspan, rowspan=rowspan, sticky='nsew')
        # make it stretchy if the window is resized
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        return frame 
    
    def make_status_grid_loop(self, root:Frame, names, callbacks):
        """Makes a grid of all the sensors. Currently a placeholder for anything we 
        want to display about the instruments, like adding control or their status"""
        num_cols = 2   # might make this dynamic later
        num_rows = round(len(names) / num_cols)

        self.start_all_frame = self.make_status_grid_cell(root, col=0, row=0, colspan=num_cols)
        label=Label(self.start_all_frame, text="Start All Data Collection")
        label.grid(row=0, column=0)

        self.sensor_status_frames = [] # append all frames to a list, just in case we want to access them later
        i = 0
        for row in range(1,num_rows+1):
            for col in range(num_cols):
                frame = self.make_status_grid_cell(root, col=col, row=row)
                label = Label(frame, text=names[i], justify='center')
                label.grid(row=0, column=0)
                # add a button
                self.sensor_status_frames.append(frame)
                i += 1

        # Make the grid stretchy if the window is resized, with all the columns and rows stretching by the same weight
        root.columnconfigure(np.arange(num_cols).tolist(), weight=1, minsize=self.grid_width)
        root.rowconfigure(np.arange(num_rows+1).tolist(), weight=1, minsize=self.grid_height) # "+1" for the title row
 
    
    ## --------------------- CALLBACKS --------------------- ##
    
    def toggle_button(self, button: Button):
        """Method that toggles a button between its 'normal' state and its 'disabled' state"""
        if button["state"] == NORMAL:
            button["state"] = DISABLED
        else:
            button["state"] = NORMAL

    def run_cont(self):
        self.root.mainloop()
        self.root.destroy()

    def run(self, delay=0):
        # self.root.update_idletasks()
        self.root.update()
        # time.sleep(delay)

    ##  --------------------- HELPER FUNCTIONS  --------------------- ##

    def update_data1(self, new_x, new_y):
        self.xdata1.append(new_x)
        self.ydata1.append(new_y)

    def update_data2(self, new_x, new_y):
        self.xdata2.append(new_x)
        self.ydata2.append(new_y)

if __name__ == "__main__":
    sensors = ["Picarro Gas", "Picarro Water", "Laser Distance Sensor", "Abakus Particle Counter",
                       "Flowmeter SLI2000 (Green)", "Flowmeter SLS1500 (Black)", "Bronkhurst Pressure", "Melthead"]
    start_callbacks = [None]*len(sensors)
    stop_callbacks = [None]*len(sensors)

    app = GUI(sensors, start_callbacks, stop_callbacks)
    ani1 = FuncAnimation(app.f1, app.animate, interval=1000, cache_frame_data=False)
    ani2 = FuncAnimation(app.f2, app.animate2, interval=1000, cache_frame_data=False)

    while True:
        app.run()