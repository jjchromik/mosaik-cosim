from pymodbus3.server.sync import ModbusTcpServer, ModbusSocketFramer
from pymodbus3.device import ModbusDeviceIdentification
from pymodbus3.datastore import ModbusServerContext
import threading
from datetime import datetime
import logging

logging.basicConfig()
log = logging.getLogger('datablock')
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)

class Server(threading.Thread):
    """
    Modbus Server class. Holds a datablock and identity. Serves forever (blocks calling thread).
    """
    def __init__(self, datablock, identity):
        threading.Thread.__init__(self)
        self.do_stop = threading.Event()

        self.ip = None
        self.port = None
        self.id = None

        self.srv = None
        self.context = None
        self.datablock = datablock

        self.framer = ModbusSocketFramer
        self.context = ModbusServerContext(slaves=self.datablock.store, single=True)

        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = identity["vendorname"]
        self.identity.ProductCode = identity["productcode"]
        self.identity.VendorUrl = identity["vendorurl"]
        self.identity.ProductName = identity["productname"]
        self.identity.ModelName = identity["modelname"]
        self.identity.MajorMinorRevision = '0.3'
        #self.identity.Filter = ''

    def run(self):
        """
        Start the server.
        """
        while not self.do_stop.is_set():
            try:
                self.srv = ModbusTcpServer(self.context, self.framer, self.identity, (self.ip, self.port))
                self.srv.allow_reuse_address = True
                self.srv.serve_forever()
            except Exception:
                raise
        print("[*] Server stopping.")

    def verify_request(self, request, client_address):
        print('verify_request(%s, %s)', request, client_address)
        log.warning('     SERVER NEW REQUEST, {}'.format(datetime.now()))
        return socketserver.ThreadingTCPServer.verify_request(self, request, client_address)

    def stop(self):
        """
        Stop the server.
        """
        self.do_stop.set()
        self.srv.server_close()
        self.srv.shutdown()
        print("[*] Stopping server.")
