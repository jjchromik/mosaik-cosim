#!/usr/bin/env python3
'''
Pymodbus Payload Building/Decoding Example
--------------------------------------------------------------------------

# Run modbus-payload-server.py or synchronous-server.py to check the behavior
'''
from pymodbus3.constants import Endian
from pymodbus3.payload import BinaryPayloadDecoder
from pymodbus3.payload import BinaryPayloadBuilder
from pymodbus3.client.sync import ModbusTcpClient as ModbusClient

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

#---------------------------------------------------------------------------# 
# We are going to use a simple client to send our requests
#---------------------------------------------------------------------------# 
client = ModbusClient('192.168.33.1', port=10502)
client.connect()

#---------------------------------------------------------------------------# 
# If you need to build a complex message to send, you can use the payload
# builder to simplify the packing logic.
#
# Here we demonstrate packing a random payload layout, unpacked it looks
# like the following:
#
# - a 8 byte string 'abcdefgh'
# - a 32 bit float 22.34
# - a 16 bit unsigned int 0x1234
# - an 8 bit int 0x12
# - an 8 bit bitstring [0,1,0,1,1,0,1,0]
#---------------------------------------------------------------------------# 

#---------------------------------------------------------------------------# 
# If you need to decode a collection of registers in a weird layout, the
# payload decoder can help you as well.
#
# Here we demonstrate decoding a random register layout, unpacked it looks
# like the following:
#
# - a 8 byte string 'abcdefgh'
# - a 32 bit float 22.34
# - a 16 bit unsigned int 0x1234
# - an 8 bit int 0x12
# - an 8 bit bitstring [0,1,0,1,1,0,1,0]
#---------------------------------------------------------------------------# 
address = 28
count   = 4
result  = client.read_holding_registers(address, count,  unit=1)
decoder = BinaryPayloadDecoder.from_registers(result.registers, endian=Endian.Big)
print(decoder.decode_64bit_float())
    #'8int': decoder.decode_8bit_int(),
    #'bits': decoder.decode_bits(),



#---------------------------------------------------------------------------# 
# close the client
#---------------------------------------------------------------------------# 
client.close()
