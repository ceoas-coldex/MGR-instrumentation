import numpy as np
import time
import pandas as pd
from collections import deque
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter.ttk import Notebook, Sizegrip, Separator
from tkinter.font import Font, BOLD

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class GUI():
    """This is the Graphical User Interface, or GUI! It sets up the user interface for the main pipeline.  
        I've tried to make it as modular as possible, so adding additional sensors in the future won't be as much of a pain."""
    def __init__(self, button_callback_dict):
        """Initializes everything"""
        ##  --------------------- SIZE & FORMATTING --------------------- ##
        # Make the window and set some size parameters
        self.root = tk.Tk()
        self.root.title("Sample MGR GUI")
        self.width = 1700
        self.height = 1200
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.resizable(False, False)
        
        self.grid_width = 150 # px? computer screen units?
        self.grid_height = 50

        # Make some default colors
        self.light_blue = "#579cba"
        self.dark_blue = "#083054"

        # Make some default fonts
        self.bold16 = Font(self.root, family="Helvetica", size=16, weight=BOLD)
        self.bold12 = Font(self.root, family="Helvetica", size=12, weight=BOLD)

        # Set some styles
        s = ttk.Style()
        s.configure('TNotebook.Tab', font=self.bold12, padding=[10, 5])
        s.configure('TNotebook', background=self.light_blue)
        s.layout("TNotebook", []) # get rid of the notebook border

        ##  --------------------- INSTRUMENTS & DATA BUFFER MANAGEMENT --------------------- ##
        max_buffer_length = 500 # how long we let the buffers get, helps with memory
        self._init_data_buffer(max_buffer_length)

        # initialize dummy data buffers - will eventually delete this, currently for testing
        self.index = 0
        self.x_dummy = []
        self.y_dummy = []

        ## --------------------- GUI LAYOUT --------------------- ##
        # Set up the data grid that will eventually contain sensor status / control, fow now it's empty
        status_grid_frame = Frame(self.root)
        self.button_callback_dict = button_callback_dict
        self._init_status_grid(status_grid_frame)

        # Set up the notebook for data streaming/live plotting
        data_streaming_frame = Frame(self.root, bg=self.light_blue)
        self._init_data_streaming_notebook(data_streaming_frame)
        self._init_data_streaming_figs()
        self._init_data_streaming_canvases()
        self._init_data_streaming_animations(animation_delay=1000) #1s of delay in between drawing frames, adjust later
        
        # make some buttons! One toggles the other on/off, example of how to disable buttons and do callbacks with arguments
        # logging_frame = Frame(self.root, bg="white")
        # b1 = self.pack_button(logging_frame, callback=None, loc='bottom', default=DISABLED)
        # b2 = self.pack_button(logging_frame, callback=lambda: self.toggle_button(b1), loc='bottom', text="I toggle the other button")

        # pack the frames
        status_grid_frame.pack(side="left", expand=True, fill=BOTH)
        data_streaming_frame.pack(side="right", expand=True, fill=BOTH)
        # logging_frame.pack(side="bottom", expand=False, fill=X, anchor=S)
        
    ## --------------------- LAYOUT --------------------- ##
    
    def pack_button(self, root, callback, loc:str="right", text="I'm a button :]", default=NORMAL):
        """General method that creates and packs a button inside the given root"""
        button = Button(root, text=text, command=callback, state=default)
        button.pack(side=loc)
        return button
  
    ## --------------------- DATA STREAMING DISPLAY --------------------- ##

    def _init_data_buffer(self, max_buffer_length):
        # Read in the sensor data config file to initialize the data buffer. 
        # Creates an empty dictionary with keys to assign timestamps and data readings to each sensor
        with open("config/sensor_data.yaml", 'r') as stream:
            self.big_data_dict = yaml.safe_load(stream)

        # Comb through the keys, set the timestamp to the current time and the data to zero
        sensor_names = self.big_data_dict.keys()
        for name in sensor_names:
            self.big_data_dict[name]["Time (epoch)"] = deque([], maxlen=max_buffer_length)
            channels = self.big_data_dict[name]["Data"].keys()
            for channel in channels:
                self.big_data_dict[name]["Data"][channel] = deque([], maxlen=max_buffer_length)

        # Grab the names of the sensors from the dictionary
        self.sensor_names = list(sensor_names)
    
    def _init_data_streaming_notebook(self, root):
        """
        Method to set up a tkinter notebook with a page for each sensor (stored in self.sensor_names)
            
        Updates - self.data_streaming_windows (dict of tkinter frames that live in the notebook, can be referenced
        for plotting, labeling, etc)
        """
        # Create a tkinter Notebook and add a frame for each sensor
        self.data_streaming_windows = {}
        notebook = Notebook(root)
        for name in self.sensor_names:
            window = Frame(notebook)
            window.configure(background=self.light_blue)
            window.grid(column=0, row=1, sticky=NSEW)
            notebook.add(window, text=name)
            # Append the frames to a dict so we can access them later
            self.data_streaming_windows.update({name:window})

        notebook.pack(padx=2, pady=1, expand = True)
    
    def _init_data_streaming_figs(self):
        """Initializes matplotlib figs and axes for each sensor. These get saved and called later for live plotting
        
            Updates - self.streaming_data_figs (dict of matplotlib figures)"""
        # For each sensor, generate and save a unique matplotlib figure and corresponding axes
        self.data_streaming_figs = {}
        for name in self.sensor_names:
            # We want to make a subplot for each data channel per sensor, so grab those
            channels = list(self.big_data_dict[name]["Data"].keys())
            num_subplots = len(channels)
            # Create a figure and size it based on the number of subplots
            fig = plt.figure(name, figsize=(10.5,4*num_subplots))
            self.data_streaming_figs.update({name:fig})
            # Add the desired number of subplots to each figure
            for i in range(0, num_subplots):
                fig.add_subplot(num_subplots,1,i+1)
            
            # A little cheesy - futz with the whitespace by adjusting the position of the top edge of the subplots 
            # (as a fraction of the figure height) based on how many subplots we have. For 1 subplot put it at 90% of the figure height, 
            # for 4 subplots put it at 97%, and interpolate between the two otherwise
            plt.subplots_adjust(top=np.interp(num_subplots, [1,4], [0.9,0.97]))

    def _one_canvas(self, f, root, vbar:Scrollbar, num_subplots) -> FigureCanvasTkAgg:
        """General method to set up a canvas in a given root. I'm eventually using each canvas
        to hold a matplotlib figure for live plotting
        
        Args - f (matplotlib figure), root (tkinter object), vbar (tkinter Scrollbar), 
        num_subplots(int, how many subplots we want on this canvas. Used to set the size of the scroll region)"""
        # Initialize and render a matplotlib embedded canvas
        canvas = FigureCanvasTkAgg(f, root)
        canvas.draw()
        canvas.get_tk_widget().config(bg='white', # set the background color 
                                      scrollregion=(0,0,0,num_subplots*(self.height/2.5)), # set the size of the scroll region in screen units
                                      yscrollcommand=vbar.set, # link the scrollbar to the canvas
                                      )
        canvas.get_tk_widget().grid(row=0, column=0)

        # Set the scrollbar command and position
        vbar.config(command=canvas.get_tk_widget().yview)
        vbar.grid(row=0, column=1, sticky=N+S)
        # Bind the scrollbar to the mousewheel
        canvas.get_tk_widget().bind("<MouseWheel>", self._on_mousewheel)

    def _init_data_streaming_canvases(self):
        """
        Sets up a tkinter canvas for each sensor in its own tkinter frame and with its own matplotlib figure. 
        The frames were set up in _init_data_streaming_notebook(), and the figures in _init_data_streaming_figs(). We pass
        the frame and figure into a canvas (FigureCanvasTkAgg object), set up a scrollbar, and bind the scrollbar to the mousewheel.

        It might not look like anything is getting saved here, but Tkinter handles parent/child relationships internally,
        so the canvases exist wherever Tkinter keeps the frames
        """
        for name in self.sensor_names:
            # Grab the appropriate matplotlib figure and root window (a tkinter frame)
            fig = self.data_streaming_figs[name]
            window = self.data_streaming_windows[name]
            # Make a scrollbar
            vbar = Scrollbar(window, orient=VERTICAL)
            # Make a canvas to hold the figure in the window, and set up the scrollbar
            self._one_canvas(fig, window, vbar, num_subplots = len(fig.get_axes()))

    def _init_data_streaming_animations(self, animation_delay=1000):
        """
        Initializes a matplotlib FuncAnimation for each sensor and stores it in a dictionary.
        
            Args - animation_delay (int, number of ms to delay between live plot updates) \n
            Updates - self.streaming_anis (dict, holds the FuncAnimations)
        """
        self.data_streaming_anis = {}
        for name in self.sensor_names:
            # For each sensor, grab the corresponding matplotlib figure and axis.
            fig = self.data_streaming_figs[name]
            axes = fig.get_axes()
            # Use the figure and axis to create a FuncAnimation
            ani = FuncAnimation(fig, self._animate_general, fargs=(name, axes), interval=animation_delay, cache_frame_data=False)
            # Save the animation to make sure it doesn't vanish when this function ends
            self.data_streaming_anis.update({name:ani})

    def _animate_general(self, i, sensor_name:str, axes:list):
        """Method to pass into FuncAnimation, grabs data from the appropriate sensor buffer and plots it on the given axis
        
            Args - sensor_name (str, must correspond to a key in self.big_data_dict), axis (list of Axes objects)"""
        xdata, ydata, ylabels = self.get_data(sensor_name)
        # ydata is a list of lists, one for each channel of the sensor. Iterate through and plot them on the corresponding subplot
        for i, y in enumerate(ydata):
            axes[i].clear()
            axes[i].plot(xdata, y)
            axes[i].set_xlabel("Time (epoch)")
            axes[i].set_ylabel(ylabels[i])
        axes[0].set_title(sensor_name)
        # plt.tight_layout(pad=0.25)
    
    def get_data(self, sensor_name):
        """Method that combs through the data buffer dictionary and pulls out the timestamp and channels corresponding
        to the given sensor_name.
            
            Args - sensor_name (str, must match the keys in big_data_dict)

            Returns - x_data (list of floats, timestamp buffer), y_data (list of lists, all the data channels of the given sensor),
                channels (list of strings, name of the channel)"""
        # Pull out the timestamp corresponding to the sensor name
        x_data = self.big_data_dict[sensor_name]["Time (epoch)"]
        # Pull out the keys under the "Data" subsection of the sensor to get a list of the channel names
        channels = list(self.big_data_dict[sensor_name]["Data"].keys())
        # For each channel, grab the data and append to a list
        y_data = []
        for channel in channels:
            y_data.append(self.big_data_dict[sensor_name]["Data"][channel])
        return x_data, y_data, channels
    
    def dummy_data(self):
        """Dummy helper method to randomly generate x and y values for testing"""
        self.x_dummy.append(self.index)
        self.y_dummy.append(np.random.randint(0, 5))
        self.index += 1

    def update_buffer(self, new_data:dict, use_noise=False):
        """Method to update the self.big_data_dict buffer with new data from the sensor pipeline.
        
            Args - new_data (dict, most recent data update. Should have the same key/value structure as big_data_dict),
            use_noise (bool, adds some random noise if true. Will delete eventually)
        """
        # For each sensor name, grab the timestamp and the data from each sensor channel. If it's in a list, take the
        # first index, otherwise, append the dictionary value directly
        for name in self.sensor_names:
            # Grab and append the timestamp
            try:    # Check if the dictionary key exists... 
                new_time = new_data[name]["Time (epoch)"]  
                self.big_data_dict[name]["Time (epoch)"].append(new_time)
            except KeyError as e:   # ... otherwise log an exception
                print(f"Error updating the {name} buffer: {e}")
            
            # Grab and append the data from each channel
            channels = list(self.big_data_dict[name]["Data"].keys())
            for channel in channels:
                if use_noise: # If we're using noise, set that (mostly useful for visual plot verification with simulated sensors)
                    noise = np.random.rand()
                else:
                    noise = 0
                try:    # Check if the dictionary key exists... 
                    ch_data = new_data[name]["Data"][channel] + noise
                    self.big_data_dict[name]["Data"][channel].append(ch_data)
                except KeyError:    # ... otherwise log an exception
                    print(f"Error updating the {name} buffer: {e}")

    ## --------------------- "STATUS" GRID --------------------- ##
   
    def _make_status_grid_title(self, root, num_cols, button_width=20):
        pad = int(button_width / 2)
        title_frame = self._make_status_grid_cell(root, title="Sensor Status & Control", col=0, row=0, colspan=num_cols)

        init_sensor_button = Button(title_frame, text="Initialize All Sensors", font=self.bold16, width=button_width, command=self._on_sensor_init)
        init_sensor_button.grid(column=0, row=1, sticky=W, padx=pad, pady=pad)

        shutdown_sensor_button = Button(title_frame, text="Shut Down All Sensors", font=self.bold16, width=button_width, command=self._on_sensor_shutdown)
        shutdown_sensor_button.grid(column=1, row=1, sticky=E, padx=pad)

        start_data_button = Button(title_frame, text="Start Data Collection", font=self.bold16, width=button_width, state=DISABLED, command=self._on_start_data)
        start_data_button.grid(column=0, row=2, sticky=W, padx=pad)
        self.buttons_to_enable_after_init.append(start_data_button)

        stop_data_button = Button(title_frame, text="Stop Data Collection", font=self.bold16, width=button_width, state=DISABLED, command=self._on_stop_data)
        stop_data_button.grid(column=1, row=2, sticky=E, padx=pad)
        self.buttons_to_enable_after_init.append(stop_data_button)
    
    def _make_status_grid_cell(self, root, title, col, row, start_callback=None, stop_callback=None, colspan=1, rowspan=1, color='white'):
        """Method to make one frame of the grid at the position given"""        
        frame = Frame(root, relief=RAISED, borderwidth=1.25, bg=color, highlightcolor='blue')
        # place in the position we want and make it fill the space (sticky in all directions)
        frame.grid(column=col, row=row, columnspan=colspan, rowspan=rowspan, sticky=NSEW)
        # make it stretchy if the window is resized
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # set a title for the cell
        label=Label(frame, text=title, font=self.bold16, bg='white')
        label.grid(row=0, column=0, columnspan=2, sticky=N, pady=20)

        # If we have the ability to start and stop the sensor measurement, add those buttons
        # Note 9-3: might want to add a flag in each sensor to disable querying while off, just to stop quite as much serial communication. 
            # But it also might not matter if sending the "query" command while the sensor is off doesn't hurt anything
        if start_callback is not None:
            start_button = Button(frame, text="Start Measurement", command=start_callback, state=DISABLED)
            start_button.grid(row=1, column=0, sticky=W, padx=10)
            self.buttons_to_enable_after_init.append(start_button)
        if stop_callback is not None:
            stop_button = Button(frame, text="Stop Measurement", command=stop_callback, state=DISABLED)
            stop_button.grid(row=1, column=1, sticky=E, padx=10)
            self.buttons_to_enable_after_init.append(stop_button)

        return frame
    
    def _find_status_grid_dims(self):
        """Method to determine the number of rows and columns we need in our grid
        
            Returns - num_rows (int), num_cols (int)"""

        num_cols = 2   # might make this dynamic later
        num_rows = len(self.sensor_names) / num_cols
        # If the last number of the fraction is a 5, add 0.1. This is necessary because Python defaults to 
        # "bankers rounding" (rounds 2.5 down to 2, for example) so would otherwise give us too few rows
        if str(num_rows).split('.')[-1] == '5':
            num_rows += 0.1
        num_rows = round(num_rows)

        return num_rows, num_cols
    
    def _init_status_grid(self, root:Frame):
        """Makes a grid of all the sensors. Currently a placeholder for anything we 
        want to display about the instruments, like adding control or their status"""

        print(self.button_callback_dict)
        
        num_rows, num_cols = self._find_status_grid_dims()
        # Make and save all the frames
        self.sensor_status_frames = {}

        # Make a list of all buttons that are initially disabled, but should be enabled after sensors have been initialized
        self.buttons_to_enable_after_init = [] 

        # Title row
        title_frame = self._make_status_grid_title(root, num_cols)
        
        self.sensor_status_frames.update({"All": title_frame})
        

        # All the other rows/cols
        i = 0
        try:
            for row in range(1,num_rows+1):
                for col in range(num_cols):
                    # Grab the sensor name
                    sensor_name = self.sensor_names[i]
                    
                    # Grab the callbacks we're assigning to the buttons for each sensor
                    callback_dict = self.button_callback_dict[sensor_name]
                    # If there's more going on in the "start" category, deal with that later
                    if type(callback_dict["start"]) == dict:
                        start_callback = None
                        stop_callback = None
                    # Otherwise pull out the start and stop callbacks
                    else:
                        start_callback = callback_dict["start"]
                        stop_callback = callback_dict["stop"]

                    # Make the cell for each sensor
                    frame = self._make_status_grid_cell(root, 
                                                        title=sensor_name, 
                                                        start_callback=start_callback, 
                                                        stop_callback=stop_callback, 
                                                        col=col, 
                                                        row=row)

                    self.sensor_status_frames.update({sensor_name: frame})

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

    def _on_mousewheel(self, event):
        """Method that scrolls the widget that currently has focus, assuming that widget has this callback bound to it"""
        scroll_speed = int(event.delta/120)
        try:
            widget = self.root.focus_get()
            widget.yview_scroll(-1*scroll_speed, "units")
        except Exception as e:
            print(f"Exception in mousewheel callback: {e}")

    def _on_sensor_init(self):
        for button in self.buttons_to_enable_after_init:
            button["state"] = NORMAL

        try:
            self.button_callback_dict["All Sensors"]["start"]() # <- Oh that looks cursed. This calls the method that lives in the dictionary
        except KeyError as e:
            print(f"No callback found to initialize all sensors. Probably not run from the executor script: Key Error {e}, _on_sensor_init")
    
    def _on_sensor_shutdown(self):
        for button in self.buttons_to_enable_after_init:
            button["state"] = DISABLED

        try:
            self.button_callback_dict["All Sensors"]["stop"]() # Yep, that again.
        except KeyError as e:
            print(f"No callback found to shutdown all sensors. Probably not run from the executor script: Key Error {e}, _on_sensor_shutdown")
    
    def _on_start_data(self):
        try:
            self.button_callback_dict["Data Collection"]["start"]()
        except KeyError as e:
            print(f"No callback found to start data collection. Probably not run from the executor script: Key Error {e}, _on_start_data")

    def _on_stop_data(self):
        try:
            self.button_callback_dict["Data Collection"]["stop"]()
        except KeyError as e:
            print(f"No callback found to stop data collection. Probably not run from the executor script: Key Error {e}, _on_stop_data")

    def run_cont(self):
        self.root.mainloop()
        self.root.destroy()

    def run(self, delay=0):
        # self.root.update_idletasks()
        self.root.update()
        # time.sleep(delay)

    ##  --------------------- HELPER FUNCTIONS  --------------------- ##


if __name__ == "__main__":
    # Read the sensor data config file in order to grab the sensor names
    with open("config/sensor_data.yaml", 'r') as stream:
        big_data_dict = yaml.safe_load(stream)
    sensor_names = big_data_dict.keys()

    # Read in an instance of the sensor class to grab the callback methods
    from main_pipeline.sensor import Sensor
    sensor = Sensor()

    # Initialize an empty dictionary to hold the methods we're going to use as button callbacks. Sometimes
    # these don't exist (e.g the Picarro doesn't have start/stop, only query), so initialize them to None
    button_dict = {}
    for name in sensor_names:
        button_dict.update({name:{"start":None, "stop":None}})
    # Add the start/stop measurement methods for the Abakus and the Laser Distance Sensor
    button_dict["Abakus Particle Counter"]["start"] = sensor.abakus.start_measurement
    button_dict["Abakus Particle Counter"]["stop"] = sensor.abakus.stop_measurement
    button_dict["Laser Distance Sensor"]["start"] = sensor.laser.start_laser
    button_dict["Laser Distance Sensor"]["stop"] = sensor.laser.stop_laser
    
    app = GUI(button_callback_dict=button_dict)

    while True:
        app.run()