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

from time import sleep
import os
from datetime import datetime

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

FILENAME = 'rtu_5_log.csv'

try: 
  os.remove(FILENAME)
except OSError:
  pass

print("*"*30)
print("SCADA server, reading the values of switch states, current and voltage readings")
print("*"*30+"\n\n")

fd = open(FILENAME, 'w+')
csvrow = "timestamp;switch19;switch24;switch25;switch36;voltageb5;current19;current24;current25;current36\n"
fd.write(csvrow)
i=0
while i<10000:
  result  = client.read_coils(0, 4,  unit=1)
  ts = str(datetime.now())
  print("*"*10+" SWITCHES "+"*"*10)
  switches = [result.bits[0], result.bits[1], result.bits[2], result.bits[3]]
  print("Switch branch 19: {}\nSwitch branch 24: {}\nSwitch branch 25: {}\nSwitch branch 36: {}".format(switches[0], switches[1], switches[2], switches[3]))
  # Voltage and current
  address = 12
  count   = 20
  result  = client.read_holding_registers(address, count,  unit=1)
  decoder = BinaryPayloadDecoder.from_registers(result.registers, endian=Endian.Big)
  print("*"*10+" VOLTAGE "+"*"*10)
  voltage = decoder.decode_64bit_float()
  current = [decoder.decode_64bit_float(),
	decoder.decode_64bit_float(),
	decoder.decode_64bit_float(),
	decoder.decode_64bit_float()]
  address = 50
  count   = 4
  result  = client.read_holding_registers(address, count,  unit=1)
  decoder = BinaryPayloadDecoder.from_registers(result.registers, endian=Endian.Big)
  trafo = decoder.decode_64bit_float()
  print("Voltage bus b5: {}\n".format(voltage)+"*"*10+" CURRENTS "+"*"*10+"\nCurrent line 19: {}\nCurrent line 24: {}\nCurrent line 25: {}\nCurrent line 36: {}".format(current[0], current[1], current[2], current[3]))
  print("*"*10+" TRAFO "+"*"*10)
  print("Transformer tap position: {}".format(trafo))
  print("*"*30+"\n")
  csvrow = ts+";"+str(switches[0])+";"+str(switches[1])+";"+str(switches[2])+";"+str(switches[3])+";"+str(voltage)+";"+str(current[0])+";"+str(current[1])+";"+str(current[2])+";"+str(current[3])+"\n"
  fd.write(csvrow)
  sleep(1)
  i=i+1
fd.close()
#---------------------------------------------------------------------------# 
# close the client
#---------------------------------------------------------------------------# 
client.close()
