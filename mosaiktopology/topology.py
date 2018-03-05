"""
A simple data collector that prints all data when the simulation finishes.

"""


import collections
from mosaiktopology import topology_model
from datetime import datetime
import mosaik_api
from mosaikpypower import model
recordtimes = 1


META = {
    'models': {
        'TopologyModel': {
            'public': True,
            'any_inputs': True,
            'params': [],
            'attrs': ['newgrid', 'switchstates'], 
        },
    },
}


class TopologySim(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.newgrid = None
        self.eid = None
        self.sid=None
        self.step_size = None
        self.rtu_info=None


    def init(self, sid, step_size):
        self.step_size = step_size
        self.sid = sid
        return self.meta

    def create(self, num, model):
        if num > 1 or self.eid is not None:
            raise RuntimeError('Can only create one instance of Topology.')
        self.eid = 'Topology'
        self.newgrid='data/demo_mv_grid.json'
        return [{ 'eid': self.eid, 'type': model, 'newgrid': self.newgrid }]

    def step(self, time, inputs):
        # inputs from RTU 
        self.rtu_info=None
        commands = {}
        if 'switchstates' in inputs['Topology'].keys():
            if recordtimes == 1:
                myCsvRow = "{};{};{}\n".format("TOPOLOGY-API", "change of switchstates.... refreshing the topology",
                                                  format(datetime.now()))
                fd = open('/Users/chromikjj/Code/mosaik-demo-integrated/times.csv', 'a')
                fd.write(myCsvRow)
                fd.close()
            self.rtu_info=inputs['Topology']['switchstates']['RTUSim-0.0-rtu']
            self.newgrid = topology_model.topology_refresh(self.newgrid, self.rtu_info)
            src=self.sid+'.'+self.eid
            dest = 'PyPower-0.0-grid'
            commands[src]={}
            commands[src][dest]={}
            commands[src][dest]['newgrid'] = self.newgrid
        yield self.mosaik.set_data(commands)
        if  bool(commands) and recordtimes == 1:
            myCsvRow = "{};{};{}\n".format("TOPOLOGY-API", "Sending new topology to PYPOWER", format(datetime.now()))
            fd = open('/Users/chromikjj/Code/mosaik-demo-integrated/times.csv', 'a')
            fd.write(myCsvRow)
            fd.close()
        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            for attr in attrs:
                try:
                    val = self.rtu_info
                except KeyError:
                    print("No such Key")
                    val = None
                data.setdefault(eid, {})[attr] = val
        return data

if __name__ == '__main__':
    mosaik_api.start_simulation(TopologySim())   