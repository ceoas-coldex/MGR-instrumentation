# -------------
# This is the main data processing pipeline. It has multiple classes - Sensor, Interpretor, Display - that handle 
# the sensing, interpreting, and displaying of the intrument data. Data is passed between them with the Bus class, 
# managed asynchronously with threads.
#
# It's set up in a producer/consumer framework, with methods that only output data (like sensors) as "producers"
# and those that only recieve data (like a display) as "consumers". There are also "consumer-producers", which 
# read /and/ write data. These generally take in sensor data, do some processing, and republish the processed data.
# 
# Ali Jones
# Last updated 8/23/24
# -------------

import numpy as np
import time
import concurrent.futures
from readerwriterlock import rwlock

import serial
from serial import SerialException
import pandas as pd
import keyboard
import msvcrt as kb
import os, sys

from tkinter_practice import GUI

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import logging
from logdecorator import log_on_start , log_on_end , log_on_error
logging_format = "%(asctime)s: %(message)s"
logging.basicConfig(format=logging_format, level=logging.INFO, datefmt ="%H:%M:%S")
logging.getLogger().setLevel(logging.DEBUG)

# Imports sensor classes for either real hardware or shadow hardware, depending on the situation
test_port = "COM3" # REPLACE WITH READING A .YAML FILE
test_baud = 15200
try:
    serial.Serial(port=test_port, baudrate=test_baud, timeout=5) 
    from sensor_interfaces.abakus_interface import Abakus
    from sensor_interfaces.flowmeter_interface import FlowMeter
    from sensor_interfaces.laser_interface import Dimetix
    from sensor_interfaces.picarro_interface import Picarro
    logging.info(f"Successfully connected to port {test_port}, using real hardware")
except:
    from sim_instruments import Abakus, FlowMeter, Dimetix, Picarro
    logging.info(f"Couldn't find real hardware at port {test_port}, shadowing sensor calls with substitute functions")

class Bus():
    """Class that sets up a bus to pass information around with read/write locking"""
    def __init__(self):
        self.message = None
        self.lock = rwlock.RWLockWriteD() # sets up a lock to prevent simultanous reading and writing

    def write(self, message):
        with self.lock.gen_wlock():
            self.message = message

    def read(self):
        with self.lock.gen_rlock():
            message = self.message
        return message
    
class Sensor():
    """Class that reads from the different sensors and publishes that data over busses"""
    def __init__(self) -> None:
        ### SHOULD EITHER READ IN OR BE PASSED IN A .YAML FILE HERE THAT SPECIFIES PORTS AND BAUDS ###
        self.abakus = Abakus()
        self.flowmeter_sli2000 = FlowMeter(serial_port="COM6")
        self.flowmeter_sls1500 = FlowMeter(serial_port="COM7")
        self.laser = Dimetix()
        self.gas_picarro = Picarro(serial_port="COM3")
        self.water_picarro = Picarro(serial_port="COM4")

    def __del__(self) -> None:
        # self.abakus.__del__()
        pass
    
    ## ------------------- ABAKUS PARTICLE COUNTER ------------------- ##
    def abakus_producer(self, abakus_bus:Bus, delay):
        """Method that writes Abakus data to its bus"""
        data = self.read_abakus()
        abakus_bus.write(data)
        time.sleep(delay)

    def read_abakus(self):
        """Method that gets data from the Abakus \n
            Returns - tuple (timestamp[float, epoch time], data_out[str, bins and counts])"""
        timestamp, data_out = self.abakus.query()
        return timestamp, data_out

    ## ------------------- FLOWMETER ------------------- ##
    def flowmeter_sli2000_producer(self, flowmeter_bus:Bus, delay):
        """Method that writes flowmeter SLI2000 data to its bus"""
        data = self.read_flowmeter(flowmeter_model="SLI2000")
        flowmeter_bus.write(data)
        time.sleep(delay)

    def flowmeter_sls1500_producer(self, flowmeter_bus:Bus, delay):
        """Method that writes flowmeter SLS1500 data to its bus"""
        data = self.read_flowmeter(flowmeter_model="SLS1500")
        flowmeter_bus.write(data)
        time.sleep(delay)

    def read_flowmeter(self, flowmeter_model):
        """
        Method that gets data from a flow meter, specified by the model number. 
        Querying is the same for both models, but processing is different.

            Returns - tuple (timestamp[float, epoch time], data_out([int], bytes)
        """
        if flowmeter_model == "SLI2000":
            timestamp, data_out = self.flowmeter_sli2000.query()
        elif flowmeter_model == "SLS1500":
            timestamp, data_out = self.flowmeter_sls1500.query()
        else:
            timestamp = 0.0
            data_out = [0]
        
        return timestamp, data_out
    
    # ------------------- DIMETIX LASER DISTANCE SENSOR ------------------- ##
    def laser_producer(self, laser_bus:Bus, delay):
        """Method that writes laser data to its bus"""
        data = self.read_laser()
        laser_bus.write(data)
        time.sleep(delay)

    def read_laser(self):
        """Method that gets data from the Dimetix laser \n
            Returns - tuple (timestamp [epoch time], data_out [str])"""
        timestamp, data_out = self.laser.query_distance()
        return timestamp, data_out
    
    ## ------------------- PICARRO ------------------- ##
    def picarro_gas_producer(self, picarro_bus:Bus, delay):
        """Method that writes Picarro gas concentration data to its bus"""
        data = self.read_picarro("GAS")
        picarro_bus.write(data)
        time.sleep(delay)

    def picarro_water_producer(self, picarro_bus:Bus, delay):
        """Method that writes Picarro water isotope data to its bus"""
        data = self.read_picarro("WATER")
        picarro_bus.write(data)
        time.sleep(delay)

    def read_picarro(self, picarro_model):
        """Method that gets data from a Picarro, specified by the model \n
            Returns - tuple (timestamp[float, epoch time], data_out[str])"""
        if picarro_model == "GAS":
            timestamp, data_out = self.gas_picarro.query()
        elif picarro_model == "WATER":
            timestamp, data_out = self.water_picarro.query()
        else:
            timestamp = [0.0]
            data_out = ["0"]

        return timestamp, data_out

class Interpretor():
    """Class that reads data from each sensor bus, does some processing, and republishes on an interpretor bus."""
    def __init__(self) -> None:
        # Set up data frame for all sensors, with initial measurements zeroed and 
        #   the correct formatting to be updated by the sensor outputs
        self.abakus_bin_num = 32
        init_abakus_data = {"abks time (epoch)": [0.0]*self.abakus_bin_num, "bins": [0]*self.abakus_bin_num, "counts": [0]*self.abakus_bin_num}
        self.abakus_data = pd.DataFrame(init_abakus_data)
        self.abakus_total_counts = pd.DataFrame({"abks time (epoch)": [0.0], "total counts": 0})

        self.flowmeter_sli2000_data = pd.DataFrame({"FM time (epoch)": [0.0], "flow (uL/min)": [0.0]})
        self.flowmeter_sls1500_data = pd.DataFrame({"FM time (epoch)": [0.0], "flow (mL/min)": [0.0]})

        init_laser_data = {"lsr time (epoch)": [0.0], "distance (cm)": [0.0], "temperature (°C)": [99.99]}
        self.laser_data = pd.DataFrame(init_laser_data)

        init_picarro_gas_data = {"gas time (epoch)":[0.0], "sample time":[0.0], "CO2":[0.0], "CH4":[0.0], "CO":[0.0], "H2O":[0.0]}
        self.picarro_gas_data = pd.DataFrame(init_picarro_gas_data)

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

        # Process the raw data from each bus (each produces a data frame)
        self.process_abakus_data(abakus_output)
        self.process_flowmeter_data(flowmeter_sli_output, model="SLI2000", scale_factor=5, units="uL/min")
        self.process_flowmeter_data(flowmeter_sls_output, model="SLS1500", scale_factor=500, units="mL/min")
        self.process_laser_data(laser_output)
        self.process_picarro_data(picarro_gas_output, model="GAS")
        # self.process_picarro_data(picarro_water_timestamp, picarro_water_data, model="WATER")
        
        # Concatanate the data frames and take a look at the differece between their timestamps
        big_df = pd.concat([self.abakus_total_counts, self.flowmeter_sli2000_data, 
                            self.flowmeter_sls1500_data, self.laser_data, self.picarro_gas_data], axis=1)

        time1 = self.abakus_total_counts["time (epoch)"] - self.flowmeter_sli2000_data["time (epoch)"]
        time2 = self.abakus_total_counts["time (epoch)"] - self.flowmeter_sls1500_data["time (epoch)"]
        time3 = self.abakus_total_counts["time (epoch)"] - self.laser_data["time (epoch)"]
        time4 = self.abakus_total_counts["time (epoch)"] - self.picarro_gas_data["time (epoch)"]
        # print(f"time difference 1: {time1}")
        # print(f"time difference 2: {time2}")
        # print(f"time difference 3: {time3}")
        # print(f"time difference 4: {time4}")
        
        # Write to the output bus
        output_bus.write(big_df)
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
            if len(bins) == self.abakus_bin_num: 
                # logging.info("Abakus data good, recieved 32 channels.")
                self.abakus_data["time (epoch)"] = timestamp
                self.abakus_data["bins"] = bins
                self.abakus_data["counts"] = counts
                self.abakus_total_counts["time (epoch)"] = timestamp
                self.abakus_total_counts["total counts"] = np.sum(counts)
            else:
                raise Exception("Didn't recieve the expected 32 Abakus channels. Not updating measurement")
        except Exception as e:
            logging.debug(f"Encountered exception in processing Abakus: {e}. Not updating measurement")
            
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

                if model == "SLI2000":
                    self.flowmeter_sli2000_data["time (epoch)"] = timestamp
                    self.flowmeter_sli2000_data[f"flow ({units})"] = flow_rate
                elif model == "SLS1500":
                    self.flowmeter_sls1500_data["time (epoch)"] = timestamp
                    self.flowmeter_sls1500_data[f"flow ({units})"] = flow_rate
                else:
                    logging.debug("Invalid flowmeter model given. Not updating measurement")
        # If that didn't work, give up this measurement
        except Exception as e:
            logging.debug(f"Encountered exception in processing flowmeter {model}: {e}. Not updating measurement.")

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
            logging.debug(f"Encountered exception in validating flowmeter {model}: {e}. Not updating measurement.")
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
            self.laser_data["time (epoch)"] = timestamp
            self.laser_data["distance (cm)"] = output_cm
        except ValueError as e:
            logging.error(f"Error in converting distance reading to float: {e}. Not updating measurement")

    ## ------------------- PICARRO ------------------- ##
    def process_picarro_data(self, picarro_model, model):
        """Method to process data from querying the picarro
        
            Inputs - picarro_data (tuple, (timestamp, raw_data)), model
            
            Updates - self.picarro_gas_data"""
        if model == "GAS":
            try:
                timestamp, data_out = picarro_model
                self.picarro_gas_data["time (epoch)"] = timestamp
                self.picarro_gas_data["sample time"] = data_out[0] # the time at which the measurement was sampled, probably different than timestamp
                self.picarro_gas_data["CO2"] = float(data_out[1])
                self.picarro_gas_data["CH4"] = float(data_out[2])
                self.picarro_gas_data["CO"] = float(data_out[3])
                self.picarro_gas_data["H2O"] = float(data_out[4])
            except Exception as e:
                logging.debug(f"Encountered exception in processing picarro {model}: {e}. Not updating measurement.")
        elif model == "WATER":
            try:
                timestamp, data_out = picarro_model
            except Exception as e:
                logging.debug(f"Encountered exception in processing picarro {model}: {e}. Not updating measurement.")

class Display():
    """Class that reads the interpreted data and displays it. Will eventually be on the GUI, for now it 
    reads the interpretor bus and prints the data"""
    def __init__(self, gui:GUI) -> None:
        self.gui = gui
        self.x = 0
        
        self.ani1 = FuncAnimation(self.gui.f1, self.gui.animate, interval=1000, cache_frame_data=False)
        self.ani2 = FuncAnimation(self.gui.f2, self.gui.animate2, interval=1000, cache_frame_data=False)

    def display_consumer(self, interpretor_bus:Bus, delay):
        interp_data = interpretor_bus.read()
        # logging.info(f"Data: \n{interp_data}")
        try:
            self.gui.update_abakus_buffer(interp_data["abks time (epoch)"].values[0], interp_data["total counts"].values[0])
        except TypeError:
            pass
        time.sleep(delay)

class Executor():
    """Class that handles passing the data around on all the busses. Still needs a clean shutdown."""
    def __init__(self) -> None:
        # Allow us to enter the data collection loop
        self.data_collection = True
        self.sensors_on = True

        # Initialize the GUI (pull in the GUI class and link it to our functions)
        sensors = ["Picarro Gas", "Picarro Water", "Laser Distance Sensor", "Abakus Particle Counter",
                        "Flowmeter SLI2000 (Green)", "Flowmeter SLS1500 (Black)", "Bronkhurst Pressure", "Melthead"]
        self.gui = GUI(sensors)
        
        # Initialize the classes
        self.sensor = Sensor()
        self.interpretor = Interpretor()
        self.display = Display(self.gui)

        # Set what GUI buttons correspond to what functions (stop measurement, query, etc)
        self._set_gui_buttons()

        # Initialize the busses
        self.abakus_bus = Bus()
        self.flowmeter_sli2000_bus = Bus()
        self.flowmeter_sls1500_bus = Bus()
        self.laser_bus = Bus()
        self.picarro_gas_bus = Bus()
        self.main_interp_bus = Bus()

        # Set the delay times (sec)
        self.sensor_delay = 0.1
        self.interp_delay = 0.1
        self.display_delay = 0.1

    def clean_sensor_shutdown(self):
        """Method to cleanly shut down sensors, if they're active"""
        if self.sensors_on:
            del self.sensor
        self.sensors_on = False
    
    @log_on_start(logging.INFO, "Exiting data collection")
    def stop_data_collection(self):
        """Method to stop data collection, called by the 'alt+q' hotkey"""
        self.data_collection = False
        self.clean_sensor_shutdown()
        self.executor.shutdown(wait=False, cancel_futures=True)
    
    def __del__(self) -> None:
        self.clean_sensor_shutdown()
    
    def _set_gui_buttons(self):
        pass    
    
    def execute(self):
        """Method to execute the sensor, interpretor, and display classes with threading. Calls the appropriate methods within
        those classes and passes them the correct busses and delay times."""

        # Add a hotkey to break the loop
        keyboard.add_hotkey('alt+q', self.stop_data_collection, suppress=True, trigger_on_release=True)
        
        while self.data_collection == True:
            try:
                self.gui.run()
                with concurrent.futures.ThreadPoolExecutor() as self.executor:
                    eAbakus = self.executor.submit(self.sensor.abakus_producer, self.abakus_bus, self.sensor_delay)
                    eFlowMeterSLI2000 = self.executor.submit(self.sensor.flowmeter_sli2000_producer, self.flowmeter_sli2000_bus, self.sensor_delay)
                    eFlowMeterSLS1500 = self.executor.submit(self.sensor.flowmeter_sls1500_producer, self.flowmeter_sls1500_bus, self.sensor_delay)
                    eLaser = self.executor.submit(self.sensor.laser_producer, self.laser_bus, self.sensor_delay)
                    ePicarroGas = self.executor.submit(self.sensor.picarro_gas_producer, self.picarro_gas_bus, self.sensor_delay)
                    
                    eInterpretor = self.executor.submit(self.interpretor.main_consumer_producer, self.abakus_bus, self.flowmeter_sli2000_bus,
                                                self.flowmeter_sls1500_bus, self.laser_bus, self.picarro_gas_bus, self.main_interp_bus, self.interp_delay)

                    eDisplay = self.executor.submit(self.display.display_consumer, self.main_interp_bus, self.display_delay)

                eAbakus.result()
                eFlowMeterSLI2000.result()
                eFlowMeterSLS1500.result()
                eLaser.result()
                ePicarroGas.result()
                eInterpretor.result()
                eDisplay.result()

            # If we got a keyboard interrupt (something Wrong happened), don't try to shut down the threads cleanly -
            # prioritize shut down the sensors cleanly and killing the program
            except KeyboardInterrupt:
                try:
                    self.clean_sensor_shutdown()
                    sys.exit(130)
                except SystemExit:
                    self.clean_sensor_shutdown()
                    os._exit(130)
            
if __name__ == "__main__":
    my_executor = Executor()
    data_collection = True
    my_executor.execute()
    del my_executor
