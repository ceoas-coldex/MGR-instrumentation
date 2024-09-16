# -------------
# The display class
# -------------

import time
import yaml
import csv
import pandas as pd

from gui import GUI
from main_pipeline.bus import Bus

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

class Display():
    """Class that reads the interpreted data and displays it on the GUI"""
    @log_on_end(logging.INFO, "Display class initiated", logger=logger)
    def __init__(self, gui:GUI) -> None:
        # Store the GUI
        self.gui = gui

        self.init_data_saving()

    def init_data_saving(self):
        """Method to set up data storage and configure internal data management"""
        # Read in the sensor config file to grab a list of all the sensors we're working with
        with open("config/sensor_data.yaml", 'r') as stream:
            big_data_dict = yaml.safe_load(stream)
        self.sensor_names = big_data_dict.keys()

        self._load_data_directory()

        data_titles = []
        for name in self.sensor_names:
            data_titles.append(f"{name}: time (epoch)")
            channels = big_data_dict[name]["Data"].keys()
            for channel in channels:
                data_titles.append(f"{name}: {channel}")

        self.init_csv(self.csv_filepath, data_titles)
    
    def init_csv(self, filepath, header):
        """Method to initialize a csv with given header"""
        # Check if we can read the file
        try:
            with open(filepath, 'r'):
                pass
        # If the file doesn't exist, create it and write in whatever we've passed as row titles
        except FileNotFoundError:
            with open(filepath, 'x') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', lineterminator='\r')
                writer.writerow(header)

    def _load_data_directory(self):
        """
        Method to read the data_saving.yaml config file and set the data filepath accordingly. If
        it can't find that file, it defaults to the current working directory.
        
        Updates - 
            - self.csv_filepath: str, where the sensor data gets saved as a csv
        """
        # Set up the first part of the file name - the current date
        # Grab the current time in YYYY-MM-DD HH:MM:SS format
        datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        # Grab only the date part of the time
        date = datetime.split(" ")[0]
        # Try to read in the data saving config file to get the directory and filename suffix
        try:
            with open("config/data_saving.yaml", 'r') as stream:
                saving_config_dict = yaml.safe_load(stream)
            # Create filepaths in the data saving directory with the date (may change to per hour depending on size)
            directory = saving_config_dict["Sensor Data"]["Directory"]
            suffix = saving_config_dict["Sensor Data"]["Suffix"]
            self.csv_filepath = f"{directory}\\{date}{suffix}.csv"
        # If we can't find the file, note that and set the filepath to the current working directory
        except FileNotFoundError as e:
            logger.warning(f"Error in loading data_saving config file: {e}. Saving to current working directory")
            self.csv_filepath = f"{date}_notes.csv"
        # If we can't read the dictonary keys, note that and set the filepath to the current working directory
        except KeyError as e:
            logger.warning(f"Error in reading data_saving config file: {e}. Saving to current working directory")
            self.csv_filepath = f"{date}_notes.csv"
    
    def save_data(self, data_dict):
        """Method to save the passed in directory to a csv file
        
        Args -
            - data_dict: dict, must have the same key-value pairs as the expected dictionary from config/sensor_data.yaml"""
        
        # print(pd.DataFrame(data_dict))
        tstart = time.time()
        to_write = []
        try:
            for name in self.sensor_names:
                sensor_timestamp = data_dict[name]["Time (epoch)"]
                to_write.append(sensor_timestamp)
                channel_data = data_dict[name]["Data"].values()
                for data in channel_data:
                    to_write.append(data)
        except KeyError as e:
            logger.warning(f"Error in reading data dictionary: {e}")

        try:
            with open(self.csv_filepath, 'a') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', lineterminator='\r')
                writer.writerow(to_write)
        except FileNotFoundError as e:
            logger.warning(f"Error in accessing csv to save data: {e}")
        tend = time.time()
        print(f"saving data took {tend-tstart} seconds")

    def display_consumer(self, interpretor_bus:Bus, delay):
        """Method to read the processed data published by the interpretor class, save it to a csv, and update 
        the appropriate buffers for plotting"""
        interp_data = interpretor_bus.read()
        # logger.info(f"Data: \n{interp_data}")
        try:
            tstart = time.time()
            self.gui.update_buffer(interp_data, use_noise=True)
            tend = time.time()
            print(f"updaing buffer took {tend-tstart} seconds")
            self.save_data(interp_data)
            
        except TypeError:
            pass
        time.sleep(delay)