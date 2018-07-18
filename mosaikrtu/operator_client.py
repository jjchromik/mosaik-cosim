import threading
from simpy.io import select as backend
from simpy.io.http import Client


class operator_client(threading.Thread):

    """
    Client for communication with the operator tools server.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.env = backend.Environment()
        addr = ('127.0.0.1', 12500)
        self.sock = backend.TCPSocket.connection(self.env, addr)
        self.client = Client(self.sock)
        self.sock.sock.setblocking(True)

    def run(self):
        """
        Runs the client thread.
        """
        self.env.run()

    def send_msg(self, msg):
        """
        Sends a message to the server and returns the answer.
        :param msg: message to send
        :return: answer from the server
        """
        self.sock.write(bytes(msg, 'utf-8'))
        answer = self.sock.sock.recv(1024)
        ans = answer.decode()
        return ans
