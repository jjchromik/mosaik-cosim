from collections import Callable
import pprint

class Singleton(object):
    """
    Singleton base class
    http://mail.python.org/pipermail/python-list/2007-July/450681.html
    """
    def __new__(cls, *args, **kwargs):
        """ Create a new instance
        """
        if '_inst' not in vars(cls):
            cls._inst = object.__new__(cls)
        return cls._inst

def default(value):
    """
    Given a python object, return the default value
    of that object.
    :param value: The value to get the default of
    :returns: The default value
    """
    return type(value)()


def dict_property(store, index):
    """ Helper to create class properties from a dictionary.
    Basically this allows you to remove a lot of possible
    boilerplate code.
    :param store: The store store to pull from
    :param index: The index into the store to close over
    :returns: An initialized property set
    """
    if isinstance(store, Callable):
        getter = lambda self: store(self)[index]
        setter = lambda self, value: store(self).__setitem__(index, value)
    elif isinstance(store, str):
        getter = lambda self: self.__getattribute__(store)[index]
        setter = lambda self, value:\
            self.__getattribute__(store).__setitem__(index, value)
    else:
        getter = lambda self: store[index]
        setter = lambda self, value: store.__setitem__(index, value)

    return property(getter, setter)

class ModbusCountersHandler(object):
    """
    This is a helper class to simplify the properties for the counters::
    0x0B  1  Return Bus Message Count
             Quantity of messages that the remote
             device has detected on the communications system since its
             last restart, clear counters operation, or power-up.  Messages
             with bad CRC are not taken into account.
    0x0C  2  Return Bus Communication Error Count
             Quantity of CRC errors encountered by the remote device since its
             last restart, clear counters operation, or power-up.  In case of
             an error detected on the character level, (overrun, parity error),
             or in case of a message length < 3 bytes, the receiving device is
             not able to calculate the CRC. In such cases, this counter is
             also incremented.
    0x0D  3  Return Slave Exception Error Count
             Quantity of MODBUS exception error detected by the remote device
             since its last restart, clear counters operation, or power-up.  It
             comprises also the error detected in broadcast messages even if an
             exception message is not returned in this case.
             Exception errors are described and listed in "MODBUS Application
             Protocol Specification" document.
    0xOE  4  Return Slave Message Count
             Quantity of messages addressed to the remote device,  including
             broadcast messages, that the remote device has processed since its
             last restart, clear counters operation, or power-up.
    0x0F  5  Return Slave No Response Count
             Quantity of messages received by the remote device for which it
             returned no response (neither a normal response nor an exception
             response), since its last restart, clear counters operation, or
             power-up. Then, this counter counts the number of broadcast
             messages it has received.
    0x10  6  Return Slave NAK Count
             Quantity of messages addressed to the remote device for which it
             returned a Negative Acknowledge (NAK) exception response, since
             its last restart, clear counters operation, or power-up. Exception
             responses are described and listed in "MODBUS Application Protocol
             Specification" document.
    0x11  7  Return Slave Busy Count
             Quantity of messages addressed to the remote device for which it
             returned a Slave Device Busy exception response, since its last
             restart, clear counters operation, or power-up. Exception
             responses are described and listed in "MODBUS Application
             Protocol Specification" document.
    0x12  8  Return Bus Character Overrun Count
             Quantity of messages addressed to the remote device that it could
             not handle due to a character overrun condition, since its last
             restart, clear counters operation, or power-up. A character
             overrun is caused by data characters arriving at the port faster
             than they can.
    .. note:: I threw the event counter in here for convenience
    """
    __data = dict([(i, 0x0000) for i in range(9)])
    __names = [
        'BusMessage',
        'BusCommunicationError',
        'SlaveExceptionError',
        'SlaveMessage',
        'SlaveNoResponse',
        'SlaveNAK',
        'SlaveBusy',
        'BusCharacterOverrun'
        'Event '
    ]

    def __iter__(self):
        """ Iterate over the device counters
        :returns: An iterator of the device counters
        """
        return zip(self.__names, self.__data.values())

    def update(self, values):
        """ Update the values of this identity
        using another identify as the value
        :param values: The value to copy values from
        """
        for k, v in values.items():
            v += self.__getattribute__(k)
            self.__setattr__(k, v)

    def reset(self):
        """ This clears all of the system counters
        """
        self.__data = dict([(i, 0x0000) for i in range(9)])

    def summary(self):
        """ Returns a summary of the counters current status
        :returns: A byte with each bit representing each counter
        """
        count, result = 0x01, 0x00
        for i in self.__data.values():
            if i != 0x00:
                result |= count
            count <<= 1
        return result

    # region Properties

    BusMessage = dict_property(lambda s: s.__data, 0)
    BusCommunicationError = dict_property(lambda s: s.__data, 1)
    BusExceptionError = dict_property(lambda s: s.__data, 2)
    SlaveMessage = dict_property(lambda s: s.__data, 3)
    SlaveNoResponse = dict_property(lambda s: s.__data, 4)
    SlaveNAK = dict_property(lambda s: s.__data, 5)
    SlaveBusy = dict_property(lambda s: s.__data, 6)
    BusCharacterOverrun = dict_property(lambda s: s.__data, 7)
    Event = dict_property(lambda s: s.__data, 8)

    # endregion

    pass

class ModbusDeviceIdentification(object):
    """
    This is used to supply the device identification
    for the readDeviceIdentification function
    For more information read section 6.21 of the modbus
    application protocol.
    """
    __data = {
        0x00: '',  # VendorName
        0x01: '',  # ProductCode
        0x02: '',  # MajorMinorRevision
        0x03: '',  # VendorUrl
        0x04: '',  # ProductName
        0x05: '',  # ModelName
        0x06: '',  # UserApplicationName
        0x07: '',  # reserved
        0x08: '',  # reserved
        # 0x80 -> 0xFF are private
    }

    __names = [
        'VendorName',
        'ProductCode',
        'MajorMinorRevision',
        'VendorUrl',
        'ProductName',
        'ModelName',
        'UserApplicationName',
    ]

    def __init__(self, info=None):
        """
        Initialize the datastore with the elements you need.
        (note acceptable range is [0x00-0x06,0x80-0xFF] inclusive)
        :param info: A dictionary of {int:string} of values
        """
        if isinstance(info, dict):
            for key in info:
                if (0x06 >= key >= 0x00) or (0x80 > key > 0x08):
                    self.__data[key] = info[key]

    def __iter__(self):
        """ Iterate over the device information
        :returns: An iterator of the device information
        """
        return self.__data.items()

    def summary(self):
        """ Return a summary of the main items
        :returns: An dictionary of the main items
        """
        return dict(zip(self.__names, self.__data.values()))

    def update(self, value):
        """ Update the values of this identity
        using another identify as the value
        :param value: The value to copy values from
        """
        self.__data.update(value)

    def __setitem__(self, key, value):
        """ Wrapper used to access the device information
        :param key: The register to set
        :param value: The new value for referenced register
        """
        if key not in [0x07, 0x08]:
            self.__data[key] = value

    def __getitem__(self, key):
        """ Wrapper used to access the device information
        :param key: The register to read
        """
        return self.__data.setdefault(key, '')

    def __str__(self):
        """ Build a representation of the device
        :returns: A string representation of the device
        """
        return 'DeviceIdentity'

    # region Properties

    VendorName = dict_property(lambda s: s.__data, 0)
    ProductCode = dict_property(lambda s: s.__data, 1)
    MajorMinorRevision = dict_property(lambda s: s.__data, 2)
    VendorUrl = dict_property(lambda s: s.__data, 3)
    ProductName = dict_property(lambda s: s.__data, 4)
    ModelName = dict_property(lambda s: s.__data, 5)
    UserApplicationName = dict_property(lambda s: s.__data, 6)

    # endregion

    pass


class ModbusPlusStatistics(object):
    """
    This is used to maintain the current modbus plus statistics count. As of
    right now this is simply a stub to complete the modbus implementation.
    For more information, see the modbus implementation guide page 87.
    """

    __data = {
        'node_type_id': [0x00] * 2,  # 00
        'software_version_number': [0x00] * 2,  # 01
        'network_address': [0x00] * 2,  # 02
        'mac_state_variable': [0x00] * 2,  # 03
        'peer_status_code': [0x00] * 2,  # 04
        'token_pass_counter': [0x00] * 2,  # 05
        'token_rotation_time': [0x00] * 2,  # 06

        'program_master_token_failed': [0x00],  # 07 hi
        'data_master_token_failed': [0x00],  # 07 lo
        'program_master_token_owner': [0x00],  # 08 hi
        'data_master_token_owner': [0x00],  # 08 lo
        'program_slave_token_owner': [0x00],  # 09 hi
        'data_slave_token_owner': [0x00],  # 09 lo
        'data_slave_command_transfer': [0x00],  # 10 hi
        '__unused_10_lowbit': [0x00],  # 10 lo

        'program_slave_command_transfer': [0x00],  # 11 hi
        'program_master_rsp_transfer': [0x00],  # 11 lo
        'program_slave_auto_logout': [0x00],  # 12 hi
        'program_master_connect_status': [0x00],  # 12 lo
        'receive_buffer_dma_overrun': [0x00],  # 13 hi
        'pretransmit_deferral_error': [0x00],  # 13 lo
        'frame_size_error': [0x00],  # 14 hi
        'repeated_command_received': [0x00],  # 14 lo
        'receiver_alignment_error': [0x00],  # 15 hi
        'receiver_collision_abort_error': [0x00],  # 15 lo
        'bad_packet_length_error': [0x00],  # 16 hi
        'receiver_crc_error': [0x00],  # 16 lo
        'transmit_buffer_dma_underrun': [0x00],  # 17 hi
        'bad_link_address_error': [0x00],  # 17 lo

        'bad_mac_function_code_error': [0x00],  # 18 hi
        'internal_packet_length_error': [0x00],  # 18 lo
        'communication_failed_error': [0x00],  # 19 hi
        'communication_retries': [0x00],  # 19 lo
        'no_response_error': [0x00],  # 20 hi
        'good_receive_packet': [0x00],  # 20 lo
        'unexpected_path_error': [0x00],  # 21 hi
        'exception_response_error': [0x00],  # 21 lo
        'forgotten_transaction_error': [0x00],  # 22 hi
        'unexpected_response_error': [0x00],  # 22 lo

        'active_station_bit_map': [0x00] * 8,  # 23-26
        'token_station_bit_map': [0x00] * 8,  # 27-30
        'global_data_bit_map': [0x00] * 8,  # 31-34
        'receive_buffer_use_bit_map': [0x00] * 8,  # 35-37
        'data_master_output_path': [0x00] * 8,  # 38-41
        'data_slave_input_path': [0x00] * 8,  # 42-45
        'program_master_output_path': [0x00] * 8,  # 46-49
        'program_slave_input_path': [0x00] * 8,  # 50-53
    }

    def __init__(self):
        """
        Initialize the modbus plus statistics with the default
        information.
        """
        self.reset()

    def __iter__(self):
        """ Iterate over the statistics
        :returns: An iterator of the modbus plus statistics
        """
        return self.__data.items()

    def reset(self):
        """ This clears all of the modbus plus statistics
        """
        for key in self.__data:
            self.__data[key] = [0x00] * len(self.__data[key])

    def summary(self):
        """ Returns a summary of the modbus plus statistics
        :returns: 54 16-bit words representing the status
        """
        return self.__data.values()

    def encode(self):
        """ Returns a summary of the modbus plus statistics
        :returns: 54 16-bit words representing the status
        """
        total, values = [], sum(self.__data.values(), [])
        for c in range(0, len(values), 2):
            total.append((values[c] << 8) | values[c+1])
        return total


class ModbusControlBlock(Singleton):
    """
    This is a global singleton that controls all system information
    All activity should be logged here and all diagnostic requests
    should come from here.
    """

    __mode = 'ASCII'
    __diagnostic = [False] * 16
    __instance = None
    __listen_only = False
    __delimiter = '\r'
    __counters = ModbusCountersHandler()
    __identity = ModbusDeviceIdentification()
    __plus = ModbusPlusStatistics()
    __events = []

    # region Magic

    def __str__(self):
        """ Build a representation of the control block
        :returns: A string representation of the control block
        """
        return 'ModbusControl'

    def __iter__(self):
        """ Iterate over the device counters
        :returns: An iterator of the device counters
        """
        return self.__counters.__iter__()

    # endregion

    # region Events

    def add_event(self, event):
        """ Adds a new event to the event log
        :param event: A new event to add to the log
        """
        self.__events.insert(0, event)
        self.__events = self.__events[0:64]  # chomp to 64 entries
        self.Counter.Event += 1

    def get_event(self):
        """ Returns an encoded collection of the event log.
        :returns: The encoded events packet
        """
        events = [event.encode() for event in self.__events]
        return b''.join(events)

    def clear_events(self):
        """ Clears the current list of events
        """
        self.__events = []

    # endregion

    # region Other Properties

    Identity = property(lambda self: self.__identity)
    Counter = property(lambda self: self.__counters)
    Events = property(lambda self: self.__events)
    Plus = property(lambda self: self.__plus)

    def reset(self):
        """ This clears all of the system counters and the
            diagnostic register
        """
        self.__events = []
        self.__counters.reset()
        self.__diagnostic = [False] * 16

    # endregion

    # region Listen Properties

    def _set_listen_only(self, value):
        """ This toggles the listen only status
        :param value: The value to set the listen status to
        """
        self.__listen_only = bool(value)

    ListenOnly = property(lambda self: self.__listen_only, _set_listen_only)

    # endregion

    # region Mode Properties

    def _set_mode(self, mode):
        """ This toggles the current serial mode
        :param mode: The data transfer method in (RTU, ASCII)
        """
        if mode in ('ASCII', 'RTU'):
            self.__mode = mode

    Mode = property(lambda self: self.__mode, _set_mode)

    # endregion

    # region Delimiter Properties

    def _set_delimiter(self, char):
        """ This changes the serial delimiter character
        :param char: The new serial delimiter character
        """
        if isinstance(char, str):
            self.__delimiter = char.encode()
        if isinstance(char, bytes):
            self.__delimiter = char
        elif isinstance(char, int):
            self.__delimiter = struct.pack('B', char)

    Delimiter = property(lambda self: self.__delimiter, _set_delimiter)

    # endregion

    # region Diagnostic Properties

    def set_diagnostic(self, mapping):
        """ This sets the value in the diagnostic register
        :param mapping: Dictionary of key:value pairs to set
        """
        for entry in mapping.items():
            if 0 <= entry[0] < len(self.__diagnostic):
                self.__diagnostic[entry[0]] = (entry[1] != 0)

    def get_diagnostic(self, bit):
        """ This gets the value in the diagnostic register
        :param bit: The bit to get
        :returns: The current value of the requested bit
        """
        if (bit is not None) and 0 <= bit < len(self.__diagnostic):
            return self.__diagnostic[bit]
        return None

    def get_diagnostic_register(self):
        """ This gets the entire diagnostic register
        :returns: The diagnostic register collection
        """
        return self.__diagnostic

    # endregion

    pass

class ModbusDeviceIdentification(object):
    """
    This is used to supply the device identification
    for the readDeviceIdentification function
    For more information read section 6.21 of the modbus
    application protocol.
    """
    __data = {
        0x00: '',  # VendorName
        0x01: '',  # ProductCode
        0x02: '',  # MajorMinorRevision
        0x03: '',  # VendorUrl
        0x04: '',  # ProductName
        0x05: '',  # ModelName
        0x06: '',  # UserApplicationName
        0x07: '',  # reserved
        0x08: '',  # reserved
        # 0x80 -> 0xFF are private
    }

    __names = [
        'VendorName',
        'ProductCode',
        'MajorMinorRevision',
        'VendorUrl',
        'ProductName',
        'ModelName',
        'UserApplicationName',
    ]

    def __init__(self, info=None):
        """
        Initialize the datastore with the elements you need.
        (note acceptable range is [0x00-0x06,0x80-0xFF] inclusive)
        :param info: A dictionary of {int:string} of values
        """
        if isinstance(info, dict):
            for key in info:
                if (0x06 >= key >= 0x00) or (0x80 > key > 0x08):
                    self.__data[key] = info[key]

    def __iter__(self):
        """ Iterate over the device information
        :returns: An iterator of the device information
        """
        return iter(self.__data.items())  # STYSIA added iter()

    def summary(self):
        """ Return a summary of the main items
        :returns: An dictionary of the main items
        """
        return dict(zip(self.__names, self.__data.values()))

    def update(self, value):
        """ Update the values of this identity
        using another identify as the value
        :param value: The value to copy values from
        """
        self.__data.update(value)

    def __setitem__(self, key, value):
        """ Wrapper used to access the device information
        :param key: The register to set
        :param value: The new value for referenced register
        """
        if key not in [0x07, 0x08]:
            self.__data[key] = value

    def __getitem__(self, key):
        """ Wrapper used to access the device information
        :param key: The register to read
        """
        return self.__data.setdefault(key, '')

    def __str__(self):
        """ Build a representation of the device
        :returns: A string representation of the device
        """
        return 'DeviceIdentity'

    # region Properties

    VendorName = dict_property(lambda s: s.__data, 0)
    ProductCode = dict_property(lambda s: s.__data, 1)
    MajorMinorRevision = dict_property(lambda s: s.__data, 2)
    VendorUrl = dict_property(lambda s: s.__data, 3)
    ProductName = dict_property(lambda s: s.__data, 4)
    ModelName = dict_property(lambda s: s.__data, 5)
    UserApplicationName = dict_property(lambda s: s.__data, 6)

    # endregion

    pass


if __name__ == '__main__':
    pp = pprint.PrettyPrinter(indent=4)
    identity_src={'code': u'conf/rtu_status.py', 'ip': u'localhost', 'label': u'Local substation', 'registers': {u'max_current1': [u'ir', 0, [u'98']], u'max_current2': [u'ir', 1, [u'99']], u'max_current3': [u'ir', 2, [u'95']], u'switch3': [u'co', 2, [u'1']], u'switch2': [u'co', 1, [u'1']], u'switch1': [u'co', 0, [u'1']], u'current1': [u'hr', 0, [u'-1']], u'current3': [u'hr', 2, [u'-1']], u'current2': [u'hr', 1, [u'-1']]}, 'port': 12502, 'identity': {'productcode': u'PSS', 'modelname': u'PSS 1.0', 'vendorurl': u'https://www.utwente.nl', 'versionmajor': u'0', 'versionminor': u'5', 'productname': u'PoorSecuritySubstation', 'vendorname': u'UTwente'}}
    identity_src=identity_src["identity"]

    print(identity_src["vendorname"])
    control = ModbusControlBlock()

    identity = ModbusDeviceIdentification()
    identity.VendorName = identity_src["vendorname"]
    identity.ProductCode = identity_src["productcode"]
    identity.VendorUrl = identity_src["vendorurl"]
    identity.ProductName = identity_src["productname"]
    identity.ModelName = identity_src["modelname"]
    identity.MajorMinorRevision = '0.3'
    
    if isinstance(identity, ModbusDeviceIdentification):
        control.Identity.update(identity)
    pp.pprint(identity)
    pp.pprint(control)