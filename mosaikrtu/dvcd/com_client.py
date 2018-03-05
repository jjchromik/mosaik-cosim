import threading
import json
from simpy.io import select as backend
from simpy.io.http import Client


class com_client(threading.Thread):

    """
    Client for communication with other rtus over communication server.
    """

    def __init__(self, eid, worker, server):
        threading.Thread.__init__(self)
        self.eid = eid
        self.server = server
        self.worker = worker

    def run(self):
        """
        Registeres this client at the communication server.
        """
        #print("worker client from " + str(self.eid))
        self.server.register(self.eid, self)

    def send(self, target, rq):
        """
        Sends request to communication server.
        :return: answer from server as a dict
        """
        return self.server.handle(self.eid, target, rq)

    def handle(self, rq):
        """
        Handles given request.
        :param rq: request to handle
        :return: result of request
        """
        # print(self.eid + " handle: " + str(rq))
        cmds = rq.split(" ")
        if cmds[0] == "at":
            # checks if rtu is on given branch cmds[1]
            return str(cmds[1] in self.worker.get_branches())
        elif cmds[0] == "Va":
            # gets the value of Va
            return str(self.worker.get_Va())
        return "unknown cmd"

    def broadcast(self, msg):
        """
        Broadcasts a message to all rtus.
        :param msg: message to broadcast
        """
        self.server.broadcast(self.eid, msg)

    def recv(self, src, msg):
        """
        Recives broacasted message from communication server.
        :param src: source of the broadcast
        :param msg: broadcast message
        """
        msg = msg.split(" ")
        # atk means that at least one sensor was marked as untrusted
        if msg[0] == "atk":
            # in case this RTU is adjacent to the attacked RTU we increase it's sensitivity for warnings
            if msg[1] in self.worker.adj_rtus:
                self.worker.warning_value += 5
                self.worker.great_warning_value += 5
                print("RTU " + str(self.worker.eid[0:1] + " warning sensitivity was increased because the adjacent RTU " + msg[1][0:1] + " was attacked."))
        else:
            print(self.eid + " got broadcast \"" +
              str(msg) + "\" from " + str(src))
