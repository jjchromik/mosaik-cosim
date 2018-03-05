import threading
from simpy.io import select as backend
from simpy.io.http import Service
import logging
logger = logging.getLogger('server_operator_tools')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class server(threading.Thread):

    """
    Server for communication with MonitoringRTU.
    """

    def __init__(self, op_tools):
        threading.Thread.__init__(self)
        self.op_tools = op_tools
        addr = ('127.0.0.1', 12500)
        self.env = backend.Environment()
        self.sock = backend.TCPSocket.server(self.env, addr)
        self.env.process(self.serve())
        self.service = None
        self.resetting = False

    def run(self):
        """
        Runs the server thread.
        """
        self.env.run()

    def serve(self):
        """
        Servs the incoming request.
        """
        #while True:
        sock = yield self.sock.accept()
        self.service = Service(sock)
        self.env.process(self.handler(self.service))

    def handler(self, service):
        """
        Handles communication requests and answers.
        :param service: service to handle
        """
        try:
            while True:
                msg = yield service.sock.read(amount=1024)
                msg = msg.decode()
                self.service.sock.sock.sendall(bytes(str(self.resetting), 'utf-8'))
                if "isresetting" not in msg:
                    self.op_tools.append_lbl_line(msg)
                elif self.resetting:
                    self.resetting = False
        except ConnectionError:
            logger.warn('operator_server ConnectionError in "Server.handler()"')
        except OSError as e:
            logger.warn('operator_server OSError in "Server.handler()": %s' % e)
        
    def hard_reset(self):
        """
        Prepares server to send hard reset command.
        """
        self.resetting = True