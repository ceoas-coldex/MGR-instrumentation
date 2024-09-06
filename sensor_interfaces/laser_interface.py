import serial
from serial import SerialException
import time
import yaml

import logging
from logdecorator import log_on_start , log_on_end , log_on_error

logger = logging.getLogger(__name__) # set up a logger for this module
logger.setLevel(logging.DEBUG) # set the lowest-severity log message the logger will handle (debug = lowest, critical = highest)
ch = logging.StreamHandler() # create a handler
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(asctime)s - %(name)s:  %(message)s", datefmt="%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

class Dimetix():
    def __init__(self, serial_port="COM8", baud_rate=19200) -> None:
        """Class to communicate with the dimetix laser distance sensor."""
        # Dimetix communication codes
        self.LASER_ON = b's0o\r\n' # Switches the laser beam on. The laser is on until the Stop / Clear command (STOP_CLR) is issued
        self.STOP_CLR = b's0c\r\n' # Stops the current execution and clears the status LEDs
        self.DIST = b's0g\r\n' # Triggers one distance measurement. Each new command cancels an active measurement
        self.TEMP = b's0t\r\n' # Triggers one temperature measurement

        self.SET_COM_SETTINGS = b's0br+07\r\n' # Sets communication settings to "7" (correct baud, parity, etc. Check docs for more)
        self.READ_ERROR = b's0re\r\n' # Read error stack

        self.CRLF = b'\r\n' # "Carriage return line feed", returned at the end of all sensor readings

        self.RET_SUCCESS = b'g0?\r\n' # "Return successful" command from the laser when turned on or off

        self.initialize_pyserial(serial_port, baud_rate)

        self.laser_status = 0 # flag to keep track internally of what the laser is doing: 0 (off), 1 (on), 3 (error)

    def __del__(self) -> None:
        """Deconstructor, turns off the laser and closes the serial port when this object is destroyed"""
        self.stop_laser()
        time.sleep(0.5)
        self.ser.close()

    def initialize_pyserial(self, port, baud):
        """
        Method to open the serial port at the specified baud. Also specifies a timeout to prevent infinite blocking.
        These values (except for timeout) MUST match the instrument. Typing "mode" in the Windows Command Prompt 
        gives information about serial ports, but sometimes the baud is wrong, so beware. Check sensor documentation.
        Inputs - port (str, serial port), baud (int, baud rate)
        """
        try:
            self.ser = serial.Serial(port, baud, timeout=1, 
                                     bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE)
            logger.info(f"Connected to serial port {port} with baud {baud}")
        except SerialException:
            logger.info(f"Could not connect to serial port {port}")
    
    def initialize_once(self, query_function, timeout:int, measurement:str):
        # Try to query and get a valid distance output. If we can't get a valid reading after a set of attempts, report back that initialization failed
        for i in range(timeout):
            logger.info(f"Laser {measurement} initialization attempt {i+1}/{timeout}")
            timestamp, output = query_function()
            # Validity check: should be able to convert the output to a float
            init_status = 0
            try:
                # The laser starts error messages as "g0@Eaaa", where "aaa" is the error code. If we get that, we've errored
                if output[0:4] == "g0@E":
                    init_status = 3
                # Otherwise, the laser returns successful queries as "g0x±aaaaaaaa", where "x" is specific to the measurement 
                # and "±a" is the data. If we can slice away the first 3 characters and convert the rest to a float, we're good.
                elif type(timestamp) == float and float(output[3:]):
                    logger.info(f"Laser {measurement} initialized")
                    init_status = 1
                    return init_status
                # If something else has gone wrong, we've probably also errored
                else:
                    init_status = 3
            except Exception as e:
                logger.warning(f"Error in laser {measurement} initialization: {e}")
                init_status = 3

        logger.warning(f"Laser {measurement} initialization failed after {i+1} attempts")
        return init_status
    
    def initialize_laser(self, timeout=10):
        """
        Queries the laser until we get a valid output. If we can't get a valid reading after a set of attempts,
        report that initialization failed.
        
        The initialization methods return one of three values: 
        0 (real hardware, failed to initialize), 1 (real hardware, succeeded), 2 (simulated hardware)
        """
        # Set communication settings
        self.ser.write(self.SET_COM_SETTINGS) 
        # Start the laser and grab the result - 0 (off), 1 (on)
        self.laser_status = self.start_laser() 
        # If we've successfully turned on, try querying
        if self.laser_status == 1:
            distance_status = self.initialize_once(self.query_distance, timeout, measurement="distance")
            temp_status = self.initialize_once(self.query_temperature, timeout, measurement="temperature")
        
            # If distance and temperature both initialized, report that we're initialized. Otherwise report that we have an error
            if distance_status == 1 and temp_status == 1:
                self.laser_status = 1
            else:
                self.laser_status = 3

            return self.laser_status
        
        # Otherwise return
        else:
            return self.laser_status

    def start_laser(self):
        """Method to turn on the laser and make sure we've succeeded"""
        # Send the message and get the response
        self.ser.write(self.LASER_ON)
        response = self.ser.read_until(self.CRLF)
        # If we've recieved anything other than a successful laser message, log that and return that we're still off
        if response != self.RET_SUCCESS:
            logger.warn(f"Error returned from starting Dimetix laser: {response}. Check the manual for the error code")
        # Otherwise, log and return that we're on
        else:
            logger.info("Dimetix laser turned on")
            self.laser_status = 1 # our status has changed now
        
        return self.laser_status

    def stop_laser(self):
        """Method to turn off the laser and make sure we've succeeded"""
        # Send the message and get the response
        self.ser.write(self.STOP_CLR)
        response = self.ser.read_until(self.CRLF)
        # If we've recieved anything other than a successful laser message, log and return that we've failed
        if response != self.RET_SUCCESS:
            logger.warn(f"Error returned from stopping Dimetix laser: {response}. Check the manual for the error code")
        # Otherwise, log and return that we're successfully off
        else:
            logger.info("Dimetix laser turned off")
            self.laser_status = 0 # our status has changed now

        return self.laser_status

    @log_on_end(logging.INFO, "Dimetix laser queried distance", logger=logger)
    def query_distance(self):
        # Get the most recent measurement from the laser sensor
        time1 = time.time()
        self.ser.write(self.DIST)
        timestamp = time.time()
        # response = self.ser.readline()
        response = self.ser.read_until(self.CRLF)
        time2 = time.time()
        
        print(f"sending serial message took {timestamp-time1} sec")
        print(f"laser reading took {time2-timestamp} sec")
        
        # Decode the response
        response = response.decode()

        return timestamp, response

    @log_on_end(logging.INFO, "Dimetix laser queried temperature", logger=logger)
    def query_temperature(self):
        # Get the temperature from the laser sensor
        self.ser.write(self.TEMP)
        timestamp = time.time()
        response = self.ser.read_until(self.CRLF)
        # Decode the response
        response = response.decode()

        return timestamp, response
            
if __name__ == "__main__":
    ## ------- DATA PROCESSING FUNCTION FOR TESTING  ------- ##
    def process_distance(distance, timestamp):
        try:
            # The laser starts error messages as "g0@Eaaa", where "aaa" is the error code. If we get that, we've errored
            if distance[0:4] == "g0@E":
                logger.warning(f"Recieved error message from laser distance: {distance} Check manual for error code.")
            # Otherwise, the laser returns a successful distance reading as "g0g+aaaaaaaa", where "+a" is the dist in 0.1mm.
            # We need to slice away the first three characters, strip whitespace, and divide by 100 to get distance in cm
            else:
                distance = distance[3:].strip()
                distance_cm = float(distance) / 100.0
                logger.info(f"Distance measurement {distance_cm}cm, timestamp {timestamp}")
        except ValueError as e:
            logger.warning(f"Error in converting distance reading to float: {e}. Not updating measurement")

    
    def process_temp(temp, timestamp):
        try:
            # The laser starts error messages as "g0@Eaaa", where "aaa" is the error code. If we get that, we've errored
            if temp[0:4] == "g0@E":
                logger.warning(f"Recieved error message from laser temperature: {temp}. Check manual for error code. Not updating measurement")
            # Otherwise, the laser returns successful temperature as "g0t±aaaaaaaa", where "±a" is the temp in 0.1°C.
            # We need to slice away the first three characters, strip whitespace, and divide by 10 to get distance in °C
            else:
                temp = temp[3:].strip()
                temp_c = float(temp) / 10.0
                logger.info(f"Temp measurement {temp_c}°C, timestamp {timestamp}")
        except ValueError as e:
            logger.warning(f"Error in converting temperature reading to float: {e}. Not updating measurement")

    ## ------- UI FOR TESTING  ------- ##
    with open("config/sensor_comms.yaml", 'r') as stream:
        comms_config = yaml.safe_load(stream)
    port = comms_config["Laser Distance Sensor"]["serial port"]
    baud = comms_config["Laser Distance Sensor"]["baud rate"]
    my_laser = Dimetix(serial_port=port, baud_rate=baud)

    print("Testing serial communication\n")
    stop = False
    while not stop:
        command = input("z: Initialize laser, a: Start laser, b: Stop laser, c: Query dist, d: Query temp, x: Quit \n")
        if command == "z" or command == "Z":
            my_laser.initialize_laser()
        elif command == "a" or command == "A":
            my_laser.start_laser()
        elif command == "b" or command == "B":
            my_laser.stop_laser()
        elif command == "c" or command == "C":
            timestamp, output = my_laser.query_distance()
            process_distance(output, timestamp)
        elif command == "d" or command == "D":
            timestamp, output = my_laser.query_temperature()
            process_temp(output, timestamp)
        elif command == "x" or command == "X":
            stop = True
        else:
            print("Invalid entry. Try again")