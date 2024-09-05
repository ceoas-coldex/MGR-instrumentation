import numpy as np
import time
from collections import deque
import yaml

from functools import partial

import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter.ttk import Notebook
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
        # self.height = 1000
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

    def _one_canvas(self, f, root, vbar:Scrollbar) -> FigureCanvasTkAgg:
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
            self._one_canvas(fig, window, vbar)

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
            axes[i].plot(xdata, y, '.--')
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
    
    def _make_status_grid_cell(self, root, title, col, row, button_callbacks, button_names, button_states, colspan=1, rowspan=1, color='white'):
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
        label=Label(frame, text=title, font=self.bold16, bg='white')
        label.grid(row=0, column=0, columnspan=title_colspan, sticky=N, pady=20)
        
        self._make_status_readout(frame, 1, title, colspan=title_colspan)
        print(title)
        buttons = self._make_sensor_buttons(frame, title, 2, button_rows, button_cols, button_names, button_callbacks, button_states)
        
        # Note 9-3: might want to add a flag in each sensor to disable querying while off, just to stop quite as much serial communication. 
        # But it also might not matter if sending the "query" command while the sensor is off doesn't hurt anything
        
        return buttons
    
    def create_callback(self, sensor_name, old_callback):
        return lambda: self._sensor_button_callback(sensor_name, old_callback)
    
    def _make_sensor_buttons(self, root, sensor_name, row:int, button_rows:int, button_cols:int, button_names, button_callbacks, button_states):
        # Loop through the determined number of rows and columns, creating buttons and assigning them callbacks accordingly
       
        print(button_callbacks)
        i = 0
        buttons = []
        try:
            for row in range(row, button_rows+row):
                for col in range(button_cols):
                    test = button_callbacks[i]
                    print(test)
                    callback = partial(self._sensor_button_callback, sensor_name, test)
                    button = Button(root, text=button_names[i], command=callback, 
                                    font=self.bold16, state=button_states[i])
                    button.grid(row=row, column=col, sticky=N, padx=10, pady=10)
                    buttons.append(button)
                    i+=1
        except IndexError as e:
            print(f"Exception in building status grid buttons: {e}. Your number of buttons probably doesn't divide evenly by 2, that's fine")

        return buttons
    
    def _update_sensor_status(self):
        """Method to update the sensor status upon initialization or shutdown"""
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

            label = self.sensor_status_colors[name]
            label["bg"] = color
            label["text"] = text
    
    def _make_status_readout(self, root, row, name, col=0, colspan=1):
        try:
            self.sensor_status_dict[name]
        except KeyError:
            return
        
        frame = Frame(root, bg="white")
        frame.grid(column=col, row=row, columnspan=colspan, pady=10, padx=10)

        Label(frame, text="Status:", font=self.bold16, bg="white").grid(column=0, row=0, ipadx=5, ipady=5)

        status_box = Frame(frame)
        status_box.grid(column=1, row=0)

        status_text = Label(status_box, font=self.bold16, bg="white")
        status_text.grid(column=0, row=0, ipadx=5, ipady=5)

        self.sensor_status_colors[name] = status_text

    def _init_status_grid(self, root:Frame):
        """Makes a grid of all the sensors. Currently a placeholder for anything we 
        want to display about the instruments, like adding control or their status"""
        # Initialize an empty sensor status dictionary, will be filled when the sensor initialization callback is triggered
        self.sensor_status_dict = {}
        self.sensor_status_colors = {}
        for name in self.sensor_names:
            self.sensor_status_dict.update({name:0})
            self.sensor_status_colors.update({name:None})
        # Grab the number of rows we should have in our grid given the number of sensors in self.sensor_names 
        # (this is a little unnecessary currently, since I decided one column looked better)
        num_rows, num_cols = self._find_grid_dims(num_elements=len(self.sensor_names), num_cols=1)
            
        # Make the title row
        title_buttons = self._make_status_grid_cell(root, title="Sensor Status & Control", col=0, row=0, colspan=num_cols,
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
                    # Grab the button names and callbacks for each sensor
                    callback_dict = self.button_callback_dict[sensor_name]
                    button_names = list(callback_dict.keys())
                    button_callbacks = list(callback_dict.values())
                    # Make the cell (makes buttons and status indicator)
                    buttons = self._make_status_grid_cell(root, col=col, row=row,
                                                          colspan=num_cols,
                                                          title=sensor_name,
                                                          button_names=button_names,
                                                          button_callbacks=button_callbacks,
                                                          button_states=[ACTIVE]*len(button_names),
                                                        )
                    # Add the buttons to the list of those we enable after sensor initialization
                    for button in buttons:
                        self.buttons_to_enable_after_init.append(button)

                    i += 1
        except IndexError as e:
            print(f"Exception in building status grid loop: {e}. Probably your sensors don't divide evenly by {num_cols}, that's fine")

        # Make the grid stretchy if the window is resized, with all the columns and rows stretching by the same weight
        root.columnconfigure(np.arange(num_cols).tolist(), weight=1, minsize=self.grid_width)
        # root.rowconfigure(np.arange(1,num_rows+1).tolist(), weight=1, minsize=self.grid_height) # "+1" for the title row
 
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
        """Callback for the 'Initialize Sensors' button. Enables the other buttons and tries to call the *sensor init* method
        that was passed into self.button_callback_dict when this class was instantiated. If that method doesn't exist, it lets you know."""
        #
        for button in self.buttons_to_enable_after_init:
            button["state"] = NORMAL
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
            button["state"] = DISABLED
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

    def _sensor_button_callback(self, sensor_name, sensor_command):
        status = sensor_command()
        if sensor_name in self.sensor_names:
            self.sensor_status_dict[sensor_name] = status
            self._update_sensor_status()




    ##  --------------------- HELPER FUNCTIONS --------------------- ##

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
    
    ##  --------------------- EXECUTABLES --------------------- ##
    
    def run_cont(self):
        self.root.mainloop()
        self.root.destroy()

    def run(self):
        self.root.update()


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

    while True:
        app.run()
        time.sleep(0.1)