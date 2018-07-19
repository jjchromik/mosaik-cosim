# simulator_mosaik.py
"""
Mosaik interface for the example simulator.

"""
import mosaik_api
import os
from datetime import datetime
from mosaikrtu import rtu_model
import logging
logger = logging.getLogger('demo_main')
ch = logging.StreamHandler()
ch.setLevel(logging.WARN)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
from topology_loader.topology_loader import topology_loader
from distutils.util import strtobool

try:
    os.remove('./outputs/readings.csv')
except OSError:
    pass

META = {
    'models': {
        'RTU': {
            'public': True,
            'params': ['rtu_ref'],
            'attrs': ['switchstates'], 
        },
        'sensor': {
            'public': True,
            'params': ['node', 'branch'],
            'attrs': ['I_real', 'I_imag', 'Vm'], 
        },
        'switch': {
            'public': True,
            'params': ['init_status', 'branch'], # read from the file and mark as "on" if line is online. 
            'attrs': ['online'], 
        },        
    },
}


class MonitoringRTU(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.rtu_ref = ""
        self.conf=""
        self.sid = None
        self.data = ""    #Datablock
        self.rtueid = ""
        self._rtus = []
        self.entities = {}  # Maps EIDs to model indices in self.simulator ??
        self._entities = {}
        self._cache = {} 
        self.worker=""
        self.server=""
        topoloader = topology_loader()
        conf = topoloader.get_config()
        global RECORD_TIMES
        RECORD_TIMES = bool(strtobool(conf['recordtimes'].lower()))
        global RTU_STATS_OUTPUT
        RTU_STATS_OUTPUT = bool(strtobool(conf['rtu_stats_output'].lower()))

    def init(self, sid):
        self.sid = sid
        return self.meta

    def create(self, num, model, rtu_ref=None):
        rtu = []
        for i in range(num):
            rtu_idx = len(self._rtus)
            if rtu_ref:
                self.rtu_ref = rtu_ref
                self.conf = rtu_model.load_rtu(self.rtu_ref) # use rtu_model.load_rtu to load the configuration
                self.data = rtu_model.create_datablock(self.conf) # create_datablock should take the dt into account
                self._cache, entities = rtu_model.create_cache(self.conf["registers"])
                self.server = rtu_model.create_server(self.conf, self.data)
                #self.worker = rtu_model.create_worker(self.conf, self.data, self._cache)
                #self.worker.start()
                self.server.start()
            self._rtus.append(rtu)
            children = []
            for eid, attrs in sorted(entities.items()):
                assert eid not in self._entities
                self._entities[eid] = attrs
                if 'node' not in attrs:
                    print("Entity without the node is {}".format(eid))
                    print("Attrs: {}".format(attrs))
                children.append({
                    'eid': eid,
                    'type': attrs['etype'],
                    'node': attrs['node'],
                    'branch': attrs['branch'],
                })
            self.rtueid = rtu_model.make_eid('rtu', rtu_idx)
            rtu.append({
                'eid': self.rtueid, #model.make_eid('grid', grid_idx),
                'type': 'RTU',
                'children': children,
            })
        return rtu

    def step(self, time, inputs):
        commands = {}  # set commands for switches
        switchstates = {}
        src = self.sid +'.'+ self.rtueid # RTUSim-0.0-rtu%
        dest = 'PyPower-0.PyPower'
        commands[src] = {}
        commands[src][dest] = {}

        for s, v in self._cache.items():
            if 'switch' in s or 'transformer' in s:
                if self.data.get(v['reg_type'], v['index'], 1)[0] != v['value']: # TODO: operation on datablock!
                    if RTU_STATS_OUTPUT: 
                        myCsvRow = "{};{};state;{}\n".format(format(datetime.now()),  v['reg_type']+str(v['index']), v['value'])
                        fd = open('./outputs/readings.csv', 'a')
                        fd.write(myCsvRow)
                        fd.close()
                    self._cache[s]['value'] = self.data.get(v['reg_type'], v['index'], 1)[0]
                    switchstates[v['place']] = v['value']

        if bool(switchstates):
            if commands[src][dest] == {}:
                commands[src][dest]['switchstates'] = switchstates
            else:
                commands[src][dest]['switchstates'].update(switchstates)

        for eid, data in inputs.items():
            for attr, values in data.items(): # attr is like I_real etc.
                if attr in ['I_real', 'Vm']:
                    for src, value in values.items():
                        if "grid" in src:
                            continue
                        else:
                            src=src.split("-")[2]
                            dev_id = eid+"-"+src   # dev_id, e.g. sensor_2-node_d1, sensor_2-branch_17, sensor_1-branch_16
                            assert dev_id in self._cache
                            self._cache[dev_id]["value"] = value
                            #print(self.conf['registers'][dev_id][0])
                            # logger.warning("Sensor {} value changed to {} ".format(dev_id, value))
                            #print("Stuff in data.set: {} {} {} {}".format(self.conf['registers'][dev_id][0], self.conf['registers'][dev_id][1], value, self.conf['registers'][dev_id][2]))
                            self.data.set(self.conf['registers'][dev_id][0], self.conf['registers'][dev_id][1], value, self.conf['registers'][dev_id][2])
                            if RTU_STATS_OUTPUT:
                                myCsvRow = "{};{};{};{}\n".format(format(datetime.now()), dev_id, attr, value)
                                fd = open('./outputs/readings.csv', 'a')
                                fd.write(myCsvRow)
                                fd.close()
        if bool(switchstates) and RECORD_TIMES:
            myCsvRow = "{};{};{}\n".format("RTU-API", "Pass the commands to TOPOLOGY", format(datetime.now()))
            fd = open('./outputs/times.csv', 'a')
            fd.write(myCsvRow)
            fd.close()
        yield self.mosaik.set_data(commands)
        return time + 60

    def finalize(self):
        #self.worker.stop()
        #print("Worker Stopped")
        self.server.stop()
        print("Server Stopped")
        print("\n\n\n")
        print("#########################################")
        print('Finished')


    def get_data(self, outputs): # Return the data for the requested attributes in outputs
#outputs is a dict mapping entity IDs to lists of attribute names whose values are requested:
# 'eid_1': ['attr_1', 'attr_2', ...],
#{    'eid_1: {}      'attr_1': 'val_1', 'attr_2': 'val_2', ... 
        #print("Output of RTU: {}".format(outputs))
        data = {}
        for eid, attrs in outputs.items():
            for attr in attrs:
                try:
                    val = self._entities[eid][attr]
                except KeyError:
                    print("No such Key")
                    val = None
                data.setdefault(eid, {})[attr] = val
        return data

def main():
    return mosaik_api.start_simulation(MonitoringRTU())


if __name__ == '__main__':
    main()