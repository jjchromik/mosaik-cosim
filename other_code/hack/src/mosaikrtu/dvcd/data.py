from pymodbus3.datastore import ModbusSequentialDataBlock
from pymodbus3.datastore import ModbusSlaveContext


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

    def get(self, _type, address, count):
        """
        Generic 'get' method for LockedDataBlock. Figures out the underlying method to call according to _type.
        :param _type: Type of modbus register ('co', 'di', 'hr', 'ir')
        :param address: Index of the register
        :param count: The amount of registers to get sequentially
        :return: Value of requested index(es).
        """
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

    def set(self, _type, address, values):
        """
        Generic 'set' method for LockedDataBlock. Figures out the underlying method to call according to _type.
        :param _type: Type of modbus register ('co', 'di', 'hr', 'ir')
        :param address: Index of the register
        :param values: Value(s) to set the addresses to.
        :return: Value of requested address for type.
        """
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
