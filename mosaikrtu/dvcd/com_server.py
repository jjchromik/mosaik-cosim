import threading
from simpy.io import select as backend
from simpy.io.http import Service
import json
import logging

logger = logging.getLogger(__name__)


class com_server(threading.Thread):

    """
    Communication server for rtus.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.rtus = {}

    # def run(self):
        #print("starting server")

    def register(self, eid, worker):
        """
        Registers worker with given eid.
        :param eid: eid of worker
        :param worker: worker to register
        """
        self.rtus.update({eid: worker})
        # print("registered " + str(eid) + ", " + str(worker))

    def handle(self, src, target, rq):
        """
        Handles request from worker client.
        :param src: source of the request
        :param target: target array for the request for being sent to
        :param rq: request
        :return: result dict of request
        """
        res = {}
        if target == 'all':
            target = self.rtus.keys()
        #print("source: " + src + ", target: " + str(target))
        for rtu in target:
            if rtu != src:
                res.update({rtu: self.rtus[rtu].handle(rq)})
        return res

    def broadcast(self, src, msg):
        """
        Broadcasts a message to all rtus.
        :param src: source worker client
        :param msg: message to broadcast
        """
        for rtu in self.rtus:
            self.rtus[rtu].recv(src, msg)
