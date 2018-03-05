import threading
import json
from simpy.io import select as backend
from simpy.io.http import Client


class worker_web_client(threading.Thread):

    """
    TCP Client for communicating with the webserver.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.env = backend.Environment()
        addr = ('127.0.0.1', 8000)
        self.sock = backend.TCPSocket.connection(self.env, addr)
        self.client = Client(self.sock)
        self.client.get(path="/rtu_worker")

    def run(self):
        """
        Runs the client.
        """
        self.env.run()

    def highlight(self, target):
        """
        Sends a message to the server to highlight the given target in the web visualisation.
        :param target: target to highlight
        """
        msg = json.dumps([target])
        self.sock.write(bytes(msg, 'utf-8'))
