import threading
import sys
from shutil import copyfile
import os

class topology_loader(threading.Thread):

    """
    Loader for topologies, RTU XML files, attack script and other various stuff.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.rootdir = os.path.join("..", "data")
        self.defaultdir = "basic_normal"
        self.flag = 1
        self.jsonfile = "demo_mv_grid.json"
        self.conf_file_name = "config.cfg"
        self.rt_factor = 0.0
        self.output_rtu_stats = None
        self.recordtimes = 'False'

    def run(self):
        """
        Starts the simulation.
        """
        os.system("./startSimTopo.sh")

    def write_config(self, dir):
        """
        Writes the config file for the simulation.
        :param dir: directory from where to pull the configuration
        """
        default = self.load_config(self.defaultdir)
        dir_conf = self.load_config(dir)
        conf_file = os.path.join(os.getcwd(), self.rootdir, self.conf_file_name)
        with open(conf_file, "w") as out_stream:
            for key in dir_conf:
                if "default" in dir_conf[key]:
                    dir_conf.update({key: default[key]})
                out_stream.write(key + " " + dir_conf[key] + "\n")
        out_stream.close()
    
    def load_config(self, dir, finalload=False):
        """
        Loads a config file into a dict.
        :param dir: directory to pull configuration from
        :param finalload: boolean whether it is the final load for the simulation
        :return: configuration as a dict
        """

        conf = {}
        if finalload == True:
            conf_file = os.path.join(os.getcwd(), "data", self.conf_file_name)
            #print(conf_file)
        else:
            conf_file = os.path.join(os.getcwd(), self.rootdir, dir, self.conf_file_name)
        with open(conf_file) as in_stream:
            for line in in_stream:
                line = line.rstrip()
                key, value = line.split(" ", 1)
                #print(key + ": " + value)
                conf[key] = value
        in_stream.close()
        if finalload != True:
            conf['grid_file'] = os.path.join(dir, conf['grid_name'] + ".json")
            conf['pv_data'] = os.path.join(dir, conf['pv_data'])
            if 'gen_data' in conf: conf['gen_data'] = os.path.join(dir, conf['gen_data'])
            conf['profile_file'] = os.path.join(dir, conf['profile_file'])
            conf['rtu_file'] = os.path.join(dir, conf['rtu_file'])
            conf['attack_script'] = os.path.join(dir, conf['attack_script'])
            conf['rt_factor'] = self.rt_factor
            conf['rtu_stats_output'] = self.output_rtu_stats
            conf['recordtimes'] = self.recordtimes
            if self.flag:
                old_file = os.path.join(os.getcwd(), self.rootdir, self.jsonfile)
                new_file = os.path.join(os.getcwd(), self.rootdir, dir, self.jsonfile)
                copyfile(new_file, old_file)
                self.flag = 0
        return conf

    def get_config(self, dir=None):
        """
        Gets the config dict for the simulation.
        :param dir: directory to pull the config from
        :return: configuration dict
        """
        if dir:
            self.write_config(dir)
            return self.load_config("")
        return self.load_config("", True)

    def get_topos(self):
        """
        Returns an array of all available configurations.
        """
        res = []
        for d in os.listdir(self.rootdir):
            if os.path.isdir(os.path.join(self.rootdir, d)):
                for f in os.listdir(os.path.join(self.rootdir, d)):
                    if ".cfg" in f:
                        res.append(d)
        return res

    def set_sim_conf(self, rt_factor, stats):
        """
        Sets the simulation configuration of real-time factor and wheter to output the sensor data.
        :param rt_factor: real-time factor
        :param stats: boolean whether to output sensor stats
        """
        self.rt_factor = rt_factor
        self.output_rtu_stats = stats

if __name__ == "__main__":
    tl = topology_loader()
    tl.write_config()
    tl.load_config("", tl.conf_file_name)
