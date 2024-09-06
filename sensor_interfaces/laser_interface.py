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

        self.RET_SUCCESS = b'g0?\r\n' # "Return successful" command from the laser

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
            # Try to query and get a valid output. If we can't get a valid reading after a set of attempts, report back that initialization failed
            for i in range(timeout+1):
                logger.info(f"Initialization attempt {i+1}/{timeout}")
                timestamp, data_out = self.query_distance()
                # Validity check - should be able to convert the output to a float
                try: 
                    if type(timestamp) == float and float(data_out):
                        logger.info("Laser initialized")
                        self.laser_status = 1
                        return 1
                    else:
                        self.laser_status = 3
                except Exception as e:
                    logger.info(f"Exception in Laser initialization: {e}")
            
            logger.info(f"Laser initialization failed after {i} attempts")
            return self.laser_status
        
        # Otherwise return 0
        else:
            return 0

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
        print(response)
        print(response.decode())
        # Decode the response
        dist_raw = response.decode()
        output = dist_raw[7:].strip()
        return timestamp, output
    
    @log_on_end(logging.INFO, "Dimetix laser queried temperature", logger=logger)
    def query_temperature(self):
        # Get the temperature from the laser sensor
        self.ser.write(self.TEMP)
        temp_raw = self.ser.read_until(self.CRLF)
        # Decode the response
        temp_raw = temp_raw.decode()
        print(temp_raw)
        # A successful response is "g0t+aaaaaaaa", where "a" is the temp in 0.1°C. We need to extract the temp
        # value, strip off any white space, and divide by 10 to get the temp in °C. If we can do that, we've gotten
        # a successful reading
        try:
            temp = temp_raw[3:].strip()
            temp_c = float(temp)/10
        # Otherwise, something is wrong with the reading. 
        except ValueError as e:
            logger.warning(f"Error in reading laser temperature: {temp_raw}. Check manual for the error code")
            temp_c = 9999 # maybe this should be NAN?
            self.laser_status = 3
        
        logger.info(f"Laser temperature {temp_c}°C")
            
if __name__ == "__main__":
    ## ------- DATA PROCESSING FUNCTION FOR TESTING  ------- ##
    def process_distance(data_out, timestamp):
        try:
            output_cm = float(data_out) / 100
        except ValueError as e:
            logger.error(f"Error in converting distance reading to float: {e}")
            output_cm = 0
        logger.info(f"Laser distance {output_cm}cm")

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
            my_laser.query_temperature()
        elif command == "x" or command == "X":
            stop = True
        else:
            print("Invalid entry. Try again")