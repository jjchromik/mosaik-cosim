import threading
import time
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.WARNING)

class Worker(threading.Thread):
    """
    Thread holding the Modbus Client, its Datablock, and its Functions.
    """
    def __init__(self, datablock, code, cache):
        threading.Thread.__init__(self)
        self.cached_val = cache
        self.datablock = datablock
        self.code = code
        self.do_stop = threading.Event()
        #TODO: change max_current reference further to the logic.
        self.max_current={}
        self.max_current["branch_16"] = self.db("hr", 6)
        self.max_current["branch_17"] = self.db("hr", 7)
        self.max_current["branch_16a"] = self.db("hr", 8)

    def run(self):
        """
        Client's endless run-loop. 
        Client reads the new values from the file 
        """

        while not self.do_stop.is_set():
            #start = time.clock()
            #with open(self.code) as f:
            #    code = compile(f.read(), self.code, 'exec')
            #    exec(code)
            time.sleep(1)
        print("[*] Worker stopping.")

    def stop(self):
        """
        Signal the client to stop its run-loop.
        """
        self.do_stop.set()
        print("[*] Worker given stop signal...")

    def db(self, t, i, c=1, dt=None):
        """
        Gets values from the datablock.
        :param t: Register type, from; 'di', 'co', 'hr', 'ir'
        :param i: Index of register.
        :param c: Amount of registers to read.
        :return: List of values.
        """
        log.debug("Read from datablock {}, #{}".format(t, i))
        if c == 1:
            return self.datablock.get(t, i, c, dt)[0]
        return self.datablock.get(t, i, c, dt)

    def to_db(self, t, i, data, dt=None):
        """
        Sets values in the datablock.
        :param t: Register type, from; 'di', 'co', 'hr', 'ir'
        :param i: Index of register.
        :return: List of values.
        """
        self.datablock.set(t, i, data, dt)

    @staticmethod
    def to_float(a, b, c, d):
        import struct
        return struct.unpack("f", "".join(chr(int(i)) for i in (a, b, c, d)))[0]

    @staticmethod
    def from_float(a):
        import struct
        return struct.pack("f", a)
