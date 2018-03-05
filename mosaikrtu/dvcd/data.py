from pymodbus3.datastore import ModbusSequentialDataBlock
from pymodbus3.datastore import ModbusSlaveContext
from pymodbus3.payload import BinaryPayloadBuilder
from pymodbus3.payload import BinaryPayloadDecoder
from pymodbus3.constants import Endian

# logging options
import logging
logging.basicConfig()
log = logging.getLogger('datablock')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)



class DataBlock(object):
    """
    Not locked at the moment! =)

    Locking Datablock.
    Can't be simultaniously read from and/or written to. Threads beyond the first would get in line.
    """
    def __init__(self):
        self.di = ModbusSequentialDataBlock(0x00, [0]*0xFF)
        self.co = ModbusSequentialDataBlock(0x00, [0]*0xFF)
        self.hr = ModbusSequentialDataBlock(0x00, [0]*0xFF)
        self.ir = ModbusSequentialDataBlock(0x00, [0]*0xFF)

        self.store = ModbusSlaveContext(
            di=self.di,  # Single Byte, Read-Only
            co=self.co,  # Single Byte, Read-Write
            hr=self.hr,  # 16-Bit Word, Read-Only
            ir=self.ir)  # 16-Bit Word, Read-Write

    def get(self, _type, address, count, _datatype=None): # get == Decoder
        """
        Generic 'get' method for LockedDataBlock. Figures out the underlying method to call according to _type.
        :param _type: Type of modbus register ('co', 'di', 'hr', 'ir')
        :param address: Index of the register
        :param count: The amount of registers to get sequentially
        :return: Value of requested index(es).
        """

        if _datatype == None:
            #log.debug("Retrieving a None type")
            if _type == "di":
                return self._get_di(address, count)
            elif _type == "co":
                return self._get_co(address, count)
            elif _type == "hr":
                return self._get_hr(address, count)
            elif _type == "ir":
                return self._get_ir(address, count)
            else:
                print("t: {}   a: {}   c: {}")
                raise ValueError
        elif _datatype == 'bool':
            if _type == "di":
                values = self._get_di(address, count)
            elif _type == "co":
                values = self._get_co(address, count)
            # elif _type == "hr":
            #     values = self._get_hr(address, count)
            # elif _type == "ir":
            #     values = self._get_ir(address, count)
            else:
                print("t: {}   a: {}   c: {}")
                raise ValueError
            decoder = BinaryPayloadDecoder.from_coils(values.bits, endian=Endian.Big)
            return decoder.decode_bits()
        else:
            if _type == "hr":
                values = self._get_hr(address, count)
            elif _type == "ir":
                values = self._get_ir(address, count)
            else:
                print("t: {}   a: {}   c: {}")
                raise ValueError
            if _datatype == '32bit_float': # TODO: try for the datatypes you have in the RTU for the mosaik simulation and do it also for set and test
                decoder = BinaryPayloadDecoder.from_registers(values, endian=Endian.Big)
                return decoder.decode_32bit_float()
            elif _datatype == '64bit_float':
                decoder = BinaryPayloadDecoder.from_registers(values, endian=Endian.Big)
                return decoder.decode_64bit_float()

    # def get(self, _type, address, count):#, _datatype=None): # get == Decoder
    #     """
    #     Generic 'get' method for LockedDataBlock. Figures out the underlying method to call according to _type.
    #     :param _type: Type of modbus register ('co', 'di', 'hr', 'ir')
    #     :param address: Index of the register
    #     :param count: The amount of registers to get sequentially
    #     :return: Value of requested index(es).
    #     """
    #     if _type == "di":
    #         return self._get_di(address, count)
    #     elif _type == "co":
    #         return self._get_co(address, count)
    #     elif _type == "hr":
    #         return self._get_hr(address, count)
    #     elif _type == "ir":
    #         return self._get_ir(address, count)
    #     else:
    #         print("t: {}   a: {}   c: {}")
    #         raise ValueError

    def set(self, _type, address, values, _datatype=None):
        """
        Generic 'set' method for LockedDataBlock. Figures out the underlying method to call according to _type.
        :param _type: Type of modbus register ('co', 'di', 'hr', 'ir')
        :param address: Index of the register
        :param values: Value(s) to set the addresses to.
        :return: Value of requested address for type.
        """
        if _datatype == None:
            #print("Adding a None type")
            if _type == "di":
                self._set_di(address, values)
            elif _type == "co":
                self._set_co(address, values)
            elif _type == "hr":
                self._set_hr(address, values)
            elif _type == "ir":
                self._set_ir(address, values)
            else:
                print("t: {}   a: {}   v: {}")
                raise ValueError
        elif _datatype == 'bool':
            print("Adding a bool type")
            builder = BinaryPayloadBuilder(endian=Endian.Big)
            builder.add_bits(values)
            payload = unpack_bitstring(builder.to_string())
            if _type == "di":
                self._set_di(address, payload)
            elif _type == "co":
                self._set_co(address, payload)
        else:
            builder = BinaryPayloadBuilder(endian=Endian.Big)
            if _datatype == '32bit_float':  # TODO: try for the datatypes you have in the RTU for the mosaik simulation and do it also for set and test
                builder.add_32bit_float(values)
            elif _datatype == '64bit_float':
                builder.add_64bit_float(values)
            payload = builder.to_registers()
            if _type == "hr":
                self._set_hr(address, payload)
            elif _type == "ir":
                self._set_ir(address, payload)
            else:
                print("t: {}   a: {}   v: {}")
                raise ValueError

    def _get_di(self, address, count):
        values = self.di.get_values(address+1, count)
        return values

    def _set_di(self, address, values):
        self.di.set_values(address+1, values)

    def _get_co(self, address, count):
        values = self.co.get_values(address+1, count)
        return values

    def _set_co(self, address, values):
        self.co.set_values(address+1, values)

    def _get_hr(self, address, count):
        values = self.hr.get_values(address+1, count)
        return values

    def _set_hr(self, address, values):
        self.hr.set_values(address+1, values)

    def _get_ir(self, address, count):
        values = self.ir.get_values(address+1, count)
        return values

    def _set_ir(self, address, values):
        self.ir.set_values(address+1, values)
