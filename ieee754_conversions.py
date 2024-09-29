import struct
import numpy as np

def from_bytes(b):
    return struct.unpack('!f', b)[0]

def dec_from_hex(h):
    return from_bytes(bytes.fromhex(h))

def from_bin(b):
    return struct.unpack('!f', int(b, 2).to_bytes(4, byteorder='big'))[0]

def to_bytes(f):
    return struct.pack('!f', f)

def dec_to_hex(f):
    return to_bytes(f).hex()

def to_bin(f):
    return '{:032b}'.format(struct.unpack('>I', struct.pack('!f', f))[0])

if __name__ == "__main__":
    assert dec_from_hex('c4725c44') == -969.441650390625
    assert from_bin('11000100011100100101110001000100') == -969.441650390625
    assert from_bytes(b'\xc4r\\D') == -969.441650390625
    assert dec_to_hex(-969.441650390625) == 'c4725c44'
    assert to_bin(-969.441650390625) == '11000100011100100101110001000100'
    assert to_bytes(-969.441650390625) == b'\xc4r\\D'

    test_list = np.linspace(0, 10, 32)
    print(test_list)

    result_list = []
    for num in test_list:
        hex_rep = dec_to_hex(num)
        dec_rep = dec_from_hex(hex_rep)
        result_list.append(dec_rep)
    
    print(result_list)
