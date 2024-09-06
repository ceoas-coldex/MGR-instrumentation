# -------------
# The intepretor class
# -------------

import numpy as np
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

try:
    from main_pipeline.bus import Bus
except ImportError:
    from bus import Bus

class Interpretor():
    """Class that reads data from each sensor bus, does some processing, and republishes on an interpretor bus."""
    def __init__(self) -> None:

       self._initialize_data_storage()
    
    def _initialize_data_storage(self):
        """
            Method to set up the dict for all sensors, with initial measurements zeroed and the correct formatting to be 
            updated by the sensor outputs. Does this by reading in the data buffer stored in config/sensor_data.yaml and 
            initializing all values
        """
        # Read in the sensor data config file to initialize the data buffer. 
        with open("config/sensor_data.yaml", 'r') as stream:
            self.big_data = yaml.safe_load(stream)

        t_i = time.time()
        # Comb through the keys, set the timestamp to the current time and the data to zero
        sensor_names = self.big_data.keys()
        for name in sensor_names:
            self.big_data[name]["Time (epoch)"] = t_i
            channels = list(self.big_data[name]["Data"].keys())
            for channel in channels:
                self.big_data[name]["Data"][channel] = 0.0
    
    def main_consumer_producer(self, abakus_bus:Bus, flowmeter_sli_bus:Bus, flowmeter_sls_bus:Bus, laser_bus:Bus,
                               picarro_gas_bus:Bus, output_bus:Bus, delay):
        """Method to read from all the sensor busses and write one compiled output file"""
        # Read from all the busses (should be in the form (timestamp, sensor_data))
        abakus_output = abakus_bus.read()
        flowmeter_sli_output = flowmeter_sli_bus.read()
        flowmeter_sls_output = flowmeter_sls_bus.read()
        laser_output = laser_bus.read()
        picarro_gas_output = picarro_gas_bus.read()
        # picarro_water_timestamp, picarro_water_data = picarro_water_bus.read()

        # Process the raw data from each bus (saves the data in self.big_data)
        self.process_abakus_data(abakus_output)
        self.process_flowmeter_data(flowmeter_sli_output, model="SLI2000", scale_factor=5, units="uL/min")
        self.process_flowmeter_data(flowmeter_sls_output, model="SLS1500", scale_factor=500, units="mL/min")
        self.process_laser_data(laser_output)
        self.process_picarro_data(picarro_gas_output, model="GAS")
        # self.process_picarro_data(picarro_water_timestamp, picarro_water_data, model="WATER")
        
        # Uncomment these lines to check the difference in timestamps between the sensors
        # print(f"time difference 1: {self.big_data["Abakus Particle Counter"]["Time (epoch)"] - self.big_data["Picarro Gas"]["Time (epoch)"]}")
        # print(f"time difference 2: {self.big_data["Abakus Particle Counter"]["Time (epoch)"] - self.big_data["Laser Distance Sensor"]["Time (epoch)"]}")
        # print(f"time difference 3: {self.big_data["Abakus Particle Counter"]["Time (epoch)"] - self.big_data["Flowmeter"]["Time (epoch)"]}")
        # # print(f"time difference 4: {self.big_data["Abakus Particle Counter"]["Time (epoch)"] - self.big_data["Picarro Water"]["Time (epoch)"]}")
        
        # Write to the output bus
        output_bus.write(self.big_data)
        time.sleep(delay)

    ## ------------------- ABAKUS PARTICLE COUNTER ------------------- ##
    def process_abakus_data(self, abakus_data):
        """
        Function to processes the data from querying the Abakus. The first measurement comes through with 
        more than the expected 32 channels (since the Abakus holds onto the last measurement from the last batch)
        so you should query the Abakus a couple times before starting data processing. We have a check for that here
        just in case.

            Inputs - abakus_data (tuple, (timestamp, raw_data))    
        
            Updates - self.abakus_data (pd.df, processed timestamp, bins, and particle count/bin)
        """
        # Data processing - from Abby's stuff originally
        try:
            timestamp, data_out = abakus_data
            output = data_out.split() # split into a list
            bins = [int(i) for i in output[::2]] # grab every other element, starting at 0, and make it an integer while we're at it
            counts = [int(i) for i in output[1::2]] # grab every other element, starting at 1, and make it an integer

            # If we've recieved the correct number of bins, update the measurement. Otherwise, log an error
            abakus_bin_num = 32
            if len(bins) == abakus_bin_num: 
                # logger.info("Abakus data good, recieved 32 channels.")
                self.big_data["Abakus Particle Counter"]["Time (epoch)"] = timestamp
                self.big_data["Abakus Particle Counter"]["Other"]["Bins"] = bins
                self.big_data["Abakus Particle Counter"]["Other"]["Counts/Bin"] = counts
                self.big_data["Abakus Particle Counter"]["Data"]["Total Counts"] = int(np.sum(counts))

                logger.debug(f"abakus: {self.big_data['Abakus Particle Counter']}")
            else:
                logger.warning("Didn't recieve the expected 32 Abakus channels. Not updating measurement")
        except KeyError as e:
            logger.warning(f"Error in saving Abakus data to big dict: {e}. Not updating measurement")
        except TypeError as e:
            logger.warning(f"Error in extracting time and data from Abakus reading: {e}. Probably not a tuple. Not updating measurement")
            
    ## ------------------- FLOWMETER ------------------- ##
    def process_flowmeter_data(self, flowmeter_data, model, scale_factor, units):
        """Method to process data from querying the Flowmeter. The scale factor and unit output of the two 
        models differs (SLI2000 - uL/min, SLS1500 - mL/min). Could make that the same if needed, but for now
        I want it to be consistent with the out-of-box software
        
            Inputs - flowmeter_data (tuple, (timestamp, raw_data)), model, scale_factor, units  
        
            Updates - self.flowmeter_SLXXXXX_data (pd.df, processed timestamp and flow rate)"""
        # Check if reading is good
        validated_data = self.check_flowmeter_data(flowmeter_data, model)
        # If it's good, try processing it
        try:
            timestamp = flowmeter_data[0]
            if validated_data:
                rxdata = validated_data[4]
                ticks = self.twos_comp(rxdata[0])
                flow_rate = ticks / scale_factor

                self.big_data["Flowmeter"]["Time (epoch)"] = timestamp
                self.big_data["Flowmeter"]["Data"][f"{model} ({units})"] = flow_rate

        # If that didn't work, give up this measurement
        except Exception as e:
            logger.warning(f"Encountered exception in processing flowmeter {model}: {e}. Not updating measurement.")

    def check_flowmeter_data(self, flowmeter_data, model):
        """Method to validate the flowmeter data with a checksum and some other things. From Abby, I should
        check in with her about specifics. 

            Inputs - flowmeter_data (tuple, (timestamp, raw_data)), model

            Returns - a bunch of bytes if the data is valid, False if not"""
        try:
            raw_data = flowmeter_data[1]
            adr = raw_data[1]
            cmd = raw_data[2]
            state = raw_data[3]
            if state != 0:
                raise Exception("Bad reply from flow meter")
            length = raw_data[4]
            rxdata8 = raw_data[5:5 + length]
            chkRx = raw_data[5 + length]

            chk = hex(adr + cmd + length + sum(rxdata8))  # convert integer to hexadecimal
            chk = chk[-2:]  # extract the last two characters of the string
            chk = int(chk, 16)  # convert back to an integer base 16 (hexadecimal)
            chk = chk ^ 0xFF  # binary check
            if chkRx != chk:
                raise Exception("Bad checksum")

            rxdata16 = []
            if length > 1:
                i = 0
                while i < length:
                    rxdata16.append(self.bytepack(rxdata8[i], rxdata8[i + 1]))  # convert to a 16-bit integer w/ little-endian byte order
                    i = i + 2  # +2 for pairs of bytes

            return adr, cmd, state, length, rxdata16, chkRx

        except Exception as e:
            logger.warning(f"Encountered exception in validating flowmeter {model}: {e}. Not updating measurement.")
            return False
    
    def bytepack(self, byte1, byte2):
        """ 
        Helper method to concatenate two uint8 bytes to uint16. Takes two's complement if negative
            Inputs - byte1 (uint8 byte), byte2 (uint8 byte)
            Return - binary16 (combined uint16 byte)
        """
        binary16 = (byte1 << 8) | byte2
        return binary16
    
    def twos_comp(self, binary):
        """Helper method to take two's complement of binary input if negative, returns input otherwise"""
        if (binary & (1 << 15)):
            n = -((binary ^ 0xFFFF) + 1)
        else:
            n = binary
        return n
    
    # ------------------- DIMETIX LASER DISTANCE SENSOR ------------------- ##
    def process_laser_data(self, laser_data):
        """
        Method to process data from querying the laser. It doesn't always like to return a valid result, but
        if it does, it's just the value in meters (I think, should check with Abby about getting the data sheet there) \n
        
            Inputs - laser_data (tuple, (timestamp, raw_data))
            
            Updates - self.laser_data (pd.df, processed_timestamp, distance reading (cm)). 
            Doesn't currently have temperature because I was getting one or the other, and prioritized distance
        """
        try:
            timestamp, data_out = laser_data
            output_cm = float(data_out) / 100
            self.big_data["Laser Distance Sensor"]["Time (epoch)"] = timestamp
            self.big_data["Laser Distance Sensor"]["Data"]["Distance (cm)"] = output_cm
        except ValueError as e:
            logger.warning(f"Error in converting distance reading to float: {e}. Not updating measurement")
        except TypeError as e:
            logger.warning(f"Error in extracting time and data from laser reading: {e}. Probably not a tuple. Not updating measurement")

    ## ------------------- PICARRO ------------------- ##
    def process_picarro_data(self, picarro_model, model):
        """Method to process data from querying the picarro
        
            Inputs - picarro_data (tuple, (timestamp, raw_data)), model
            
            Updates - self.picarro_gas_data"""
        if model == "GAS":
            try:
                timestamp, data_out = picarro_model
                logger.debug(data_out)
                # self.picarro_gas_data["sample time"] = data_out[0] # the time at which the measurement was sampled, probably different than timestamp

                self.big_data["Picarro Gas"]["Time (epoch)"] = timestamp
                self.big_data["Picarro Gas"]["Data"]["CO2"] = float(data_out[1])
                self.big_data["Picarro Gas"]["Data"]["CH4"] = float(data_out[2])
                self.big_data["Picarro Gas"]["Data"]["CO"] = float(data_out[3])
                self.big_data["Picarro Gas"]["Data"]["H2O"] = float(data_out[4])

            except Exception as e:
                logger.warning(f"Encountered exception in processing picarro {model}: {e}. Not updating measurement.")
        elif model == "WATER":
            try:
                timestamp, data_out = picarro_model
            except Exception as e:
                logger.warning(f"Encountered exception in processing picarro {model}: {e}. Not updating measurement.")

if __name__ == "__main__":
    interp = Interpretor()
    print(interp.big_data)