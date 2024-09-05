# -------------
# This script creates shadow hardware. If you're not connected to the instruments, this will substitute sensor readings
# with simulated values that have the same representation and type as real data 
# 
# Ali Jones
# Last updated 8/29/24
# -------------

import time

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

logger = logging.getLogger(__name__) # set up a logger for this module
logger.setLevel(logging.DEBUG) # set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
ch = logging.StreamHandler() # create a handler
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

class Abakus():
    def __init__(self, serial_port="COM3", baud_rate=38400) -> None:
        """Fake hardware, pretends to do everything the real Abakus class does"""
        self.initialize_pyserial(serial_port, baud_rate)

    def __del__(self) -> None:
        self.stop_measurement()

    def initialize_pyserial(self, port, baud):
        logger.info(f"Fake hardware, pretending to use serial port {port} with baud {baud}")

    @log_on_start(logging.INFO, "Initializing Abakus")
    def initialize_abakus(self):
        """
        The initialization methods return one of three values: 
        0 (real hardware, failed to initialize), 1 (real hardware, succeeded), 2 (simulated hardware)
            
            Returns - 2
        """
        logger.info("Abakus initialized")
        return 2
    
    @log_on_end(logging.INFO, "Abakus measurements started", logger=logger)
    def start_measurement(self):
        pass

    @log_on_end(logging.INFO, "Abakus measurements stopped", logger=logger)
    def stop_measurement(self):
        pass

    @log_on_end(logging.INFO, "Abakus queried", logger=logger)
    def query(self):
        """Returns - timestamp (float, epoch time), data_out (str, unprocessed string)"""

        fake_abakus_data = "00000008 00000000 00000009 00000000 00000010 00000000 00000011 00000000 00000012 00000000 00000013 00000000 00000014 00000000 00000016 00000000 00000018 00000000 00000020 00000000 00000022 00000000 00000024 00000000 00000026 00000000 00000028 00000000 00000030 00000000 00000032 00000000 00000034 00000000 00000037 00000000 00000040 00000000 00000043 00000000 00000046 00000000 00000049 00000000 00000052 00000000 00000055 00000000 00000058 00000000 00000062 00000000 00000066 00000000 00000070 00000000 00000075 00000000 00000080 00000000 00000090 00000000 00000100 00000000"
        timestamp = time.time()

        return timestamp, fake_abakus_data

class Picarro():
    def __init__(self, serial_port="COM3", baud_rate=19200) -> None:
        """Fake hardware, pretends to do everything the real Picarro class does"""
        self.initialize_pyserial(serial_port, baud_rate)

    def initialize_pyserial(self, port, baud):
        logger.info(f"Fake hardware, pretending to use serial port {port} with baud {baud}")

    
    @log_on_start(logging.INFO, "Initializing Picarro", logger=logger)
    def initialize_picarro(self):
        """
        The initialization methods return one of three values: 
        0 (real hardware, failed to initialize), 1 (real hardware, succeeded), 2 (simulated hardware)
        
        Returns - 2
        """
        logger.info("Initialized Picarro")
        return 2

    @log_on_end(logging.INFO, "Picarro queried", logger=logger)
    def query(self):
        """Returns - timestamp (float, epoch time), picarro_reading (str, raw data)"""
        fake_picarro_data = "2024-08-22 13:52:47.246;-0.990;-0.001;-0.006;0.021"
        timestamp = time.time()

        # Split along the semicolons
        fake_picarro_data = fake_picarro_data.split(";")

        return timestamp, fake_picarro_data

class FlowMeter():
    def __init__(self, serial_port="COM6", baud_rate=115200, sensor_type="SLI2000") -> None:
        """Fake hardware, pretends to do everything the real FlowMeter class does"""
        self.initialize_pyserial(serial_port, baud_rate)
        self.sensor_type = sensor_type

    def initialize_pyserial(self, port, baud):
        logger.info(f"Fake hardware, pretending to use serial port {port} with baud {baud}")

    @log_on_start(logging.INFO, "Initializing Flowmeter", logger=logger)
    def initialize_flowmeter(self):
        """
        The initialization methods return one of three values: 
        0 (real hardware, failed to initialize), 1 (real hardware, succeeded), 2 (simulated hardware)
            
            Returns - 2
        """
        logger.info(f"Flowmeter {self.sensor_type} initialized")
        return 2
    
    def start_measurement(self):
        logger.info(f"Flowmeter {self.sensor_type} measurements started")

    @log_on_end(logging.INFO, "Flowmeter measurements stopped", logger=logger)
    def stop_measurement(self):
        pass

    @log_on_end(logging.INFO, "Flowmeter queried", logger=logger)
    def query(self):
        """Returns - timestamp (float, epoch time), data_out ([int], raw data)"""
        timestamp = time.time()
        fake_flowmeter_sli2000_reading = [126, 0, 53, 0, 2, 255, 252, 205, 126]

        fake_flowmeter_sls1500_reading = [126, 0, 53, 0, 2, 255, 247, 210, 126]
                                    # [126, 0, 53, 0, 2, 255, 246, 211, 126] # also

        return timestamp, fake_flowmeter_sli2000_reading

class Dimetix():
    def __init__(self, serial_port="COM8", baud_rate=19200) -> None:
        """Fake hardware, pretends to do everything the real Dimetix laser class does"""
        self.initialize_pyserial(serial_port, baud_rate)

    def __del__(self) -> None:
        self.stop_laser()

    def initialize_pyserial(self, port, baud):
        logger.info(f"Fake hardware, pretending to use serial port {port} with baud {baud}")
    
    @log_on_start(logging.INFO, "Initializing Dimetix laser", logger=logger)
    def initialize_laser(self):
        """
        The initialization methods return one of three values: 
        0 (real hardware, failed to initialize), 1 (real hardware, succeeded), 2 (simulated hardware)
            
            Returns - 2
        """
        logger.info("Laser initialized")
        return 2
    
    @log_on_end(logging.INFO, "Dimetix laser turned on", logger=logger)
    def start_laser(self):
        pass

    @log_on_end(logging.INFO, "Dimetix laser turned off", logger=logger)
    def stop_laser(self):
        pass

    @log_on_end(logging.INFO, "Dimetix laser queried distance", logger=logger)
    def query_distance(self):
        """Returns - timestamp (float, epoch time), data_out (str, unprocessed string)"""
        fake_laser_distance_reading = "00023" # raw serial output "g0t-00000023"
        timestamp = time.time()
        return timestamp, fake_laser_distance_reading
    
    @log_on_end(logging.INFO, "Dimetix laser queried temperature", logger=logger)
    def query_temperature(self):
        pass

class Bronkhorst():
    def __init__(self, serial_port, baud_rate=38400) -> None:
        """Not yet done. Fake hardware, pretends to do everything the real Dimetix laser class does"""
        self.initialize_pyserial(serial_port, baud_rate)

    def initialize_pyserial(port, baud):
        logger.info(f"Fake hardware, pretending to use serial port {port} with baud {baud}")

    @log_on_end(logging.INFO, "Bronkhorst queried", logger=logger)
    def query(self):
        pass