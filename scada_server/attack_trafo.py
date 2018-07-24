#!/usr/bin/env python

#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus3.client.sync import ModbusTcpClient as ModbusClient
from pymodbus3.constants import Endian
from pymodbus3.payload import BinaryPayloadDecoder
from pymodbus3.payload import BinaryPayloadBuilder
from time import sleep
#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
client = ModbusClient('192.168.33.1', port=10502)
client.connect()

#---------------------------------------------------------------------------#
address = 50
trafo_tap = 1
for trafo_tap in [-1, 0, 1, 0, -1, 1, 0]:
	log.debug("*"*25)
	log.debug("One change branch 25")
	log.debug("*"*25)
	log.debug("Read value: ")

	count   = 4
	result  = client.read_holding_registers(address, count,  unit=1)
	decoder = BinaryPayloadDecoder.from_registers(result.registers, endian=Endian.Big)
	trafo = decoder.decode_64bit_float()
	log.debug("Trafo tap value: {}".format(trafo))

	sleep(3)
	log.debug("Write value: {}".format(trafo_tap))
	builder = BinaryPayloadBuilder(endian=Endian.Big)
	builder.add_64bit_float(trafo_tap)
	payload = builder.build()
	result = client.write_registers(address, payload, skip_encode=True, unit=1)

	sleep(3)
	log.debug("Read value: ")
	result  = client.read_holding_registers(address, count,  unit=1)
	decoder = BinaryPayloadDecoder.from_registers(result.registers, endian=Endian.Big)
	trafo = decoder.decode_64bit_float()
	log.debug("Trafo tap value: {}".format(trafo))
	sleep(11)
#log.debug("One change branch 36")
#rq = client.write_coil(3, False, unit=1)


#---------------------------------------------------------------------------# 
# close the client
#---------------------------------------------------------------------------# 
client.close()

