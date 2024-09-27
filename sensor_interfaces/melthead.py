# #!/usr/bin/env python3
# """Pymodbus synchronous client example.

# An example of a single threaded synchronous client.

# usage: simple_sync_client.py

# All options must be adapted in the code
# The corresponding server must be started before e.g. as:
#     python3 server_sync.py
# """

# # --------------------------------------------------------------------------- #
# # import the various client implementations
# # --------------------------------------------------------------------------- #
# import pymodbus.client as ModbusClient
# from pymodbus import (
#     ExceptionResponse,
#     FramerType,
#     ModbusException,
#     pymodbus_apply_logging_config,
# )

# # activate debugging
# pymodbus_apply_logging_config("DEBUG")

# port = "COM7"
# # framer=FramerType.SOCKET

# print("get client")
# client = ModbusClient.ModbusSerialClient(
#             port,
#             # timeout=10,
#             # retries=3,
#             baudrate=19200,
#             bytesize=8,
#             parity="N",
#             stopbits=1,
#             # handle_local_echo=False,
#         )

# print("connect to server")
# client.connect()

# cmd = b'010301680002442B'

# print("get and verify data")
# try:
#     client.send(cmd)
#     res = client.recv(32)
#     print(res)
#     # rr = client.read_coils(1, 1, slave=1)
# except ModbusException as exc:
#     print(f"Received ModbusException({exc}) from library")
#     client.close()
# # if rr.isError():
# #     print(f"Received Modbus library error({rr})")
# #     client.close()
# # if isinstance(rr, ExceptionResponse):
# #     print(f"Received Modbus library exception ({rr})")
# #     # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
# #     client.close()

# print("close connection")
# client.close()


# cmd = b'\x01\x03\x01\x68\x00\x02\x44\x2B'

# cmd = bytes.fromhex('55 FF 05 10 00 00 06 E8 01 03 01 04 01 01 E3 99')

# cmd = bytes.fromhex('55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 3F 80 00 00 8D DF') # -17.2, should be 1

# cmd = bytes.fromhex("55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 C1 89 99 9A 6C 6F" ) # -27.3, should be -17.2

# cmd = bytes.fromhex("55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 41 20 00 00 5D 24") # -12.2, should be 10

# cmd = bytes.fromhex("55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 41 A0 00 00 B1 28") # -6.7, should be 20

# cmd = bytes.fromhex("55FF 0510 0000 0AEC 0104 0701 0108 41F0 0000 52AB") # -1.1, should be 30

cmd = bytes.fromhex("55 FF 05 10 00 00 0A EC 01 04 07 01 01 08 42 00 00 00 AB 02") # 0, should be 32 ### OH SHIT IT'S CELSIUS

# cmd = bytes.fromhex(" 55 FF        05             10                00           00 0A                 EC      01 04     07 01      01 08   42 0C 00 00         08 A7")             # 1.7, should be 35
#                     |preamble|Frame type (?)|dest. addr (zone)|source addr.|length (MSB first)(10)|header crc|        ^parameter^           ^ iEEE 754 ^   |data crc (LSB first)|   
#                                  
#                       BACnet Data Expecting Reply?
#                        
# cmd = bytes.fromhex("55 FF    05  10   00 00 0A EC 01 04 07 01 01 08 42 20 00 00 90 01") # 4.4, should be 40

# cmd = bytes.fromhex("55FF 0510 0000 0AEC 0104 07 01 01 08 42 48 00 00 1F C2") # 10, should be 50

# cmd = bytes.fromhex("55FF 0510 0000 06E8 0103 0107 0101 8776")


import serial


myserial = serial.Serial(port="COM7", baudrate=38400, timeout=1)

myserial.flush()
myserial.write(cmd)
res = myserial.read_until(b"\n")
print(res)
res_str = str(res.hex())
print([res_str[i:i+2] for i in range(0, len(res_str), 2)])

# for element in res_str.split("\\x"):
#     try:
#         print(bytes.fromhex(element))
#     except:
#         pass


# myserial.close()

# Baud Rate=38400
# WordLength=8
# StopBits=1 stop bit
# Parity=No parity
# EofChar=0x0
# ErrorChar=0x0
# BreakChar=0x0
# EventChar=0x0
# XonChar=0x11
# XoffChar=0x13
# ControlHandShake=1
# FlowReplace=64
# XonLimit=2048
# XoffLimit=512
# ReadIntervalTimeout=4294967295
# ReadTotalTimeoutMultiplier=0
# ReadTotalTimeoutConstant=0
# WriteTotalTimeoutMultiplier=0
# WriteTotalTimeoutConstant=0

# print("established serial connection")
# baudrates = myserial.BAUDRATES
# myserial.close()

# for baud in baudrates:
#     print(baud)
#     myserial = serial.Serial(port="COM7", baudrate=baud, timeout=1)
#     myserial.flush()
#     myserial.write(cmd)
#     res = myserial.read_until()
#     print(res)
#     myserial.close()
#     print(baud)
#     myserial = serial.Serial(port="COM7", baudrate=baud, timeout=1)
#     myserial.flush()
#     myserial.write(cmd)
#     res = myserial.read_until()
#     print(res)
#     try:
#         res = res.hex()
#     except:
#         print("could not decode")
#     else:
#         print('decoded?')
#         print(res)   
#     # print(res)
#     # print(bytes.fromhex(res).decode('utf-8'))
#     myserial.close()
#     print("---")