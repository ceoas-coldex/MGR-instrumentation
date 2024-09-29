import numpy as np

def mantissa_to_int(mantissa_str):
    """Method to convert the mantissa of the IEEE floating point to its decimal representation"""
    # Variable to be our exponent as we loop through the mantissa
    power = -1
    # Variable to store the decimal value of mantissa
    mantissa = 0
    # Iterate through binary number and convert it from binary
    for i in mantissa_str:
        mantissa += (int(i)*pow(2, power))
        power -= 1
        
    return (mantissa + 1)

def hex_to_ieee754_dec(hex_str:str) -> float:
    """
    Method to convert a hexadecimal string (e.g what is returned from the Bronkhorst) into an IEEE floating point. It's gnarly,
    more details https://www.mimosa.org/ieee-floating-point-format/ and https://www.h-schmidt.net/FloatConverter/IEEE754.html
    
    In short, the IEEE 754 standard formats a floating point as N = 1.F x 2E-127, 
    where N = floating point number, F = fractional part in binary notation, E = exponent in bias 127 representation.

    The hex input corresponds to a 32 bit binary:
            Sign | Exponent  |  Fractional parts of number
            0    | 00000000  |  00000000000000000000000
        Bit: 31   | [30 - 23] |  [22        -         0]

    Args - 
        - hex_str (str, hexadecmial representation of binary string)

    Returns -
        - dec (float, number in decimal notation)
    """
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


def frac_to_binary(decimal_number):
    """Converts the fractional part of a decimal number to binary form

    Args:
        decimal_number (float): Real decimal number

    Returns:
        fraction_string (str): Binary representation of the fractional part of the number
    """
    # Isolate the fractional part from the number
    fraction = decimal_number - int(decimal_number) 
    # Iterate through the fraction, creating a binary string until we run out of fraction
    binary = str()
    for i in range(10):
        # Multiply by 2 for ~binary~ reasons
        fraction *= 2
        # If we're greater than 1, store a 1 and reduce the fraction further
        if fraction >= 1:
            bit = 1
            fraction -= 1
        # Otherwise, store a 0
        else:
            bit = 0
        # Keep track of the bits 
        binary += str(bit)
 
    return binary
 
# Function to get sign bit, exponent bits, and mantissa bits from given decimal number
def dec_to_ieee754_hex(decimal):
    # Determine sign bit of decimal number
    if decimal < 0:
        sign_bit = str(1)
    else:
        sign_bit = str(0)
    # Once we have the sign bit, take the absolute value
    decimal = abs(decimal)
    # Convert integer part of decimal number to binary (e.g 2.5 -> '0b10'), and slice off the
    # first two chars of the string ('0b')
    integer_str = bin(int(decimal))[2:]
    # Convert the fractional part of the real number to binary
    fraction_str = frac_to_binary(decimal)
    # print(integer_str)
    # Grab the first index where the bit is "high" in binary representation
    try:
        index = integer_str.index('1')
        exp_unbiased = len(integer_str) - 1
    except ValueError:
        exp_unbiased = 0
        index = 0

    print(integer_str)
    print(exp_unbiased)
    print("--")

    # print("--")
    # Use the index to find the exponent - we want to reformat the binary number into exponent form, 
    # e.g, turning 10110.1001 into 1.01101001 x 2^4
    # This is exactly the same concept as scientific notation, just in binary
    # exp_unbiased = len(integer_str) - 1
    # Then we bias it by 127, which is just a feature of IEEE754 notation
    exp_biased = exp_unbiased + 127
    exp_str = bin(exp_biased)[2:]
    # Get the mantissa string by adding the integer_str and the fraction_str. 
    # The zeros before the first "high" bit of the integer_str have no significance,
    # so we slice them out
    mantissa_str = integer_str[(index + 1):] + fraction_str
    # Finally, we add zeros at the end of the mantissa string to make it 23 bits long
    mantissa_str += ('0' * (23 - len(mantissa_str)))

    ieee754_binary = sign_bit + exp_str + mantissa_str

    ieee754_hex = ieee754_binary_to_hex(ieee754_binary)
    
    return ieee754_hex

def ieee754_binary_to_hex(ieee754_binary):

    ieee754_hex = hex(int(ieee754_binary,2))[2:]
    if len(ieee754_hex) < 8:
        ieee754_hex = '0' + ieee754_hex
    if len(ieee754_hex) > 8:
        ieee754_hex = ieee754_hex[0:8]

    return ieee754_hex


if __name__ == "__main__":
    test_list = np.linspace(0, 10, 32)
    print(test_list)

    result_list = []
    for num in test_list:
        hex_rep = dec_to_ieee754_hex(num)
        dec_rep = hex_to_ieee754_dec(hex_rep)
        # Printing the ieee 32 representation.
        result_list.append(dec_rep)
    
    print(result_list)