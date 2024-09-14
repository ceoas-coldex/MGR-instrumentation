import serial

def mantissa_to_int(mantissa_str):
    # Variable to make a count of negative power of 2
    power_count = -1
    
    # variable to store float value of mantissa
    mantissa_int = 0
	
    # Iterate through binary number
    for i in mantissa_str:
        mantissa_int += (int(i)*pow(2, power_count))
        power_count -= 1
		
    return (mantissa_int + 1)

def hex_to_ieee754_dec(hex_str:str):
    # Convert to integer, keeping its hex representation
    ieee_32_hex = int(hex_str, 16)
	# Convert to 32 bit binary
    ieee_32 = f'{ieee_32_hex:0>32b}'

    # The first bit is the sign bit
    sign_bit = int(ieee_32[0])

    # The next 8 bits are exponent bias in biased form
    exponent_bias = int(ieee_32[1:9], 2)
    # Subtract 127 to get the unbiased form
    exponent_unbias = exponent_bias - 127

    # Next 23 bits are the mantissa
    mantissa_str = ieee_32[9:]
    mantissa_int = mantissa_to_int(mantissa_str)

    # Finally, convert to decimal
    dec = pow(-1, sign_bit) * mantissa_int * pow(2, exponent_unbias)

    return dec


ser = serial.Serial(port="COM3", baudrate=38400, timeout=5)
print("connected to COM3 with baud 38400")

GET_MEAS = b':06030401210120\r\n'
# GET_MEAS = b'0x100201800504012101201003'

GET_SETPOINT = b':06030401210121\r\n'

SEND_SETPOINT = b'06030101213E80\r\n'

GET_TEMP = b':06800421472147\r\n'

dec_1_float = b'3F800000'

ser.write(GET_TEMP)

response = ser.read_until(b'\r\n')
response = response.decode()

print(response)

response_hex = int(response[11:], 16)

print(response[11:])
print(dec_1_float)

print(hex_to_ieee754_dec(response[11:]))



