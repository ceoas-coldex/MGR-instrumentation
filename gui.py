# -------------
# This is the Graphical User Interface (GUI) - true to its name, many graphs and user interfaces going on here!
# I've tried to make it as modular as possible, so adding additional sensors in the future won't be as much of a pain.
# 
# Most of the GUI features - like what sensors we display, what notetaking capabilities we need out of a logging panel,
# -------------

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT  as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import matplotlib.pyplot as plt
import numpy as np
import yaml
import sys
import time
from collections import deque
from functools import partial
import concurrent.futures
import traceback

import logging
from logdecorator import log_on_start , log_on_end , log_on_error
# Set up a logger for this module
logger = logging.getLogger(__name__)
# Set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
logger.setLevel(logging.DEBUG)
# Create a handler that saves logs to the log folder named as the current date
fh = logging.FileHandler(f"logs\\{time.strftime('%Y-%m-%d', time.localtime())}.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
# Create a formatter to specify our log format
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
fh.setFormatter(formatter)

from main_pipeline.sensor import Sensor
from main_pipeline.interpreter import Interpreter
from main_pipeline.writer import Writer
from main_pipeline.bus import Bus


# main window
class ApplicationWindow(QWidget):
    """
    This is the Graphical User Interface, or GUI! It sets up the user interface for the main pipeline.

    Args:
        This class inherets from the general QWidget class in order to make the main window. There are lots of different 
        ways to this inheriting, which make some of the syntax slightly different in between applications. Ah well.
        
    """
    def __init__(self):
        # Initialize the inherited class (QWidget)
        super().__init__()

        # Window settings
        self.setGeometry(50, 50, 2000, 1200) # window size (x-coord, y-coord, width, height)
        self.setWindowTitle("MGR App")

        # Set some fonts
        self.bold16 = QFont("Helvetica", 16)
        self.bold16.setBold(True)
        self.norm16 = QFont("Helvetica", 16)
        self.bold12 = QFont("Helvetica", 12)
        self.bold12.setBold(True)
        self.norm12 = QFont("Helvetica", 12)
        self.norm10 = QFont("Helvetica", 10)

        # Make some default colors
        self.button_blue = "#71b5cc"
        self.light_blue = "#579cba"
        self.dark_blue = "#083054"

        # Initialize the main sense-interpret-save data pipeline
        self.init_data_pipeline()
        
        # Set data buffer parameters
        self.max_buffer_length = 5000 # How long we let the buffers get, helps with memory
        self.default_plot_length = 60 # Length of time (in sec) we plot before you have to scroll back to see it
        self.load_notes_entries()
        self.init_data_buffer()
        
        # Create the three main GUI panels:
        # 1. Left panel: sensor status and control
        left_layout = self.build_control_layout(QGridLayout())
        # 2. Center panel: data streaming
        center_layout = self.build_plotting_layout(QVBoxLayout())
        # 3. Right panel: logging and notetaking
        right_layout = self.build_notes_layout(QVBoxLayout())

        # Wrap these three main panels up into one big layout, and add it to the app window
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(center_layout)
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)
        
        # Create a threadpool for this class, so we can do threading later
        self.threadpool = QThreadPool()
            
        # Initiate two timers that both trigger every X ms:
        timer_update = 500
        # One for updating the plots...
        self.plot_figs_timer = QTimer()
        self.plot_figs_timer.timeout.connect(self.update_plots)
        self.plot_figs_timer.start(timer_update)
        # ...and one for collecting, processing, and saving data
        self.execution_timer = QTimer()
        self.execution_timer.timeout.connect(self.run_data_collection)
        self.execution_timer.start(timer_update)
        
        # Show the window
        self.show()
    
    ## --------------------- SENSOR STATUS & CONTROL --------------------- ## 
       
    def build_control_layout(self, left_layout:QLayout):
        """Method to build the layout for sensor status & control

        Args:
            left_layout (QLayout): The layout we want to store our status & control widgets in
        """
        left_layout.setContentsMargins(0, 20, 0, 0)
        # Grab button information for both the main title array and the individual sensors
        title_button_info, sensor_button_info = self.define_sensor_button_callbacks()
        # Make the title row - has general buttons for initializing sensors and starting data collection
        start_next_row, title_colspan = self.make_title_control_panel(left_layout, title_button_info)
        # Make the individual button rows
        self.make_sensor_control_panel(left_layout, sensor_button_info, starting_row=start_next_row, colspan=title_colspan)
        # Position the panel at the top of the window
        left_layout.setAlignment(QtCore.Qt.AlignTop)

        return left_layout

    def make_title_control_panel(self, parent:QGridLayout, title_button_info:dict, colspan=2):
        """Builds the panel for general sensor control - has buttons to initialize/shutdown sensors and start/stop data collection

        Args:
            parent (QGridLayout): Parent layout
            title_button_info (dict): Dictionary containing key-value pairs of 
                "button name":{"callback:button_callback_function, "enabled":True/False}
            colspan (int, optional): How many columns of buttons. Defaults to 2.

        Returns:
            start_next_row (int): What row of a QGridLayout any further widgets should start on

            **colspan**: *int*: How many columns we've used so far
        """
        # Set the title
        label = QLabel(self)
        label.setText("Sensor Status & Control")
        label.setFont(self.bold16)
        label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        parent.addWidget(label, 0, 0, 1, colspan) # args: widget, row, column, rowspan, columnspan

        # Determine the dimensions of our button grid
        num_rows, num_cols = find_grid_dims(num_elements=len(title_button_info), num_cols=colspan)

        # For all the buttons we want to generate (stored in the title_button_info dict),
        # create, position, and assign a callback for each
        i = 0
        title_button_text = list(title_button_info.keys())
        self.title_buttons = {} # Holding onto the buttons for later
        for row in range(1, num_rows+1): # Adjusting for the QLabel title that we put on row 1
            for col in range(num_cols):
                button_text = title_button_text[i]
                button = QPushButton(self)
                button.setText(button_text)
                button.setFont(self.norm12)
                button.pressed.connect(title_button_info[button_text]["callback"]) # set the button callback
                button.setEnabled(title_button_info[button_text]["enabled"]) # set the button initial state (enabled/disabled)
                parent.addWidget(button, row, col)
                self.title_buttons.update({button_text:button})
                i+=1

        # Add a separation line to the layout after all the buttons
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        parent.addWidget(line, row+1, 0, 1, colspan)

        # We should add any further widgets after that^ line widget, so 2 rows after the last button
        start_next_row = num_rows+2

        return start_next_row, colspan
    
    def make_sensor_control_panel(self, parent:QGridLayout, sensor_buttons:dict, starting_row, colspan):
        """Builds the panel for specific sensor control - has buttons that depend upon sensor functionality

        Args:
            parent (QGridLayout): Parent layout
            sensor_buttons (dict): Dictionary containing key-value pairs of "sensor_name":{button_1_name:button_1_callback, ...}
            starting_row (_type_): What row of the parent layout we should start building from
            colspan (_type_): How many columns are already being used in the parent layout

        Returns:
            start_next_row (int): What row of a QGridLayout we any further widgets should start on
        """
        # Determine how many rows we need for a status & control block per sensor
        num_rows, num_cols = find_grid_dims(num_elements=len(self.sensor_names), num_cols=1)
        # For all the sensors, create control buttons (if applicable) and a status indicator
        i = 0
        self.sensor_status_display = {} # Holding onto the status displays for later
        # We want to place 4 widgets per sensor panel, so we need to be a little funky with the for loop - 
        elements_per_row = 4
        # - we increment by 4 each 'row' of the loop, and manually increment inside the loop
        for row in range(starting_row, (elements_per_row*num_rows)+starting_row, elements_per_row): 
            for col in range(num_cols):
                # Extract the sensor name
                sensor = self.sensor_names[i]
                i+=1
                # First widget we want to place - the sensor title
                title = QLabel(self)
                title.setFont(self.bold12)
                title.setText(sensor)
                title.setAlignment(Qt.AlignHCenter)
                title.setStyleSheet("padding-top:10px")
                parent.addWidget(title, row, col, 1, colspan)
                # Second widget - the status indicator (QLabel that changes color & text upon initialization and shutdown)
                status = QLabel(self)
                status.setText("OFFLINE")
                status.setFont(self.norm12)
                status.setStyleSheet("background-color:#AF5189; margin:10px")
                status.setAlignment(Qt.AlignCenter)
                parent.addWidget(status, row+1, col, 1, colspan)
                self.sensor_status_display.update({sensor:status}) # Hold onto the status display for later
                # Third widget - buttons. Not currently robust to multiple rows of buttons, since we haven't needed that
                try:
                    buttons = sensor_buttons[sensor]
                    c = 0
                    for button in buttons:
                        b = QPushButton(self)
                        b.setText(button)
                        b.setFont(self.norm12)
                        b.pressed.connect(sensor_buttons[sensor][button])
                        parent.addWidget(b, row+2, col+c)
                        c+=1
                except KeyError:
                    print("no command buttons for this sensor")
                # Fourth widget - dividing line
                line = QFrame(self)
                line.setFrameShape(QFrame.HLine)
                parent.addWidget(line, row+3, col, 1, colspan)

        # We should add any further widgets after the last dividing line, so 5 rows after the last 'row' iterator
        start_next_row = (elements_per_row*num_rows)+starting_row + 5

        return start_next_row

    def define_sensor_button_callbacks(self):
        """Method that sets the button callbacks for the sensor status & control panel. **If you're adding a new sensor, you'll
        likely need to add to this method.**

        Returns:
            title_buttons (dict): Dictionary with title button information 
                {"button_name":{"callback":button_callback, "enabled":True/False}}
            
            sensor_buttons (dict): Dictionary with sensor button information {"sensor_name":{"button_name":button_callback}}
        """

        title_buttons = {}
        title_button_names = ["Initialize All Sensors", "Shutdown All Sensors", "Start Data Collection", "Stop Data Collection"]
        title_button_callbacks = [self._on_sensor_init, self._on_sensor_shutdown, self._on_start_data, self._on_stop_data]
        title_button_enabled = [True, True, False, False]
        for name, callback, enabled in zip(title_button_names, title_button_callbacks, title_button_enabled):
            title_buttons.update({name: {"callback":callback, "enabled":enabled}})

        sensor_buttons = {}
        for name in self.sensor_names:
            sensor_buttons.update({name:{}})
        sensor_buttons.update({"Abakus Particle Counter": {"Start Abakus":self.sensor.abakus.initialize_abakus,
                                                           "Stop Abakus":self.sensor.abakus.stop_measurement}})
        sensor_buttons.update({"Laser Distance Sensor":{"Start Laser":self.sensor.laser.initialize_laser,
                                                        "Stop Laser":self.sensor.laser.stop_laser}})
        sensor_buttons.update({"Flowmeter":{"Start SLI2000":self.sensor.flowmeter_sli2000.initialize_flowmeter,
                                            "Start SLS1500":self.sensor.flowmeter_sls1500.initialize_flowmeter}})

        return title_buttons, sensor_buttons
        
    def _on_sensor_init(self):
        """Callback function for the 'Initialize All Sensors' button
        """
        # Start our sensor initialization in a thread so any blocking doesn't cause the GUI to freeze
        worker = Worker(self.sensor.initialize_sensors)
        # When it's done, trigger the _finished_sensor_init function
        worker.signals.result.connect(self._finished_sensor_init)
        self.threadpool.start(worker)

    def _finished_sensor_init(self, sensor_status:dict):
        """Method that gets triggered when that thread^ in _on_sensor_init finishes.

        Args:
            sensor_status (dict): dictionary returned from self.sensor.initialize_sensors
        """
        # Update the sensor status dictionary and the GUI
        self.sensor_status_dict = sensor_status
        self.update_sensor_status()
        # Enable the data collection buttons
        self.title_buttons["Start Data Collection"].setEnabled(True)
        self.title_buttons["Stop Data Collection"].setEnabled(True)
        
    def _on_sensor_shutdown(self):
        """Callback function for the 'Shutdown All Sensors' button
        """
        self.data_collection = False
        # Start our sensor shutdown in a thread so any blocking doesn't cause the GUI to freeze
        worker = Worker(self.sensor.shutdown_sensors)
        # When it's done, trigger the _finished_sensor_shutdown function
        worker.signals.result.connect(self._finished_sensor_shutdown)
        self.threadpool.start(worker)

    def _finished_sensor_shutdown(self, sensor_status:dict):
        """Method that gets triggered when that thread^ in _on_sensor_shutdown finishes.

        Args:
            sensor_status (dict): dictionary returned from self.sensor.shutdown_sensors
        """
        # Update the sensor status dictionary and the GUI
        self.sensor_status_dict = sensor_status
        self.update_sensor_status()
        # Enable the data collection buttons
        self.title_buttons["Start Data Collection"].setEnabled(False)
        self.title_buttons["Stop Data Collection"].setEnabled(False)
    
    def _on_start_data(self):
        """Callback function for the "Start Data Collection" button. Sets the data_collection flag to true
        """
        self.data_collection = True
        
    def _on_stop_data(self):
        """Callback function for the "Stop Data Collection" button. Sets the data_collection flag to false
        """
        self.data_collection = False

    def update_sensor_status(self):
        """Method to update the sensor status upon initialization or shutdown. Uses the values stored in
        self.sensor_status_dict to set the color and text of each sensor status widget."""
        # Loop through the sensors and grab their status from the sensor status dictionary
        for name in self.sensor_names:
            status = self.sensor_status_dict[name]
            # If we're offline
            if status == 0:
                # color = "#D80F0F"
                color = "#AF5189"
                text = "OFFLINE"
            # If we're online / successfully initialized
            elif status == 1:
                color = "#619CD2"
                text = "ONLINE"
            # If we're disconnected / using shadow hardware
            elif status == 2:
                color = "#FFC107"
                text = "SHADOW HARDWARE"
            # IF we failed initialization / there's some other error going on
            elif status == 3:
                color = "#D55E00"
                text = "ERROR"
            # If we recieved an erroneous reading, make it obvious
            else:
                color = "purple"
                text = "?????"

            # Update the sensor status accordingly
            status = self.sensor_status_display[name] # This is a dictionary of QLabels
            status.setText(text)
            status.setStyleSheet(f"background-color:{color}; margin:10px")

    ## --------------------- LOGGING & NOTETAKING --------------------- ##

    def build_notes_layout(self, right_layout:QLayout):
        """Method to build the layout for notetaking.

        Args:
            right_layout (QLayout): Parent layout
        """
        right_layout.setContentsMargins(0, 20, 0, 0)
        # Set the title
        label = QLabel(self)
        label.setText("Notes & Logs")
        label.setFont(self.bold16)
        label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        right_layout.addWidget(label)
        # Initialize an empty dictionary of logging entries with keys that correspond to elements in self.notes_dict
        self.init_logging_entries()
        # For each entry in self.notes_dict, create a line entry
        self.lineedits = []
        for note in self.notes_dict:
            line = QLineEdit(self)
            line.setFont(self.norm12)
            line.setPlaceholderText(note)
            line.setTextMargins(10, 10, 10, 10)
            # When the user has finished editing the line, pass the line object and the title to self._save_notes
            line.editingFinished.connect(partial(self._save_notes, line, note))
            line.setMaximumWidth(700)
            right_layout.addWidget(line, alignment=Qt.AlignTop)

        # Make a button that saves the logged entries to a csv when pressed
        log_button = QPushButton(self)
        log_button.setText("LOG")
        log_button.setFont(self.bold12)
        log_button.pressed.connect(self._log_notes)
        right_layout.addWidget(log_button, alignment=QtCore.Qt.AlignTop)

        # Position the panel at the top of the window
        right_layout.setAlignment(QtCore.Qt.AlignTop)

        return right_layout

    def init_logging_entries(self):
        """Method to build a dictionary to save logged notes
        """
        self.logging_entries = {}
        self.logging_entries.update({"Internal Timestamp (epoch)":""})
        for key in self.notes_dict:
            self.logging_entries.update({key:""})

    def _save_notes(self, line:QLineEdit, note_title:str):
        """Callback function for the QLineEdit entries, holds onto the values entered into the logging panel.

        Args:
            line (QLineEdit): _description_
            note_title (str): _description_
        """
        # Add the logging entry to the appropriate key of the dictionary
        self.logging_entries.update({note_title: line.text()})
        # Hold onto the QLineEdit object so we can modify it later
        self.lineedits.append(line)

    def _log_notes(self):
        """Callback for the 'log' button (self.init_logging_panel), logs the text entries (self.logging_entries) to a csv
        """
        # Update the timestamp and save the notes
        timestamp = time.time()
        self.logging_entries.update({"Timestamp (epoch)": timestamp})
        self.display.save_notes(self.logging_entries.values())
        
        # Clear the notes dictionary
        for key in self.logging_entries:
            self.logging_entries[key] = ""
        # Clear the text entries on the GUI
        for line in self.lineedits:
            line.clear()
   
    def load_notes_entries(self):
        """
        Method to read in the log_entries.yaml config file and grab onto that dictionary. If it can't
        find that file, it returns an empty dictionary - no logging entries will be displayed.
        
        Updates - 
            - self.notes_dict: dict, entries to display on the logging panel
        """
        # Read in the logging config file to initialize the notes entries 
        try:
            with open("config/log_entries.yaml", 'r') as stream:
                self.notes_dict = yaml.safe_load(stream)
        except FileNotFoundError as e:
            logger.warning(f"Error in reading log_entries config file: {e}. Leaving logging panel empty.")
            self.notes_dict = {}
    
    ## --------------------- DATA INPUT & STREAMING DISPLAY --------------------- ##

    def build_plotting_layout(self, center_layout:QLayout):
        """
        A method to build the central plotting panel. Takes in the parent layout (center_layout) and adds a QTabWidget
        to give us a convienent way to display the live sensor plots. For each sensor (stored in self.sensor_names), we add a tab
        to hold the matplotlib figure and toolbar that will display sensor data.

        Args:
            center_layout (QLayout): The main window layout we want to nest the plots in
        """
        center_layout.setContentsMargins(10, 20, 10, 0)
        # Make a title
        label = QLabel(self)
        label.setText("Live Sensor Data")
        label.setFont(self.bold16)
        label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        center_layout.addWidget(label)

        # Initialize the plotting flag
        self.data_collection = False

        # Create some object variables to hold plotting information - the QTabWidget that displays the figs, and a dictionary
        # to hold onto the figure objects themselves for later updating
        self.plot_tab = QTabWidget(self)
        self.plot_figs = {}
        # Loop through the sensors, create a figure & toolbar for each, and add them to the QTabWidget
        for sensor in self.sensor_names:
            # Create a new tab and give it a vertical layout
            tab = QWidget(self)
            tab.setObjectName(sensor)
            tab_vbox = QVBoxLayout(tab)
            # For each figure, we want a subplot corresponding to each piece of data returned by the sensor. Grab that number
            num_subplots = len(self.big_data_dict[sensor]["Data"])
            # Create the figure and toolbar
            fig = MyFigureCanvas(x_init=[[time.time()]]*num_subplots,   # List of lists, one for each subplot, to initialize the figure x-data
                                 y_init=[[0]]*num_subplots, # List of lists, one for each subplot, to initialize the figure y-data
                                 xlabels=["Time (epoch)"]*num_subplots,
                                 ylabels=list(self.big_data_dict[sensor]["Data"].keys()),
                                 num_subplots=num_subplots,
                                 x_range=self.default_plot_length, # Set xlimit range of each axis
                                 )
            toolbar = NavigationToolbar(canvas=fig, parent=self, coordinates=False)
            # Add the figure and toolbar to this tab's layout
            tab_vbox.addWidget(toolbar, alignment=Qt.AlignHCenter)
            tab_vbox.addWidget(fig)
            # Add this tab to the QTabWidget
            self.plot_tab.addTab(tab, sensor)
            # Hold onto the figure object for later
            self.plot_figs.update({sensor: fig})
        # Once we've done all that, add the QTabWidget to the main layout
        center_layout.addWidget(self.plot_tab)
        
        # Finally, add a custom tab to plot multiple readings from multiple sensors
        self.add_main_plots_tab()
        
        return center_layout

    def add_main_plots_tab(self):
        """Method to build a unique tab to show a specified set of sensor channels on the main page. Sensors to show here are set in 
        main_page_plots.yaml
        """
        # Create a new tab and give it a vertical layout
        tab = QWidget(self)
        tab.setObjectName("All")
        tab_vbox = QVBoxLayout(tab)
        # Read in the plots we want on the main page
        y_axis_labels, num_subplots = self.load_main_page_plot_dict()
        # Make a figure and toolbar for the main page and put them in the tab
        fig = MyFigureCanvas(x_init=[[time.time()]]*num_subplots,   # List of lists, one for each subplot, to initialize the figure x-data
                                 y_init=[[0]]*num_subplots, # List of lists, one for each subplot, to initialize the figure y-data
                                 xlabels=["Time (epoch)"]*num_subplots,
                                 ylabels=y_axis_labels,
                                 num_subplots=num_subplots,
                                 x_range=self.default_plot_length, # Set xlimit range of each axis
                                 axis_titles=list(self.main_page_plots.keys())
                                 )
        toolbar = NavigationToolbar(fig, self, coordinates=False)
        tab_vbox.addWidget(toolbar, alignment=Qt.AlignHCenter)
        tab_vbox.addWidget(fig)
        # Add the figure to the stored dictionary of data streaming figures
        self.plot_figs.update({"All":fig})
        # Add the tab to the QTabWidget
        self.plot_tab.insertTab(0, tab, "Specified Plots")
        # Set the current index so this tab is visible when the GUI opens. Also set the font
        self.plot_tab.setCurrentIndex(0)
        self.plot_tab.setFont(self.norm10)

    def load_main_page_plot_dict(self):
        """Method to read and parse the main_page_plots.yaml config file

        Returns:
            y_axis_labels (list): List of axis labels for the main page subplots

            **num_subplots**: *int* Number of needed main page subplots
        """
        # If we can find it, read in the main page configuration yaml file. This loads a dictionary with the names of sensors and channels
        # we want to put on the main page. It has key-value pairs of {"sensor name":{["channel name", "other channel name"]}, ...}
        try:
            with open("config/main_page_plots.yaml", 'r') as stream:
                self.main_page_plots = yaml.safe_load(stream)
        # If we can't find it, note that
        except:
            logger.warning("Error in reading the main_page_plots configuration file. Check your directories.")
            self.main_page_plots = {}

        # Parse through the dictionary to extract the data channels we want to plot
        num_subplots = 0 # and keep an eye on how many subplots we need to initialize
        y_axis_labels = []
        for key in self.main_page_plots: # Key: "sensor name"
            if key in self.sensor_names:
                main_page_plot_channels = self.main_page_plots[key]
                for channel in main_page_plot_channels:
                    y_axis_labels.append(channel)
                    num_subplots += 1

        return y_axis_labels, num_subplots

    def update_plots(self):
        """Method to update the live plots with the buffers stored in self.big_data_dict
        """
        # If the data collection flag is active...
        if self.data_collection:
            # Grab the name of the current QTabWidget tab we're on (which sensor data we're displaying)
            plot_name = self.plot_tab.currentWidget().objectName()
            fig = self.plot_figs[plot_name]
            # Make sure the figure is the correct object - not strictly necessary, but a good safety check
            if type(fig) == MyFigureCanvas:
                # Grab the updated x and y values from the big data buffer
                x_data_list, y_data_list = self.get_xy_data_from_buffer(plot_name)
                # Pass the updated data into the figure object and redraw the axes
                fig.update_data(x_new=x_data_list, y_new=y_data_list)
                fig.update_canvas()

    def get_xy_data_from_buffer(self, plot_name:str):
        """Method to parse the big data buffer and pull out the sensor channels we're interested in plotting.

        Args:
            plot_name (str): The name of the QWidget we're plotting on, should match a sensor in self.sensor names or be "All" for the
                main page plots

        Returns:
            x_data_list (list): List of deques from self.big_data_dict - timestamp for each sensor channel

            **y_data_list** (list): List of deques from self.big_data_dict - data for each sensor channel
        """
        # Try to extract the updated data from the big buffer
        try:
            num_subplots = len(self.big_data_dict[plot_name]["Data"].keys())
            x_data_list = [self.big_data_dict[plot_name]["Time (epoch)"]]*num_subplots # Same timestamp for all sensor readings
            y_data_list = list(self.big_data_dict[plot_name]["Data"].values())
        # If we can't do that, we're probably on the "main page plots" tab, in which case the plot name is "All"
        except KeyError as e:
            # If we /are/ on that page, we need to do a little more finagling to extract the data we want
            if plot_name == "All":
                # Grab the sensors we want to plot, from the dictionary we read in earlier (add_all_plots_page)
                sensors = list(self.main_page_plots.keys())
                # The dictionary has key-value pairs of "sensor name":["sensor channel to plot", "other sensor channel to plot"].
                # Loop through both the sensor names /and/ the sensor channels we want to plot, grabbing their data from the big dict
                x_data_list = []
                y_data_list = []
                for sensor in sensors:
                    subplot_names = self.main_page_plots[sensor]
                    for subplot_name in subplot_names:
                        x_data_list.append(self.big_data_dict[sensor]["Time (epoch)"])
                        y_data_list.append(self.big_data_dict[sensor]["Data"][subplot_name])
            # Otherwise (and we should never get here since everything is passed in externally), something went wrong. The plots safely don't update if we pass in None
            else:
                logger.warning(f"Error in reading the data buffer when updating plots: {e}")
                x_data_list = None
                y_data_list = None

        return x_data_list, y_data_list

    ## --------------------- DATA COLLECTION PIPELINE --------------------- ##

    def init_data_pipeline(self):
        """Creates objects of the Sensor(), Interpreter(), and Display() classes, and sets busses and delay times 
        for each sense/interpret/save process (see run_data_collection for how these are all used)
        """
        # Create each main object of the pipeline
        self.sensor = Sensor()
        self.interpretor = Interpreter()
        self.writer = Writer()

        # Initialize a bus for each thread we plan to spin up later
        self.abakus_bus = Bus()
        self.flowmeter_sli2000_bus = Bus()
        self.flowmeter_sls1500_bus = Bus()
        self.laser_bus = Bus()
        self.picarro_gas_bus = Bus()
        self.bronkhorst_bus = Bus()
        self.main_interp_bus = Bus()

        # Set the delay times (sec) - be a little careful that these delay times play nicely with the timer
        # firing rates set in __init__. Shouldn't trigger the timer more frequently than it takes to get data to plot
        # These are also currently conservative
        self.sensor_delay = 0.3
        self.interp_delay = 0.1
        self.write_delay = 0.1

    def init_data_buffer(self):
        """Method to read in and save the sensor_data configuration yaml file

        Updates:
            **self.big_data_dict**: *dict* - Holds buffer of data with key-value pairs 'Sensor Name':deque[data buffer]

            **self.sensor_names**: *list* - Sensor names that correspond to the buffer dict keys

        """
        # Read in the sensor data config file to initialize the data buffer. 
        # Creates a properly formatted, empty dictionary to store timestamps and data readings to each sensor
        try:
            with open("config/sensor_data.yaml", 'r') as stream:
                self.big_data_dict = yaml.safe_load(stream)
        except FileNotFoundError as e:
            logger.error(f"Error in loading the sensor data config file: {e}")
            self.big_data_dict = {}

        # Comb through the keys, set the timestamp to the current time and the data to zero
        sensor_names = self.big_data_dict.keys()
        for name in sensor_names:
            self.big_data_dict[name]["Time (epoch)"] = deque([time.time()], maxlen=self.max_buffer_length)
            channels = self.big_data_dict[name]["Data"].keys()
            for channel in channels:
                self.big_data_dict[name]["Data"][channel] = deque([0.0], maxlen=self.max_buffer_length)

        # Grab the names of the sensors from the dictionary
        self.sensor_names = list(sensor_names)

    def run_data_collection(self):
        """Method to complete the entire sense/interpret/save data pipeline once. This is called by a timer way back in __init__, so gets triggered every time that
        timer fires. It spins up a bunch of threads to gather data from each sensor, pass raw data into the interpretor class, and save the processed data
        """
        # If data collection is active...
        if self.data_collection:
            # Create a ThreadPoolExecutor to accomplish a bunch of tasks at once. These threads pass data between themselves with busses (which handle
            # proper locking, so we're not trying to read and write at the same time) and return a big dictionary of the most recent processed sensor data
            with concurrent.futures.ThreadPoolExecutor() as self.executor:
                self.executor.submit(self.sensor.abakus_producer, self.abakus_bus, self.sensor_delay)
                self.executor.submit(self.sensor.flowmeter_sli2000_producer, self.flowmeter_sli2000_bus, self.sensor_delay)
                self.executor.submit(self.sensor.flowmeter_sls1500_producer, self.flowmeter_sls1500_bus, self.sensor_delay)
                self.executor.submit(self.sensor.laser_producer, self.laser_bus, self.sensor_delay)
                self.executor.submit(self.sensor.picarro_gas_producer, self.picarro_gas_bus, self.sensor_delay)
                self.executor.submit(self.sensor.bronkhorst_producer, self.bronkhorst_bus, self.sensor_delay)
                self.executor.submit(self.interpretor.main_consumer_producer, self.abakus_bus, self.flowmeter_sli2000_bus,
                                            self.flowmeter_sls1500_bus, self.laser_bus, self.picarro_gas_bus, self.bronkhorst_bus, 
                                            self.main_interp_bus, self.interp_delay)

                eWriter = self.executor.submit(self.writer.write_consumer, self.main_interp_bus, self.write_delay)

            # Get the processed data from the final class (also blocks until everything has completed its task)
            data = eWriter.result()
            # Update our internal data buffer with the processed data
            self.update_buffer(data, use_noise=False)

    def update_buffer(self, new_data:dict, use_noise=False):
        """Method to update the self.big_data_dict buffer with new data from the sensor pipeline.
        
        Args:
            new_data (dict): Most recent data update. Should have the same key/value structure as big_data_dict
            use_noise (bool): Adds some random noise if true. For testing only
        """
        # For each sensor, grab the timestamp and the data from each sensor channel
        for name in self.sensor_names:
            # Grab and append the timestamp
            try:    # Check if the dictionary key exists... 
                new_time = new_data[name]["Time (epoch)"]  
                self.big_data_dict[name]["Time (epoch)"].append(new_time)
            except KeyError as e:   # ... otherwise log an exception
                logger.warning(f"Error updating the {name} buffer timestamp: {e}")
            except TypeError as e:  # Sometimes due to threading shenanigans it comes through as "NoneType", check for that too
                logger.warning(f"Error updating the {name} buffer timestamp: {e}")
            
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
                    logger.warning(f"Error updating the {name} buffer data: {e}")
                except TypeError as e: 
                    logger.warning(f"Error updating the {name} buffer data: {e}")


###################################### HELPER CLASSES ######################################

class MyFigureCanvas(FigureCanvas):
    """This is the FigureCanvas in which the live plot is drawn."""
    def __init__(self, x_init:deque, y_init:deque, xlabels:list, ylabels:list, num_subplots=1, x_range=60, axis_titles=None) -> None:
        """
        :param x_init:          Initial x-data
        :param y_init:          Initial y-data
        :param x_range:         How much data we show on the x-axis, in x-axis units

        """
        super().__init__(plt.Figure())

        # Initialize constructor arguments
        self.x_data = x_init
        self.y_data = y_init
        self.x_range = x_range
        self.num_subplots = num_subplots

        # Generate and store a figure axis for the number of subplots passed in
        self.axs = []
        for i in range(0, num_subplots):
            ax = self.figure.add_subplot(num_subplots+1, 1, i+1)
            self.axs.append(ax)
            ax.set_xlabel(xlabels[i])
            ax.set_ylabel(ylabels[i])
            if axis_titles is not None:
                ax.set_title(axis_titles[i])

        # Set a figure size
        self.figure.set_figheight(5*num_subplots)
        self.figure.tight_layout(h_pad=4)
        
        self.draw()   

    def update_data(self, x_new=None, y_new=None):
        """Method to update the variables to plot. If nothing is given, doesn't update data - safety catch in case something has gone wrong with the GUI"""    
        if x_new is None:
            pass
        else:
            self.x_data = x_new

        if y_new is None:
            pass
        else:
            self.y_data = y_new

    def update_canvas(self) -> None:
        """Method to update the plots based on the buffers stored in self.x_data and self.y_data"""
        # Loop through the number of subplots in this figure
        for i, ax in enumerate(self.axs):
            # Clear the figure without resetting the axis bounds or ticks
            for artist in ax.lines:
                artist.remove()
            # Plot the updated data and make sure we aren't either plotting offscreen or letting the x axis get too long
            ax.plot(self.x_data[i], self.y_data[i], '.--')
            xlim = ax.get_xlim()
            if (xlim[1] - xlim[0]) >= self.x_range:
                ax.set_xlim([self.x_data[i][-1] - self.x_range, self.x_data[i][-1] + 1])

        self.draw()

        # Faster plotting code but can't get the x-axis updating to work
        # ---------
        # self._line_.set_ydata(self.y_data)
        # self._line_.set_xdata(self.x_data)
        # self.ax.draw_artist(self.ax.patch)
        # self.ax.draw_artist(self._line_)
        # self.ax.set_ylim(ymin=min(self.y_data), ymax=min(self.y_data))
        # self.ax.set_xlim(xmin=self.x_data[0], xmax=self.x_data[-1])
        # self.draw()
        # self.update()
        # self.flush_events()

# pyqt threading
class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:
        - finished: None
        - error: tuple (exctype, value, traceback.format_exc() )
        - result: anything (object data returned from processing)
        - progress: int indicating % progress
    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handle worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    """
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except: # If there's an error, report it
            exctype, value = sys.exc_info()[:2]
            logger.error(traceback.print_exc((exctype, value, traceback.format_exc())))
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit() # Done


###################################### HELPER FUNCTIONS ######################################

def find_grid_dims(num_elements, num_cols):
    """Method to determine the number of rows we need in a grid given the number of elements and the number of columns

    Args:
        num_elements (int): How many elements we want to split
        num_cols (int): How many columns across which we want to split them

    Returns:
        num_rows (int): Number of rows needed in the grid
        
        **num_cols**: *int*  Number of columns needed in the grid
    """    

    num_rows = num_elements / num_cols
    # If the last number of the fraction is a 5, add 0.1. This is necessary because Python defaults to 
    # "bankers rounding" (rounds 2.5 down to 2, for example) so would otherwise give us too few rows
    if str(num_rows).split('.')[-1] == '5':
        num_rows += 0.1
    num_rows = round(num_rows)

    return num_rows, num_cols

if __name__ == "__main__":
    qapp = QtWidgets.QApplication(sys.argv)
    app = ApplicationWindow()
    qapp.exec_()