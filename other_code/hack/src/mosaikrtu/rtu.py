# simulator_mosaik.py
"""
Mosaik interface for the example simulator.

"""
import mosaik_api
import collections
import os
import sys
import csv

from mosaikrtu import rtu_model
from mosaikrtu.operator_client import operator_client

META = {
    'models': {
        'RTU': {
            'public': True,
            'params': ['rtu_ref', 'rtu_stats_output'],
            'attrs': ['switchstates'],
        },
        'sensor': {
            'public': True,
            'params': ['node', 'branch'],
            'attrs': ['I_real', 'I_imag', 'Vm', 'Va', 'P_from', 'P_to', 'P'],
        },
        'switch': {
            'public': True,
            # read from the file and mark as "on" if line is online.
            'params': ['init_status', 'branch'],
            'attrs': ['online'],
        },
    },
    'extra_methods': [
        'start_webclient',
    ],
}


class MonitoringRTU(mosaik_api.Simulator):

    """
    Monitoring RTU for handeling all single RTUs in the grid.
    """

    def __init__(self):
        super().__init__(META)
        self.sid = None
        self.children = []
        self.current = 0
        self.rtu_ref = None
        self.com_server = None
        # boolean whether to save stats for evaluation
        self.get_stats = False
        self.print_stats = ['I_real', 'I_imag', 'Vm', 'Va']
        self.stats = {}
        self.op_client = None

    def init(self, sid):
        self.sid = sid
        return self.meta

    def start_webclient(self):
        """
        Starts the client for communication with the web visualisation.
        """
        for rtu in self.children:
            rtu.start_webclient()

    def start_com_client(self):
        """
        Starts the client for communciation between the RTUs.
        """
        for rtu in self.children:
            rtu.start_com_client(self.com_server)
        for rtu in self.children:
            rtu.worker.initialize_adj_rtus()
    
    def start_operator_client(self):
        """
        Starts the TCP client for communication with the operator tools.
        """
        self.op_client = operator_client()
        self.op_client.start()
        # self.op_client.send_msg("init msg")
        for rtu in self.children:
            rtu.set_op_client(self.op_client)

    def create(self, num, model, rtu_ref, rtu_stats_output):
        self.rtu_ref = rtu_ref
        if rtu_stats_output == "True":
            self.get_stats = True
        # getting all RTU xml files
        rtu_xml = []
        for f in os.listdir(rtu_ref):
            if ".xml" in f:
                rtu_xml.append(os.path.join(rtu_ref, f))
        # creating a RTU for each file
        i = 0
        while i < len(rtu_xml):
            rtueid = rtu_model.make_eid('rtu', i)
            rtu = RTU(rtueid)
            rtu.create(rtu_xml[i])
            rtu.init(self.sid)
            self.children.append(rtu)
            i = i + 1
        # creating communication stuff
        port = 12500
        self.com_server = rtu_model.create_com_server()
        self.com_server.start()
        self.start_com_client()
        self.start_operator_client()
        return [self]

    def step(self, time, inputs):
        # update data
        for rtu in self.children:
            yield self.mosaik.set_data(rtu.step(time, inputs))

        # execute logic
        for rtu in self.children:
            rtu.worker.execute_logic()

        # communication with operator GUI
        if self.op_client.send_msg("isresetting") == "True":
            for rtu in self.children:
                rtu.hard_reset()

        # save stats for evaluation
        if self.get_stats:
            for s in inputs:
                if not 'rtu' in s:
                    for item in self.print_stats:
                        if item not in self.stats:
                            self.stats[item] = {}
                        for k in inputs[s][item].keys():
                            if s in self.stats[item]:
                                a = self.stats[item][s]
                                a[len(a):] = [(time, inputs[s][item][k])]
                                self.stats[item].update({s: a})
                            else:
                                self.stats[item][s] = [
                                    (time, inputs[s][item][k])]
        return time + 60

    def finalize(self):
        # finalize all RTUs
        for rtu in self.children:
            rtu.finalize()

        # print out the evaluation stats files
        if self.get_stats:
            path = os.path.join(self.rtu_ref, "..", "stats")
            if not os.path.exists(path):
                os.makedirs(path)
            for item in self.print_stats:
                for s in self.stats[item]:
                    csv_n = os.path.join(path, str(s) + "_" + item + ".txt")
                    with open(csv_n, 'w', newline='') as f:
                        writer = csv.writer(
                            f, delimiter='\t', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                        writer.writerow(['time', item, 'd/dt'])
                        b = None
                        d = self.stats[item][s][0]
                        for i in range(len(self.stats[item][s])):
                            b = d
                            d = self.stats[item][s][i]
                            if d[0] != 0:
                                d1 = str((d[1] - b[1]) /
                                         (d[0] - b[0])).replace('.', ',')
                            else:
                                d1 = str(0)
                            if d1 != '0,0':
                                writer.writerow(
                                    [d[0], str(d[1]).replace('.', ','), d1])

                csv_n = os.path.join(path, str(item) + "_all.txt")
                rows = [None] * len(self.stats[item]['sensor_1'])
                head = ['time'] * (len(self.stats[item]) + 1)
                for i in range(len(rows)):
                    rows[i] = [None] * (len(self.stats[item]) + 1)
                    for s in self.stats[item]:
                        d = self.stats[item][s][i]
                        rows[i][0] = d[0]
                        sens, j = s.split("_")
                        rows[i][int(j)] = str(d[1]).replace('.', ',')
                        if i == 0:
                            head[int(j)] = s
                with open(csv_n, 'w', newline='') as f:
                    writer = csv.writer(
                        f, delimiter='\t', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(head)
                    for r in rows:
                        if r[0] % 900 == 0:
                            writer.writerow(r)

                csv_n = os.path.join(path, str(item) + "_d1_all.txt")
                rows = [None] * len(self.stats[item]['sensor_1'])
                head = ['time'] * (len(self.stats[item]) + 1)
                for i in range(len(rows)):
                    rows[i] = [None] * (len(self.stats[item]) + 1)
                    for s in self.stats[item]:
                        d = self.stats[item][s][i]
                        rows[i][0] = d[0]
                        sens, j = s.split("_")
                        if d[0] != 0:
                            b = self.stats[item][s][i - 1]
                            d1 = str((d[1] - b[1]) / (d[0] - b[0])
                                     ).replace('.', ',')
                        else:
                            d1 = str(0)
                        rows[i][int(j)] = str(d1).replace('.', ',')
                        if i == 0:
                            head[int(j)] = s
                with open(csv_n, 'w', newline='') as f:
                    writer = csv.writer(
                        f, delimiter='\t', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(head)
                    for r in rows:
                        if r[0] % 900 == 0:
                            writer.writerow(r)

                csv_n = os.path.join(path, str(item) + "_d1_rel_all.txt")
                rows = [None] * len(self.stats[item]['sensor_1'])
                head = ['time'] * (len(self.stats[item]) + 1)
                for i in range(len(rows)):
                    rows[i] = [None] * (len(self.stats[item]) + 1)
                    for s in self.stats[item]:
                        d = self.stats[item][s][i]
                        rows[i][0] = d[0]
                        sens, j = s.split("_")
                        if d[0] != 0 and d[1] != 0:
                            b = self.stats[item][s][i - 1]
                            d1 = str(((d[1] - b[1]) / (d[0] - b[0])) / d[1]
                                     ).replace('.', ',')
                        else:
                            d1 = str(0)
                        rows[i][int(j)] = str(d1).replace('.', ',')
                        if i == 0:
                            head[int(j)] = s
                with open(csv_n, 'w', newline='') as f:
                    writer = csv.writer(
                        f, delimiter='\t', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(head)
                    for r in rows:
                        if r[0] % 900 == 0:
                            writer.writerow(r)

        print("\n")
        print("#########################################")
        print('Finished')

    def get_data(self, outputs):
        data = {}
        for rtu in self.children:
            data.update(rtu.get_data(outputs))
        return data

    def __len__(self):
        return 1

    def __iter__(self):
        return self

    def __next__(self):
        result = self.children[self.current]
        self.current += 1
        if self.current >= len(self.children):
            raise StopIteration
        return self.children[self.current]

    def __getitem__(self, item):
        if item == 'type':
            return 'RTU'
        return self.children[self.current].__getitem__(item)

    def get(self, item, out):
        """
        Gets the value of the given value or the given out value.
        :param item: item to get the value of
        :param out: output value
        :return: value of the item or out if not found
        """
        if item == 'children':
            return self.children
        else:
            return self.children[self.current].get(item, out)


class RTU(MonitoringRTU):

    def __init__(self, rtueid):
        self.rtu_ref = ""
        self.sid = None
        self.data = ""
        self.rtueid = rtueid
        self.entities = {}  # Maps EIDs to model indices in self.simulator ??
        self._entities = {}
        self._cache = {}
        self.worker = ""
        self.server = ""
        self.rtu = None

    def init(self, sid):
        self.sid = sid
        return self.meta

    def start_webclient(self):
        self.worker.start_webclient()

    def start_com_client(self, server):
        self.worker.start_com_client(server)

    def set_op_client(self, client):
        """
        Sets the TCP client for communication with the operator GUI to the given client.
        :param client: client to set
        """
        self.worker.set_op_client(client)

    def hard_reset(self):
        """
        Hard resets the RTU worker.
        """
        self.worker.reset_trust()

    def create(self, rtu_ref):
        if rtu_ref:
            self.rtu_ref = rtu_ref
            conf = rtu_model.load_rtu(self.rtu_ref)
            self.data = rtu_model.create_datablock(conf)
            self._cache, entities = rtu_model.create_cache(conf["registers"])
            self.server = rtu_model.create_server(conf, self.data, self.rtueid)
            self.worker = rtu_model.create_worker(
                conf, self.data, self._cache, self.rtueid)
            self.worker.eid = self.rtueid
            self.worker.start()
            self.server.start()
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

            self.rtu = {
                'eid': self.rtueid,  # model.make_eid('grid', grid_idx),
                'type': 'RTU',
                'children': children,
            }
        return self.rtu

    def update_worker(self, inputs, commands):
        """
        Gives the inputs (and possibly commands) of each step to the worker so they can be used in the logic.
        :param inputs: inputs to pass
        :param commands: commands to pass
        """
        self.worker.physical_data = inputs
        self.worker.commands = commands

    def step(self, time, inputs):
        commands = {}  # set commands for switches
        switchstates = {}
        src = str(self.sid) + '.' + self.rtueid
        dest = 'TopologySim-0.Topology'
        commands[src] = {}
        commands[src][dest] = {}

        #print("Inputs for RTU: {}".format(inputs))

        for s, v in self._cache.items():
            if 'switch' in s:
                if self.data.get(v['reg_type'], v['index'], 1)[0] != v['value']:
                    self._cache[s]['value'] = self.data.get(
                        v['reg_type'], v['index'], 1)[0]
                    switchstates[v['place']] = bool(v['value'])

        if bool(switchstates):
            if commands[src][dest] == {}:
                commands[src][dest]['switchstates'] = switchstates
            else:
                commands[src][dest]['switchstates'].update(switchstates)
            #print("RTU: the state of the switches was CHANGED: {}".format(commands[src][dest]['switchstates']))

        for eid, data in inputs.items():
            for attr, values in data.items():  # attr is like I_real etc.
                if attr == 'I_real':
                    for src, value in values.items():
                        _src = src.split("-")[2]
                        dev_id = eid + "-" + _src
                        if dev_id in self._cache:
                            db_val = float(self.data.get(
                                'ir', self._cache[dev_id]['index'], 1)[0])
                            if db_val < sys.maxsize:
                                #print(self.rtueid + ": set " + str(eid) + " with index " + str(self._cache[dev_id]['index']) + " to: " + str(db_val))
                                self._cache[dev_id]["value"][0] = db_val
                                inputs[eid][attr][src] = db_val
                            else:
                                self._cache[dev_id]["value"][0] = value
        # update the dicts with data from previous step
        if self.worker.voltage_angle: # check if the voltage angle dict is already initialized
            self.worker.update_voltage_angle_dict()
        if self.worker.voltage_magnitude: # check if the voltage magnitude dict is already initialized
            self.worker.update_voltage_magnitude_dict()
        if self.worker.current: # check if the voltage magnitude dict is already initialized
            self.worker.update_current_dict()
        self.update_worker(inputs, commands)
        return commands

    def finalize(self):
        self.worker.stop()
        print(self.rtueid + ": Worker Stopped")
        self.server.stop()
        print(self.rtueid + ": Server Stopped")

    def get_data(self, outputs):  # Return the data for the requested attributes in outputs
        # outputs is a dict mapping entity IDs to lists of attribute names whose values are requested:
        # 'eid_1': ['attr_1', 'attr_2', ...],
        #{    'eid_1: {}      'attr_1': 'val_1', 'attr_2': 'val_2', ...
        #print("Output of RTU: {}".format(outputs))
        data = {}
        for eid, attrs in outputs.items():
            for attr in attrs:
                try:
                    data.setdefault(eid, {})[attr] = self._entities[eid][attr]
                except KeyError:
                    val = None
                #data.setdefault(eid, {})[attr] = val
                # print(data)
        return data

    def __getitem__(self, item):
        return self.rtu[item]

    def get(self, item, out):
        if item in self.rtu:
            return self.rtu[item]
        else:
            return out


def main():
    return mosaik_api.start_simulation(MonitoringRTU())


if __name__ == '__main__':
    main()