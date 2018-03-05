import threading
from simpy.io import select as backend
from simpy.io.http import Service
import json


class Server(threading.Thread):

    """
    Modbus Server class. Holds a datablock and identity. Serves forever (blocks calling thread).
    """

    def __init__(self, datablock, identity, addr):
        threading.Thread.__init__(self)
        self.do_stop = threading.Event()
        self.id = None
        self.datablock = datablock

        self.env = backend.Environment()
        self.sock = backend.TCPSocket.server(self.env, addr)
        self.env.process(self.serve())

    def run(self):
        """
        Start the server.
        """
        self.env.run()

    def stop(self):
        """
        Stop the server.
        """
        pass

    def serve(self):
        """
        Servs the incoming requests.
        """
        while True:
            sock = yield self.sock.accept()
            service = Service(sock)
            self.env.process(self.handler(service))

    def handler(self, service):
        """
        Handles the communication with the given service.
        :param service: service to handle
        """
        try:
            while True:
                msg = yield service.sock.read(amount=1024)
                msgs = msg.decode()
                attacks = json.loads(msgs)
                if attacks[1] != "none":
                    if attacks[2]:
                        self.datablock.set(
                            'ir', int(attacks[0]), float(attacks[1]))
                    else:
                        self.datablock.set(
                            'hr', int(attacks[0]), float(attacks[1]))
                    #print("set index " + str(attacks[0]) + " to: " + str(attacks[1]))
                else:
                    msg = json.dumps(self.datablock.get(
                        'hr', int(attacks[0]), 1))
                    service.sock.sock.sendall(bytes(msg, 'utf-8'))
        except ConnectionError:
            logger.warn('rtu_server ConnectionError in "Server.handler()"')
        except OSError as e:
            logger.warn('rtu_server OSError in "Server.handler()": %s' % e)
