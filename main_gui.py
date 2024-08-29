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

        # Make matplotlib figures to put in the data streaming notebook
        self.f1 = plt.figure(1)
        self.a = self.f1.add_subplot(111)
        self.f2 = plt.figure(2)
        self.a2 = self.f2.add_subplot(111)

        # Set up data streaming
        data_streaming_frame = Frame(self.root, bg="purple")
        self.make_data_stream_notebook(data_streaming_frame)
        self.init_data_streaming_figs()
        self.init_data_streaming_canvases()
        self.init_data_streaming_animations()

        # not sure the best data management yet, will eventually need to specify how many plots per sensor
        # putting this empty dict here to remind me
        self.num_subplots = {}
    
        # initialize fake data - will eventually be deleted
        self.index = 0
        self.xdata1 = []
        self.ydata1 = []

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
        # assert(old_keys != new_keys, "picarro dictionary keys don't match")

        for key in old_keys:
            self.picarro_gas_buffer[key] = new_dict[key]

    def update_abakus_buffer(self, time, counts):
        """Method to update the abakus buffer for plotting"""
        time = float(time)
        counts = int(counts) + np.random.rand()
        self.abakus_buffer["time (epoch)"].append(time)
        self.abakus_buffer["total counts"].append(counts)
    
    ## --------------------- LAYOUT --------------------- ##
    
    def pack_button(self, root, callback, loc:str="right", text="I'm a button :]"):
        """General method that creates and packs a button inside the given root"""
        button = Button(root, text=text, command=callback)
        button.pack(side=loc)
        return button
  
    ## --------------------- DATA STREAMING DISPLAY --------------------- ##

    def init_data_streaming_figs(self):
        """Initializes dictionaries of matplotlib figs and axes for each sensor. These get saved
        and called later for live plotting
        
            Updates - self.streaming_data_figs & self.streaming_data_axes"""
        self.data_streaming_figs = {}
        self.data_streaming_axes = {}
        # For each sensor, generate and save a unique matplotlib figure and corresponding axis
        for name in self.sensor_names:
            fig = plt.figure(name)
            self.data_streaming_figs.update({name:fig})
            self.data_streaming_axes.update({name:fig.add_subplot(111)}) # could pass in a term for how many plots per sensor

    def one_canvas(self, f, root):
        """General method to set up a canvas in a given frame. I'm eventually using each canvas
        to hold a matplotlib figure for live plotting"""
        canvas = FigureCanvasTkAgg(f, root)
        canvas.draw()
        time.sleep(0.1)
        canvas.get_tk_widget().grid(row=1, column=0) 

    def init_data_streaming_canvases(self):
        """Sets up a tkinter canvas for each sensor in its own tkinter frame (stored in self.data_streaming_windows).
        It might not look like anything is getting saved here, but Tkinter handles parent/child relationships internally,
        so the canvases exist wherever Tkinter keeps the frames"""
        for name in self.sensor_names:
            # Grab the appropriate matplotlib figure and root window
            fig = self.data_streaming_figs[name]
            window = self.data_streaming_windows[name]
            # Make a canvas to hold the figure in that window
            self.one_canvas(fig, window)

    def init_data_streaming_animations(self):
        """Initializes a matplotlib FuncAnimation for each sensor and stores it in a dictionary.
        
            Updates - self.streaming_anis (dict, holds the FuncAnimations)"""
        self.data_streaming_anis = {}
        # For each sensor, grab the corresponding matplotlib figure and axis. Pass that, along with the sensor name and 
        # self.animate_general method, into a FuncAnimation. Finally, save the FuncAnimation to make sure the animation
        # doesn't vanish when this function finishes
        for name in self.sensor_names:
            fig = self.data_streaming_figs[name]
            axis = self.data_streaming_axes[name]
            n_subplots = 0
            ani = FuncAnimation(fig, self.animate_general, fargs=(name, axis, n_subplots), interval=1000, cache_frame_data=False)
            self.data_streaming_anis.update({name:ani})

    def animate_general(self, i, sensor_name, axis:plt.Axes, num_subplots):
        """Method to pass into FuncAnimation, grabs data from the appropriate sensor buffer (not yet)
        and plots it on the given axis"""
        self.get_data(sensor_name)
        axis.clear()
        axis.plot(self.xdata1, self.ydata1)
    
    def get_data(self, sensor_name):
        """Dummy helper method to randomly generate x and y values for plotting, will eventually
        grab data from the appropriate buffer"""
        self.xdata1.append(self.index)
        self.ydata1.append(np.random.randint(0, 5))
        self.index += 1
    
    def animate(self, i):
        """Basic animation function for xdata1 and ydata 1, will eventually have one for each sensor. Could
            potentially streamline with lambda functions or a big if/elif/else"""
        self.get_data()
        self.data_streaming_axes["dummy"].clear()
        self.data_streaming_axes["dummy"].plot(self.xdata1, self.ydata1)
    
    def make_data_stream_notebook(self, root):
        """
        Method to set up a tkinter notebook with a page for each sensor (stored in self.sensor_names)
            
        Updates - self.data_streaming_windows (dict of tkinter frames that live in the notebook, can be referenced
        for plotting, labeling, etc)
        """
        self.data_streaming_windows = {}
        notebook = Notebook(root)
        for name in self.sensor_names:
            window = Frame(notebook)
            window.grid()
            label = Label(window, text=name+" Data", font=self.bold16)
            label.grid(column=0, row=0)
            notebook.add(window, text=name)
            self.data_streaming_windows.update({name: window})
    
        notebook.pack(padx=2.5, pady=2.5, expand = True)

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

        # Make a frame for the title row
        self.start_all_frame = self.make_status_grid_cell(root, col=0, row=0, colspan=num_cols)
        label=Label(self.start_all_frame, text="Start All Data Collection")
        label.grid(row=0, column=0)

        self.sensor_status_frames = [] # append all frames to a list, just in case we want to access them later
        i = 0
        try:
            for row in range(1,num_rows+1):
                for col in range(num_cols):
                    frame = self.make_status_grid_cell(root, col=col, row=row)
                    label = Label(frame, text=names[i], justify='center')
                    label.grid(row=0, column=0)
                    # add a button 
                    self.sensor_status_frames.append(frame)
                    i += 1
        except IndexError as e:
            print(f"Exception in building status grid loop: {e}. Probably your sensors don't divide evenly by {num_cols}")

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

if __name__ == "__main__":
    # sensors = ["Picarro Gas", "Picarro Water", "Laser Distance Sensor", "Abakus Particle Counter",
    #                    "Flowmeter SLI2000 (Green)", "Flowmeter SLS1500 (Black)", "Bronkhurst Pressure", "Melthead"]

    sensors = ["dummy", "Picarro Gas", "Picarro Water"]
    start_callbacks = [None]*len(sensors)
    stop_callbacks = [None]*len(sensors)

    app = GUI(sensors, start_callbacks, stop_callbacks)
    # ani1 = FuncAnimation(app.f1, app.animate, interval=1000, cache_frame_data=False)
    # ani2 = FuncAnimation(app.f2, app.animate2, interval=1000, cache_frame_data=False)

    while True:
        app.run()