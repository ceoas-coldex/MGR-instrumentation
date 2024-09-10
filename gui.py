import numpy as np
import time
from collections import deque
import yaml
import pandas as pd
import csv
import os

import concurrent.futures

from functools import partial

import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter.ttk import Notebook
from tkinter.font import Font, BOLD

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from blit import BlitManager

class GUI():
    """This is the Graphical User Interface, or GUI! It sets up the user interface for the main pipeline.  
        I've tried to make it as modular as possible, so adding additional sensors in the future won't be as much of a pain."""
    def __init__(self, button_callback_dict):
        """Initializes everything"""
        ##  --------------------- SIZE & FORMATTING --------------------- ##
        # Make the window and set some size parameters
        self.root = tk.Tk()
        self.root.title("MGR GUI")
        self.width = 2200
        # self.height = 1000
        self.height = 1200

        # Make the window fullscreen and locked to the desktop size
        # self.root.attributes('-fullscreen', True) # no toolbar / close button
        self.root.overrideredirect(True) # can't close the window
        self.root.state('zoomed') # fullscreen
        self.root.resizable(False, False) # unable to be resized

        # self.root.geometry(f"{self.width}x{self.height}")

        self.grid_width = 100 # px? computer screen units?
        self.grid_height = 50

        # Make some default colors
        self.button_blue = "#71b5cc"
        self.light_blue = "#579cba"
        self.dark_blue = "#083054"
        self.root.configure(bg=self.light_blue)

        # Make some default fonts
        self.bold20 = Font(self.root, family="Helvetica", size=20, weight=BOLD)
        self.bold16 = Font(self.root, family="Helvetica", size=16, weight=BOLD)
        self.norm16 = Font(self.root, family="Helvetica", size=16)
        self.bold12 = Font(self.root, family="Helvetica", size=12, weight=BOLD)

        # Set some styles
        s = ttk.Style()
        s.configure('TNotebook.Tab', font=self.bold12, padding=[10, 5])
        s.configure('TNotebook', background=self.light_blue)
        s.layout("TNotebook", []) # get rid of the notebook border

        ##  --------------------- INSTRUMENTS & DATA MANAGEMENT --------------------- ##
        self.data_dir = "data"
        self._init_data_saving()

        max_buffer_length = 500 # How long we let the buffers get, helps with memory
        self._init_data_buffer(max_buffer_length)
        self.default_plot_length = 60 # Length of time (in sec) we plot before you have to scroll back to see it

        ## --------------------- GUI LAYOUT --------------------- ##
        # Set up the grid that contains sensor status / control
        status_grid_frame = Frame(self.root, bg='white')
        self.button_callback_dict = button_callback_dict
        self._init_sensor_status_dict() 
        self._init_sensor_grid(status_grid_frame)

        # Set up the notebook for data streaming/live plotting
        data_streaming_frame = Frame(self.root, bg=self.light_blue)
        self._init_data_streaming_notebook(data_streaming_frame)
        self._init_data_streaming_figs()
        self._init_data_streaming_canvases()
        plt.ion() # Now that we've created the figures, turn on interactive matplotlib plotting

        # Set up a frame for data logging
        logging_frame = Frame(self.root, bg=self.dark_blue)
        self._init_logging_panel(logging_frame)

        # pack the frames
        logging_frame.pack(side="right", expand=True, fill=BOTH, padx=5)
        status_grid_frame.pack(side="left", expand=True, fill=BOTH, padx=5)
        data_streaming_frame.pack(side="right", expand=True, fill=BOTH)
  
    ## --------------------- DATA MANAGEMENT --------------------- ##

    def _config_sensor_data(self):
        """Method to read in and save the sensor_data configuration yaml file"""
        # Read in the sensor data config file to initialize the data buffer. 
        # Creates an empty dictionary with keys to assign timestamps and data readings to each sensor
        with open("config/sensor_data.yaml", 'r') as stream:
            self.big_data_dict = yaml.safe_load(stream)

    def _config_logging_notes(self):
        """Method to read in and save the logging/notes configuration yaml file"""
        # Read in the logging config file to initialize the note parameters. 
        # Creates an empty dictionary with keys to assign timestamps and data readings to each sensor
        with open("config/logging_data.yaml", 'r') as stream:
            self.notes_dict = yaml.safe_load(stream)

    def _init_csv_file(self, filepath, to_write):
        # Check if we can read the file
        try:
            with open(filepath, 'r'):
                pass
        # If the file doesn't exist, create it and write in whatever we've passed as row titles
        except FileNotFoundError:
            with open(filepath, 'x') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', lineterminator='\r')
                writer.writerow(to_write)
    
    def _init_data_saving(self):
        """Method to check if today's data files have been created, and if not, creates them
        
        Should maybe live in executor?"""
        # Grab the current time in YYYY-MM-DD HH:MM:SS format
        datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        # Grab only the date part of the time
        day = datetime.split(" ")[0]
        # Create filepaths in the data saving directory with the date (may change to per hour depending on size)
        self.main_filepath = f"{self.data_dir}\\{day}.csv"
        self.notes_filepath = f"{self.data_dir}\\{day}_notes.csv"

        # Read in the configuration files for the sensor and logging data
        self._config_sensor_data()
        self._config_logging_notes()
        # Initialize csv files for data saving, pass in the dictionary keys as row titles
        self._init_csv_file(self.main_filepath, self.big_data_dict.keys()) # This one will need to be changed - multiple readings per sensors
        
        notes_titles = list(self.notes_dict.keys())
        notes_titles.insert(0, "Internal Timestamp (epoch)")
        self._init_csv_file(self.notes_filepath, notes_titles)
    
    ## --------------------- DATA STREAMING DISPLAY --------------------- ##

    def _init_data_buffer(self, max_buffer_length):
        # Comb through the keys, set the timestamp to the current time and the data to zero
        sensor_names = self.big_data_dict.keys()
        for name in sensor_names:
            self.big_data_dict[name]["Time (epoch)"] = deque([time.time()], maxlen=max_buffer_length)
            channels = self.big_data_dict[name]["Data"].keys()
            for channel in channels:
                self.big_data_dict[name]["Data"][channel] = deque([0.0], maxlen=max_buffer_length)

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
            # Create a figure and size it based on the number of channels
            fig = plt.figure(name, figsize=(10.5,4*num_subplots))
            
            # Create a subplot for each channel, and label the axes
            self.data_streaming_figs.update({name:fig})
            _, _, labels = self.get_data(name)
            for i in range(0, num_subplots):
                ax = fig.add_subplot(num_subplots,1,i+1)
                ax.set_xlabel("Time (epoch)")
                ax.set_ylabel(labels[i])

            # A little cheesy - futz with the whitespace by adjusting the position of the top edge of the subplots 
            # (as a fraction of the figure height) based on how many subplots we have. For 1 subplot put it at 90% of the figure height, 
            # for 4 subplots put it at 97%, and interpolate between the two otherwise
            plt.subplots_adjust(top=np.interp(num_subplots, [1,4], [0.9,0.97]))

    def _one_canvas(self, f, root, vbar:Scrollbar):
        """General method to set up a canvas in a given root. I'm eventually using each canvas
        to hold a matplotlib figure for live plotting
        
        Args - f (matplotlib figure), root (tkinter object), vbar (tkinter Scrollbar), 
        num_subplots(int, how many subplots we want on this canvas. Used to set the size of the scroll region)"""
        # Initialize and render a matplotlib embedded canvas
        canvas = FigureCanvasTkAgg(f, root)
        canvas.draw()

        num_subplots = len(f.get_axes())
        max_scroll = num_subplots*self.height
        scroll_region = np.interp(num_subplots, [1,4], [max_scroll/2.5, max_scroll/1.8])
        canvas.get_tk_widget().config(bg='white', # set the background color 
                                      scrollregion=(0,0,0,scroll_region), # set the size of the scroll region in screen units
                                      yscrollcommand=vbar.set, # link the scrollbar to the canvas
                                      )
        canvas.get_tk_widget().grid(row=1, column=0)

        # Set the scrollbar command and position
        vbar.config(command=canvas.get_tk_widget().yview)
        vbar.grid(row=1, column=1, sticky=N+S)
        # Bind the scrollbar to the mousewheel
        canvas.get_tk_widget().bind("<MouseWheel>", self._on_mousewheel)

        toolbar = NavigationToolbar2Tk(canvas, root, pack_toolbar=False)
        toolbar.grid(row=0, column=0, pady=(10,0))

        root.config(bg='white')

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
            self._one_canvas(fig, window, vbar)
        
    def _update_plots(self):
        ## Do some loops so we can simplify the actual plotting loop as much as possible (& make all plots update
        # near simultaneously)    
        # 1. Loop through the sensors and grab both data from their updated buffers and their corresponding matplotlib figure
        xdata = []
        ydata = []
        axes = []
        figs = []
        for name in self.sensor_names:
            fig = self.data_streaming_figs[name]
            figs.append(fig)
            axs = fig.get_axes()
            x, ys, _ = self.get_data(name)
            # 2. Loop through the number of data channels present for this sensor (i.e how many deques are present in ys)
            for i, y in enumerate(ys):
                xdata.append(x)
                ydata.append(y)
                axes.append(axs[i])
                # 3. Loop through and remove the "artists" in the current figure axis - this clears the axis without having
                # to call axis.clear(), so preserves axis labels and, more importantly for plot zooming, axis limits and bounds
                for artist in axs[i].lines:
                    artist.remove()

        # Finally, loop through all the axes and plot the updated data
        for i, ax in enumerate(axes):
            ax.plot(xdata[i], ydata[i], '.--')

            # Set the xbound to either 
            ax.set_xbound(lower = max(ax.get_xbound()[0], xdata[i][-1]-self.default_plot_length))
    
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

    ## --------------------- STATUS GRID --------------------- ##
    
    def _make_status_grid_cell(self, root, title, col, row, button_callbacks, button_names, button_states, font, colspan=1, rowspan=1, color='white'):
        """Method to make one frame of the grid at the position given with the buttons given

            Args - 
                - root (tkinter object), 
                - title (str, cell title), 
                - col (int, position in root grid), row (int, position in root grid),
                - button_callbacks (list, methods to give the buttons, can be empty), 
                - button_names (list of str, names of the buttons),
                - button_states (list of str, ACTIVE or DISABLED), 
                - colspan (int, column span in root grid), rowspan (int, row span in root grid)
        """  
        # Make a frame at the position we want and make it fill the space (sticky in all directions)
        frame = Frame(root, relief=RAISED, borderwidth=1.25, bg=color, highlightcolor='blue')
        frame.grid(column=col, row=row, columnspan=colspan, rowspan=rowspan, sticky=NSEW)
        # Make it stretchy if the window is resized
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # If we have more than 4 buttons to put in this cell, split them up into 2 columns and determine how many rows we need
        if len(button_names) >= 4:
            button_rows, button_cols = self._find_grid_dims(num_elements = len(button_names), num_cols=2) 
            title_colspan = 2
        # Otherwise, keep everything in 1 column
        else:
            button_rows, button_cols = self._find_grid_dims(num_elements = len(button_names), num_cols=1) 
            title_colspan = 1

        # Set a title for the cell
        label=Label(frame, text=title, font=font, bg='white')
        label.grid(row=0, column=0, columnspan=title_colspan, sticky=N, pady=20)
        
        # Make the status readout and sensor control buttons
        self._make_status_readout(frame, 1, title, colspan=title_colspan)
        buttons = self._make_sensor_buttons(frame, title, 2, button_rows, button_cols, button_names, button_callbacks, button_states)
        
        # Note 9-3: might want to add a flag in each sensor to disable querying while off, just to stop quite as much serial communication. 
        # But it also might not matter if sending the "query" command while the sensor is off doesn't hurt anything
        
        return buttons
    
    def _make_sensor_buttons(self, root, sensor_name, row:int, button_rows:int, button_cols:int, button_names, button_callbacks, button_states):
        """Method to make buttons for the status grid cells
        
        Args - 
            - root: tkinter object
            - sensor_name: str, name of the sensor. Should match a key in self.sensor_names
            - row: int, row of the root grid to start the buttons on
            - button_rows: int, how many rows of buttons
            - button_cols: int, how many columns of buttons
            - button_names: list of str, what text we want printed on the buttons
            - button_callbacks: list of methods, callbacks to be assigned to the buttons
            - button_states: list of str, initial status of the button (ACTIVE or DISABLED)
        """
        
        # Loop through the determined number of rows and columns, creating buttons and assigning them callbacks accordingly
        i = 0
        buttons = []
        try:
            for row in range(row, button_rows+row):
                for col in range(button_cols):
                    # The callbacks have been passed in from executor.py, and directly control the sensors. Since I also want to log
                    # the sensor status when the buttons are pushed, wrap up the callback in a functools partial() to give it a little
                    # more functionality. Check out self._sensor_button_callback for more details
                    callback = partial(self._sensor_button_callback, sensor_name, button_callbacks[i])
                    # Create and place the button
                    button = Button(root, text=button_names[i], command=callback, font=self.bold16, state=button_states[i])
                    button.grid(row=row, column=col, sticky=N, padx=10, pady=10)
                    # Grab a hold of the button just in case we want to access it later
                    buttons.append(button)
                    i+=1
        except IndexError as e:
            print(f"Exception in building status grid buttons: {e}. Your number of buttons probably doesn't divide evenly by 2, that's fine")

        return buttons
    
    def _make_status_readout(self, root, row, name, col=0, colspan=1):
        """Method to build the sensor status portion of the grid
        
            Args - 
                - root: tkinter object
                - row: int, row of the root grid to position the status readout
                - name: str, which grid cell (and therefore sensor) this status reading corresponds to
                - col: int, column of the root grid to position the sensor readout
                - colspan: int, how many columns of the root grid it should take up
        """
        # We only want to report the status of sensors, not any other grid (like the title), so check if the name
        # we've been given is in our list of sensor names. If it's not, exit
        if name not in self.sensor_names:
            return
        # Make and position a frame at the given column and row - holds the rest of the tkinter objects we're making here
        frame = Frame(root, bg="white")
        frame.grid(column=col, row=row, columnspan=colspan, pady=10, padx=10)
        # Make and position some text
        Label(frame, text="Status:", font=self.bold16, bg="white").grid(column=0, row=0, ipadx=5, ipady=5)
        # Make and position some more text, but hold onto this one - we want to be able to change its color later to 
        # represent sensor status
        status_text = Label(frame, font=self.bold16, bg="white")
        status_text.grid(column=1, row=0, ipadx=5, ipady=5)
        self.sensor_status_colors[name] = status_text

    def _init_sensor_status_dict(self):
        """Method to initialize an empty sensor status dictionary based on the sensors in self.sensor_names,
        will be filled in when a sensor button callback is triggered or self._update_sensor_status is called"""
        self.sensor_status_dict = {}
        self.sensor_status_colors = {}
        for name in self.sensor_names:
            self.sensor_status_dict.update({name:0})
            self.sensor_status_colors.update({name:None})
    
    def _init_sensor_grid(self, root:Frame):
        """Makes a grid of all the sensors, with buttons to initialize/shutdown sensors, display sensor status, 
        and start/stop data collection."""
        # Grab the number of rows we should have in our grid given the number of sensors in self.sensor_names 
        # (this is a little unnecessary currently, since I decided one column looked best)
        num_rows, num_cols = self._find_grid_dims(num_elements=len(self.sensor_names), num_cols=1)
        # Make the title row
        title_buttons = self._make_status_grid_cell(root, title="Sensor Status & Control", col=0, row=0, colspan=num_cols, font=self.bold20,
                                                    button_names=["Initialize All Sensors", "Shutdown All Sensors", "Start Data Collection", "Stop Data Collection"],
                                                    button_callbacks=[self._on_sensor_init, self._on_sensor_shutdown, self._on_start_data, self._on_stop_data],
                                                    button_states=[ACTIVE, ACTIVE, DISABLED, DISABLED],
                                                   )
        # Make a list of all buttons that are initially disabled, but should be enabled after sensors have been initialized
        self.buttons_to_enable_after_init = [button for button in title_buttons[2:]]
        # And vice versa with shutdown
        self.buttons_to_disable_after_shutdown = [button for button in title_buttons[2:]]
        # Make all the other rows/cols for the sensors
        i = 0
        try:
            for row in range(2, num_rows+2):
                for col in range(num_cols):
                    # Grab the sensor name
                    sensor_name = self.sensor_names[i]
                    # Grab the button names and callbacks for each sensor (self.button_callback_dict was passed into this GUI when
                    # the object was instantiated, and holds methods for initializing and stopping the sensors)
                    callback_dict = self.button_callback_dict[sensor_name]
                    button_names = list(callback_dict.keys())
                    button_callbacks = list(callback_dict.values())
                    # Make the cell (makes buttons and status indicator)
                    buttons = self._make_status_grid_cell(root, col=col, row=row,
                                                          colspan=num_cols,
                                                          title=sensor_name,
                                                          font=self.bold16,
                                                          button_names=button_names,
                                                          button_callbacks=button_callbacks,
                                                          button_states=[ACTIVE]*len(button_names),
                                                        )
                    i += 1
            # Now that we've made a status grid for each sensor, update them
            self._update_sensor_status()
        except IndexError as e:
            print(f"Exception in building status grid loop: {e}. Probably your sensors don't divide evenly by {num_cols}, that's fine")

        # Make the grid stretchy if the window is resized, with all the columns and rows stretching by the same weight
        root.columnconfigure(np.arange(num_cols).tolist(), weight=1, minsize=self.grid_width)
        # root.rowconfigure(np.arange(1,num_rows+1).tolist(), weight=1, minsize=self.grid_height) # "+1" for the title row
 
    ## --------------------- LOGGING FRAME --------------------- ##
    def _init_logging_panel(self, root):

        Label(root, text="Notes & Logs", font=self.bold20, bg='white', width=15).grid(column=0, row=0, columnspan=2, sticky=N, pady=10)

        entry_text = self.notes_dict.keys()
        self.logging_entries = []

        for i, text in enumerate(entry_text):
            try:
                Label(root, text=f"{text}:", font=self.bold16, bg='white', width=19, justify=LEFT, anchor=W).grid(column=0, row=i+1, sticky=N+W, padx=(25,5), pady=2.5, ipady=2.5)
                height = self.notes_dict[text]["entry height"]
                entry = Text(root, font=self.norm16, height=height, width=15)
                entry.grid(column=1, row=i+1, sticky=N+W, padx=(0,15), pady=2.5, ipady=2.5)
                self.logging_entries.append(entry)
            except KeyError:
                pass

        Button(root, text="LOG", font=self.bold16, bg=self.button_blue, width=15, command=self._on_log).grid(column=0, row=i+3, columnspan=2, pady=30)
        
        # Make the grid stretchy if the window is resized, with all the columns and rows stretching by the same weight
        root.columnconfigure(np.arange(2).tolist(), weight=1, minsize=self.grid_width)


    ## --------------------- CALLBACKS --------------------- ##

    def _on_mousewheel(self, event):
        """Method that scrolls the widget that currently has focus, assuming that widget has this callback bound to it"""
        scroll_speed = int(event.delta/120)
        try:
            widget = self.root.focus_get()
            widget.yview_scroll(-1*scroll_speed, "units")
        except Exception as e:
            print(f"Exception in mousewheel callback: {e}")

    def _on_sensor_init(self):
        """Callback for the 'Initialize Sensors' button. Enables the other buttons and tries to call the *sensor init* method
        that was passed into self.button_callback_dict when this class was instantiated. If that method doesn't exist, it lets you know."""
        # Enable other buttons
        for button in self.buttons_to_enable_after_init:
            self.toggle_button(button)
        # Try to call the method that's the value of the "All Sensors":"Initialize All Sensors" key of the dictionary
        try:
            self.sensor_status_dict = self.button_callback_dict["All Sensors"]["Initialize All Sensors"]() # <- Oh that looks cursed. This calls the method that lives in the dictionary
        # If that key or method doesn't exist, we likely haven't run this script from executor.py. If we have, check executor._set_gui_buttons()
        except KeyError as e:
            print(f"Key Error {e}, _on_sensor_init")
        except TypeError as e:
            print(f"No callback found to start data collection. Probably not run from the executor script.")

        self._update_sensor_status()

        print(self.sensor_status_dict)
    
    def _on_sensor_shutdown(self):
        """Callback for the 'Shutdown Sensors' button. Disables the other buttons and tries to call the *sensor shutdown* method
        that was passed into self.button_callback_dict when this class was instantiated. If that method doesn't exist, it lets you know."""
        # Disable other buttons
        for button in self.buttons_to_disable_after_shutdown:
            self.toggle_button(button)
        # Try to call the method that's the value of the "All Sensors":"Shutdown All Sensors" key of the dictionary
        try:
            self.sensor_status_dict = self.button_callback_dict["All Sensors"]["Shutdown All Sensors"]() # Yep, that again.
        # If that key or method doesn't exist, we likely haven't run this script from executor.py. If we have, check executor._set_gui_buttons()
        except KeyError as e:
            print(f"Key Error {e}, _on_sensor_shutdown")
        except TypeError as e:
            print(f"No callback found to start data collection. Probably not run from the executor script.")

        self._update_sensor_status()
    
    def _on_start_data(self):
        """Callback for the 'Start Data Collection' button. Tries to call the *start data collection* method
        that was passed into self.button_callback_dict when this class was instantiated. If that method doesn't exist, it lets you know."""
        # Try to call the method that's the value of the "Data Collection":"Start Data Collection" key of the dictionary
        try:
            self.button_callback_dict["Data Collection"]["Start Data Collection"]()
        # If that key or method doesn't exist, we likely haven't run this script from executor.py. If we have, check executor._set_gui_buttons()
        except KeyError as e:
            print(f"Key Error {e}, _on_start_data")
        except TypeError as e:
            print(f"No callback found to start data collection. Probably not run from the executor script.")

    def _on_stop_data(self):
        """Callback for the 'Stop Data Collection' button. Tries to call the *stop data collection* method
        that was passed into self.button_callback_dict when this class was instantiated. If that method doesn't exist, it lets you know."""
        # Try to call the method that's the value of the "Data Collection":"Stop Data Collection" key of the dictionary
        try:
            self.button_callback_dict["Data Collection"]["Stop Data Collection"]()
        # If that key or method doesn't exist, we likely haven't run this script from executor.py. If we have, check executor._set_gui_buttons()
        except KeyError as e:
            print(f"Key Error {e}, _on_stop_data")
        except TypeError as e:
            print(f"No callback found to start data collection. Probably not run from the executor script.")

    def _sensor_button_callback(self, button_name, button_command):
        """
        General callback to expand upon the methods we were passed in button_callback_dict when this class was 
        instantiated. It runs the method, then checks to see if it corresponds to a valid sensor. If it does, the 
        method will have returned a status value, so this updates the sensor status accordingly.
        
            Args -
                - button_name (str, should be a key in self.button_callback_dict)
                - button_command (method, should be a value in self.button_callback_dict)
        """
        # Activate the callback. If it's a callback for an individual sensor button (e.g "Start Laser"), the callback will
        # return the status of the sensor. This is either 0 (offline), 1 (online and initialized), 2 (disconnected/simulated hardware)
        status = button_command()
        # We only want to do something with that result if it is actually an individual sensor button, so check for that here
        if button_name in self.sensor_names:
            # Update the dictionary that holds sensor status and refresh the GUI
            self.sensor_status_dict[button_name] = status
            self._update_sensor_status()

    def _on_log(self):
        """Callback for the "log" button (self.init_logging_panel), logs the text entries to a csv"""
        # Loops through the elements in self.logging_entries (tkinter Text objects), reads and clears each element
        timestamp = time.time()
        notes = [timestamp]
        for entry in self.logging_entries:
            # Makes sure we're only working with tkinter Text objects, and also conveniently
            # tells VSCode the type of the list element
            if type(entry) == Text:
                log_val = entry.get('1.0', 'end').strip()
                entry.delete('1.0', 'end')
                notes.append(log_val)

        self._save_data_notes(notes)
    
    ##  --------------------- HELPER FUNCTIONS --------------------- ##

    def toggle_button(self, button: Button):
        """Method that toggles a button between its 'normal' state and its 'disabled' state"""
        if button["state"] == NORMAL:
            button["state"] = DISABLED
        else:
            button["state"] = NORMAL
    
    def _find_grid_dims(self, num_elements, num_cols):
        """Method to determine the number of rows we need in a grid given the number of elements and the number of columns
        
            Returns - num_rows (int), num_cols (int)"""

        num_rows = num_elements / num_cols
        # If the last number of the fraction is a 5, add 0.1. This is necessary because Python defaults to 
        # "bankers rounding" (rounds 2.5 down to 2, for example) so would otherwise give us too few rows
        if str(num_rows).split('.')[-1] == '5':
            num_rows += 0.1
        num_rows = round(num_rows)

        return num_rows, num_cols
    
    def _update_sensor_status(self):
        """Method to update the sensor status upon initialization or shutdown. Uses the values stored in
        self.sensor_status_dict to set the color and text of each sensor status widget."""
        # Loop through the sensors and grab their status from the sensor status dictionary
        for name in self.sensor_names:
            status = self.sensor_status_dict[name]
            # If we're offline / failed initialization
            if status == 0:
                # color = "#D80F0F"
                color = "#D55E00"
                text = "OFFLINE"
            # If we're online / successfully initialized
            elif status == 1:
                color = "#619CD2"
                text = "ONLINE"
            # If we're disconnected / using shadow hardware
            elif status == 2:
                color = "#FFC107"
                text = "SHADOW HARDWARE"
            # If we recieved an erroneous reading, make it obvious
            else:
                color = "purple"
                text = "?????"

            # Update the sensor status accordingly
            label = self.sensor_status_colors[name] # This is a dictionary of tkinter objects
            label["bg"] = color
            label["text"] = text
    
    def _save_sensor_data(self):
        pass

    def _save_data_notes(self, notes):
        """Method to save the logged notes to a csv file"""
        # Check if a file exists at the given path and write the notes
        try:
            with open(self.notes_filepath, 'a') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', lineterminator='\r')
                writer.writerow(notes)
        # If it doesn't, something went wrong with initialization - remake it here
        except FileNotFoundError:
            with open(self.notes_filepath, 'x') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                notes_titles = list(self.notes_dict.keys())
                notes_titles.insert(0, "Internal Timestamp (epoch)")
                writer.writerow(notes_titles) # give it a title
                writer.writerow(notes) # write the notes
    
    ##  --------------------- EXECUTABLES --------------------- ##
    
    def run_cont(self):
        self.root.mainloop()
        self.root.destroy()

    def run(self, delay):
        self._update_plots()
        try:
            self.root.update()
            time.sleep(delay)
            return True
        except:
            return False


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
        button_dict.update({name:{}})

    # Add the start/stop measurement methods for the Abakus and the Laser Distance Sensor
    button_dict["Abakus Particle Counter"] = {"Start Abakus": sensor.abakus.initialize_abakus,
                                              "Stop Abakus": sensor.abakus.stop_measurement}

    button_dict["Laser Distance Sensor"] = {"Start Laser": sensor.laser.initialize_laser,
                                            "Stop Laser": sensor.laser.stop_laser}
    
    button_dict["Flowmeter"] = {"Start SLI2000": sensor.flowmeter_sli2000.initialize_flowmeter,
                                "Start SLS1500": sensor.flowmeter_sls1500.initialize_flowmeter}
    
    # Finally, add a few general elements to the dictionary - one for initializing all sensors (self._init_sensors), 
    # one for starting (self._start_data_collection) and stopping (self._stop_data_collection) data collection 
    # and one for shutting down all sensors (self._clean_sensor_shutdown)
    button_dict.update({"All Sensors":{"Initialize All Sensors":None, "Shutdown All Sensors":None}})
    button_dict.update({"Data Collection":{"Start Data Collection":None, "Stop Data Collection":None}})
    
    app = GUI(button_callback_dict=button_dict)

    running = True
    while running:
        running = app.run(0.1)
