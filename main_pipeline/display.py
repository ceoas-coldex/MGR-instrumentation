# -------------
# The display class
# -------------

import time

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

    def display_consumer(self, interpretor_bus:Bus, delay):
        """Method to read the processed data published by the interpretor class and update the appropriate buffers for plotting"""
        interp_data = interpretor_bus.read()
        # logger.info(f"Data: \n{interp_data}")
        try:
            self.gui.update_buffer(interp_data, use_noise=True)
            # self.gui._update_plots()
        except TypeError:
            pass
        time.sleep(delay)