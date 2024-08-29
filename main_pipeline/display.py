# -------------
# The display class
# -------------

import time

from gui import GUI
from main_pipeline.bus import Bus

import logging
from logdecorator import log_on_start , log_on_end , log_on_error
logger = logging.getLogger(__name__) # set up a logger for this module

logger.setLevel(logging.DEBUG) # set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
ch = logging.StreamHandler() # create a handler
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

class Display():
    """Class that reads the interpreted data and displays it on the GUI"""
    def __init__(self, gui:GUI) -> None:
        logger.info("Display class initiated")
        # Store the GUI
        self.gui = gui

    def display_consumer(self, interpretor_bus:Bus, delay):
        """Method to read the processed data published by the interpretor class and update the appropriate buffers for plotting"""
        interp_data = interpretor_bus.read()
        # logger.info(f"Data: \n{interp_data}")
        try:
            self.gui.update_buffer(interp_data)
        except TypeError:
            pass
        time.sleep(delay)