import threading
import time
import random

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
        self.fail = 0
        self.max_current={}
        self.max_current["branch_16"] = self.db("hr", 0)
        self.max_current["branch_17"] = self.db("hr", 1)
        self.max_current["branch_16a"] = self.db("hr", 2)

    def run(self):
        """
        Client's endless run-loop. 
        Client reads the new values from the file 
        """

        while not self.do_stop.is_set():
            start = time.clock()
            for  measurements in self.cached_val.values():
                if "sensor" in measurements["dev"]:
                    self.to_db(measurements["reg_type"], measurements["index"], measurements["value"][0])
                if "switch" in measurements["dev"]:
                    if measurements["place"] == "branch_16":
                        if (float(self.cached_val["sensor_1-branch_16"]["value"][0]) > 0.6*max_current["branch_16"]) and not self.db("ir", 2):
                            self.to_db("ir", 2, 1)
                            print("Turning the branch_16a ON, because the current increased above 0.6 of max current.")
                        elif (float(self.cached_val["sensor_1-branch_16"]["value"][0]) < 0.3*max_current["branch_16"]) and self.db("ir", 2): 
                            self.to_db("ir", 2, 0)
                            print("Turning the branch_16a OFF, because the current decreased below 0.3 of max current.")
                            ###### Faking a failure ######
                            ## To fake the failure, uncomment the line below ##
                            #self.fail = bool(random.getrandbits(1))
                            if self.fail:
                                self.to_db("ir", 0, 0)
                                print("Turning the branch 16 also OFF to see if this works ")
            time.sleep(0.1)
            #print("[Time Delta: {:3.2f}ms]\r".format((time.clock() - start) * 1000))
        print("[*] Worker stopping.")

    def stop(self):
        """
        Signal the client to stop its run-loop.
        """
        self.do_stop.set()
        print("[*] Worker given stop signal...")

    def db(self, t, i, c=1):
        """
        Gets values from the datablock.
        :param t: Register type, from; 'di', 'co', 'hr', 'ir'
        :param i: Index of register.
        :param c: Amount of registers to read.
        :return: List of values.
        """
        if c == 1:
            return self.datablock.get(t, i, c)[0]
        return self.datablock.get(t, i, c)

    def to_db(self, t, i, data):
        """
        Sets values in the datablock.
        :param t: Register type, from; 'di', 'co', 'hr', 'ir'
        :param i: Index of register.
        :return: List of values.
        """
        self.datablock.set(t, i, data)

    @staticmethod
    def to_float(a, b, c, d):
        import struct
        return struct.unpack("f", "".join(chr(int(i)) for i in (a, b, c, d)))[0]

    @staticmethod
    def from_float(a):
        import struct
        return struct.pack("f", a)
