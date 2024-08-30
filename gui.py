import numpy as np
import time
import pandas as pd
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

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
    """This is the Graphical User Interface, or GUI! It sets up the user interface for the main pipeline.  
        I've tried to make it as modular as possible, so adding additional sensors in the future won't be as much of a pain."""
    def __init__(self, start_callbacks=None, stop_callbacks=None):
        """Initializes everything"""
        ##  --------------------- SIZE & FORMATTING --------------------- ##
        # Make the window and set some size parameters
        self.root = tk.Tk()
        self.root.title("Sample MGR GUI")
        self.root.geometry('1400x1000')
        
        self.grid_width = 150 # px? computer screen units?
        self.grid_height = 50

        # Make some default fonts
        self.bold16 = Font(self.root, family="Helvetica", size=16, weight=BOLD)

        ##  --------------------- INSTRUMENTS & DATA BUFFER MANAGEMENT --------------------- ##
        # Read in the sensor data config file to initialize the data buffer. 
        # Creates an empty dictionary with keys to assign timestamps and data readings to each sensor
        with open("config/sensor_data.yaml", 'r') as stream:
            self.big_data_dict = yaml.safe_load(stream)

        # Grab the names of the sensors from the dictionary
        self.sensor_names = list(self.big_data_dict.keys())

        # initialize dummy data buffers - will eventually delete this, currently for testing
        self.index = 0
        self.x_dummy = []
        self.y_dummy = []

        ## --------------------- GUI LAYOUT --------------------- ##
        # Set up the data grid that will eventually contain sensor status / control, fow now it's empty
        status_grid_frame = Frame(self.root)
        self._init_status_grid_loop(status_grid_frame, callbacks=None)

        # Set up the notebook for data streaming/live plotting
        data_streaming_frame = Frame(self.root, bg="purple")
        self._init_data_streaming_notebook(data_streaming_frame)
        self._init_data_streaming_figs()
        self._init_data_streaming_canvases()
        self._init_data_streaming_animations(animation_delay=1000) #1s of delay in between drawing frames, adjust later
        
        # make some buttons! One toggles the other on/off, example of how to disable buttons and do callbacks with arguments
        b1 = self.pack_button(data_streaming_frame, callback=None, loc='bottom')
        b2 = self.pack_button(data_streaming_frame, callback=lambda: self.toggle_button(b1), loc='bottom', text="I toggle the other button")
                
        # add a sizegrip to the bottom
        sizegrip = Sizegrip(self.root)
        sizegrip.pack(side="bottom", expand=False, fill=BOTH, anchor=SE)

        # pack the frames
        status_grid_frame.pack(side="left", expand=True, fill=BOTH)
        data_streaming_frame.pack(side="right", expand=True, fill=BOTH)
        
    ## --------------------- LAYOUT --------------------- ##
    
    def pack_button(self, root, callback, loc:str="right", text="I'm a button :]"):
        """General method that creates and packs a button inside the given root"""
        button = Button(root, text=text, command=callback)
        button.pack(side=loc)
        return button
  
    ## --------------------- DATA STREAMING DISPLAY --------------------- ##

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
            window.grid(column=0, row=0)
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
            fig = plt.figure(name, figsize=(10,4*num_subplots))
            self.data_streaming_figs.update({name:fig})
            # Add the desired number of subplots to each figure
            for i in range(0, num_subplots):
                fig.add_subplot(num_subplots,1,i+1)

    def _one_canvas(self, f, root):
        """General method to set up a canvas in a given root. I'm eventually using each canvas
        to hold a matplotlib figure for live plotting
        
        Args - f (matplotlib figure), root (tkinter object)"""
        canvas = FigureCanvasTkAgg(f, root)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0)

    def _init_data_streaming_canvases(self):
        """Sets up a tkinter canvas for each sensor in its own tkinter frame (stored in self.data_streaming_windows).
        It might not look like anything is getting saved here, but Tkinter handles parent/child relationships internally,
        so the canvases exist wherever Tkinter keeps the frames"""
        for name in self.sensor_names:
            # Grab the appropriate matplotlib figure and root window
            fig = self.data_streaming_figs[name]
            window = self.data_streaming_windows[name]
            # Make a canvas to hold the figure in the window
            self._one_canvas(fig, window)

    def _init_data_streaming_animations(self, animation_delay=1000):
        """Initializes a matplotlib FuncAnimation for each sensor and stores it in a dictionary.
        
            Args - animation_delay (int, number of ms to delay between live plot updates)
            Updates - self.streaming_anis (dict, holds the FuncAnimations)"""
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
   
    def _make_status_grid_cell(self, root, col, row, colspan=1, rowspan=1, color='white'):
        """Method to make one frame of the grid at the position given"""        
        frame = Frame(root, relief='ridge', borderwidth=2.5, bg=color, highlightcolor='blue')
        # place in the position we want and make it fill the space (sticky)
        frame.grid(column=col, row=row, columnspan=colspan, rowspan=rowspan, sticky='nsew')
        # make it stretchy if the window is resized
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        return frame 
    
    def _find_status_grid_dims(self):
        """Method to determine the number of rows and columns we need in our grid
        
            Returns - num_rows (int), num_cols (int)"""

        num_cols = 2   # might make this dynamic later
        num_rows = len(self.sensor_names) / num_cols
        # If the last number of the fraction is a 5, add 0.1. This prevents Python from doing its usual 
        # 'bankers rounding" (rounding 2.5 to 2, for example)
        if str(num_rows).split('.')[-1] == '5':
            num_rows += 0.1
        num_rows = round(num_rows)

        return num_rows, num_cols
    
    def _init_status_grid_loop(self, root:Frame, callbacks):
        """Makes a grid of all the sensors. Currently a placeholder for anything we 
        want to display about the instruments, like adding control or their status"""
        
        num_rows, num_cols = self._find_status_grid_dims()
        # Make and save all the frames
        self.sensor_status_frames = {}
        # Title row
        title_frame = self._make_status_grid_cell(root, col=0, row=0, colspan=num_cols)
        label=Label(title_frame, text="Start All Data Collection", font=self.bold16)
        label.grid(row=0, column=0)
        self.sensor_status_frames.update({"All": title_frame})
        # All the other rows/cols
        i = 0
        try:
            for row in range(1,num_rows+1):
                for col in range(num_cols):
                    frame = self._make_status_grid_cell(root, col=col, row=row)
                    label = Label(frame, text=self.sensor_names[i], justify='center', font=self.bold16)
                    label.grid(row=0, column=0)
                    # mayne add a button here? some status text?
                    self.sensor_status_frames.update({self.sensor_names[i]: frame})
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


if __name__ == "__main__":
    
    app = GUI()

    while True:
        app.run()