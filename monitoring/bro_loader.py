import threading
import sys
import os, stat

class bro_loader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.broscript = "startBro.sh"
        self.rootdir = os.path.join("..", "data")
        self.defaultdir = "basic_normal"
        self.conf_file_name = "config.cfg"

    def run(self):
        """
        Starts the simulation.
        """
        os.system("./"+self.broscript)

    def load_config(self):
        """
        Loads a config file into a dict.
        :param dir: directory to pull configuration from
        :param finalload: boolean whether it is the final load for the simulation
        :return: configuration as a dict
        """
        conf = {}
        conf_file = os.path.join(os.getcwd(), "..", "data", self.conf_file_name)
        with open(conf_file) as in_stream:
            for line in in_stream:
                line = line.rstrip()
                key, value = line.split(" ", 1)
                conf[key] = value
        in_stream.close()
        # print(conf)
        return conf

    def write_bro_start(self, config):
    	filename = "./"+self.broscript
        try:
        	os.remove(filename)
        except OSError:
        	pass
        file = open(filename, "w")
        file.write("#!/bin/bash\n") 
        file.write("# Start the Bro monitoring tool\n\n") 
        file.write("/usr/local/bro/bin/bro  -i {} {}".format(config['bro_if'], os.path.join(os.getcwd(), "..", "data", config['bro_policies']))) 
        file.close() 
        st = os.stat(filename)
        os.chmod(filename, st.st_mode | stat.S_IEXEC)

if __name__ == "__main__":
    tl = bro_loader()
    tl.write_bro_start(tl.load_config())
    tl.run()