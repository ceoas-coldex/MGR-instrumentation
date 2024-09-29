import serial
from serial import SerialException
import time
import yaml
import crcmod

try:
    import ieee754_conversions
except ImportError:
    import pathlib
    import sys
    _parentdir = pathlib.Path(__file__).parent.parent.resolve()
    sys.path.insert(0, str(_parentdir))
    import ieee754_conversions
    sys.path.remove(str(_parentdir))

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


class MeltHead:
    def __init__(self, serial_port="COM7", baudrate=38400) -> None:
        self.initialize_pyserial(serial_port, baudrate)

        self.AUTO = bytes.fromhex("55 FF 05 10 03 00 09 46 01 04 08 01 01 0F 01 00 0A 38 7C")
        self.OFF = bytes.fromhex("55 FF 05 10 03 00 09 46 01 04 08 01 01 0F 01 00 3E 9F 0B")

        self.melthead_on = False

    def __del__(self):
        self.ser.close()

    def initialize_pyserial(self, port, baud):
        """
        Method to open the serial port at the specified baud. Also specifies a timeout to prevent infinite blocking.
        These values (except for timeout) MUST match the instrument. Typing "mode" in the Windows Command Prompt 
        gives information about serial ports, but sometimes the baud is wrong, so beware. Check sensor documentation.
        Inputs - port (str, serial port), baud (int, baud rate)
        """
        try:
            self.ser = serial.Serial(port, baud, timeout=0.5)
            logger.info(f"Connected to serial port {port} with baud {baud}")
        except SerialException:
            logger.warning(f"Could not connect to serial port {port}")
    
    def initialize_pid(self):
        pass
    
    def query(self):
        pass

    def calc_data_crc(self, string):
        crc_func = crcmod.mkCrcFun(0x11021, 0, True, 0xFFFF)
        string_encoded = bytes.fromhex(string)

        crc = hex(crc_func(string_encoded))
        crc = crc[2:]
        if len(crc) < 4:
            crc = '0' + crc

        bit1 = crc[2:]
        bit2 = crc[0:2]

        return bit1+bit2
    
    def c_to_f(self, tempc):
        return (tempc * 9/5) + 32
    
    def send_setpoint(self, setpoint):
        preamble = '55 FF' 
        frame_type = '05'
        destination_address = '10' 
        source_address = '00' 
        length = '00 0A'
        header_crc = 'EC'
        setpoint_command = '01 04 07 01 01 08'
        setpoint_f = self.c_to_f(setpoint)
        setpoint_data = ieee754_conversions.dec_to_hex(setpoint_f)
        data_crc = self.calc_data_crc(setpoint_command+setpoint_data)

        cmd = preamble+frame_type+destination_address+source_address+length+header_crc+setpoint_command+setpoint_data+data_crc
        print(cmd)
        cmd = bytes.fromhex(cmd)
        self.ser.flush()
        self.ser.write(cmd)

    def start_control_loop(self):
        # print(self.melthead_on)
        # if not self.melthead_on:
        self.ser.write(self.AUTO)
        self.melthead_on = True

    def stop_control_loop(self):
        # if self.melthead_on:
        self.ser.write(self.OFF)
        self.melthead_on = False

if __name__ == "__main__":

    ## ------- UI INTEFACE FOR TESTING  ------- ##
    with open("config/sensor_comms.yaml", 'r') as stream:
        comms_config = yaml.safe_load(stream)

    port = comms_config["Melthead"]["serial port"]
    baud = comms_config["Melthead"]["baud rate"]

    mymelt = MeltHead(serial_port=port, baudrate=baud)

    print("Testing melthead (EZ-ZONE) serial communication\n")
    stop = False
    while not stop:
        command = input("a: Initialize, b: Start control loop, c: Stop control loop, d: Send setpoint, x: Quit \n")
        if command == "a" or command == "A":
            mymelt.initialize_pid()
        elif command == "b" or command == "B":
            mymelt.start_control_loop()
        elif command == "c" or command == "C":
            mymelt.stop_control_loop()
        elif command == "d" or command == "D":
            setpoint = input("Enter setpoint (degC):")
            try:
                float(setpoint)
            except:
                print("Could not convert given setpoint to a float. Please try again")
            else:
                mymelt.send_setpoint(float(setpoint))
        elif command == "x" or command == "X":
            stop = True
        else:
            print("Invalid entry. Try again")

# cmd = b'\x01\x03\x01\x68\x00\x02\x44\x2B'

# cmd = bytes.fromhex('55 FF 05 10 00 00 06 E8 01 03 01 04 01 01 E3 99')

# cmd = bytes.fromhex('55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 3F 80 00 00 8D DF') # -17.2, should be 1

# cmd = bytes.fromhex("55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 C1 89 99 9A 6C 6F" ) # -27.3, should be -17.2

# cmd = bytes.fromhex("55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 41 20 00 00 5D 24") # -12.2, should be 10

# cmd = bytes.fromhex("55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 41 A0 00 00 B1 28") # -6.7, should be 20

                      #55FF 0510 0000 0AEC 0104 0701 0108 41f0 28f6 18d4
# cmd = bytes.fromhex("55FF 0510 0000 0AEC 0104 0701 0108 41F0 0000 52AB") # -1.1, should be 30

                     #"55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 42 00 00 00 ab 02"

# cmd = bytes.fromhex("55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 42 00 00 00 AB 02") # 0, should be 32 ### OH SHIT IT'S CELSIUS

# cmd = bytes.fromhex(" 55 FF        05             10                00           00 0A                 EC      01 04     07 01      01 08   42 0C 00 00         08 A7")             # 1.7, should be 35
#                     |preamble|Frame type (?)|dest. addr (zone)|source addr.|length (MSB first)(10)|header crc|        ^parameter^           ^ iEEE 754 ^   |data crc (LSB first)|   
#                                  
#                       BACnet Data Expecting Reply?
#                        
# cmd = bytes.fromhex("55 FF    05  10   00 00 0A EC 01 04 07 01 01 08 42 20 00 00 90 01") # 4.4, should be 40

                      #55FF 0510 0000 0AEC 01 04 07 01 01 08 42 48 00 00 1f c2
# cmd = bytes.fromhex("55FF 0510 0000 0AEC 01 04 07 01 01 08 42 48 00 00 1F C2") # 10, should be 50

# cmd = bytes.fromhex("55FF 0510 0000 06E8 0103 0107 0101 8776")

# cmd = bytes.fromhex("55 FF 05 10 03 00 06 43 01 03 02 08 1F 01 0C 16")

# myserial = serial.Serial(port="COM7", baudrate=38400, timeout=1)

# res_list = []
# for i in range(1):
#     myserial.flush()
#     myserial.write(cmd)
#     res = myserial.readline()
#     # res = read_temp()
#     # print(res)
#     res_str = [str(res.hex())]
#     # print([res_str[i:i+2] for i in range(0, len(res_str), 2)])
#     res_list.append(res_str)
#     # time.sleep(1)

# print(res_list)

# myserial.close()

