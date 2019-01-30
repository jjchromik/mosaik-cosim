"""
This module implements the mosaik API for `PYPOWER
<https://pypi.python.org/pypi/PYPOWER>`_.

"""
from __future__ import division
import logging
import os
import mosaik_api

from mosaikpypower import model
from datetime import datetime
from topology_loader.topology_loader import topology_loader
from distutils.util import strtobool


logger = logging.getLogger('pypower.mosaik')

meta = {
    'models': {
        'Grid': {
            'public': True,
            'any_inputs': True,
            'params': [
                'gridfile',  # Name of the file containing the grid topology.
                'sheetnames',  # Mapping of Excel sheet names, optional.
            ],
            'attrs': [
                'newgrid', # the grid we want to later replace.
                'switchstates',
            ],
        },
        'RefBus': {
            'public': False,
            'params': [],
            'attrs': [
                'P',   # Active power [W]
                'Q',   # Reactive power [VAr]
                'Vl',  # Nominal bus voltage [V]
                'Vm',  # Voltage magnitude [V]
                'Va',  # Voltage angle [deg]
            ],
        },
        'PQBus': {
            'public': False,
            'params': [],
            'attrs': [
                'P',   # Active power [W]
                'Q',   # Reactive power [VAr]
                'Vl',  # Nominal bus voltage [V]
                'Vm',  # Voltage magnitude [V]
                'Va',  # Voltage angle [deg]
            ],
        },
        'None': {
            'public': False,
            'params': [],
            'attrs': [
                'P',   # Active power [W]
                'Q',   # Reactive power [VAr]
                'Vl',  # Nominal bus voltage [V]
                'Vm',  # Voltage magnitude [V]
                'Va',  # Voltage angle [deg]
            ],
        },
        'Transformer': {
            'public': False,
            'params': [],
            'attrs': [
                'P_from',    # Active power at "from" side [W]
                'Q_from',    # Reactive power at "from" side [VAr]
                'P_to',      # Active power at "to" side [W]
                'Q_to',      # Reactive power at "to" side [VAr]
                'S_r',       # Rated apparent power [VA]
                'I_max_p',   # Maximum current on primary side [A]
                'I_max_s',   # Maximum current on secondary side [A]
                'P_loss',    # Active power loss [W]
                'U_p',       # Nominal primary voltage [V]
                'U_s',       # Nominal secondary voltage [V]
                'taps',      # Dict. of possible tap turns and their values
                'tap_turn',  # Currently active tap turn
            ],
        },
        'Branch': {
            'public': False,
            'params': [],
            'attrs': [
                'P_from',    # Active power at "from" side [W]
                'Q_from',    # Reactive power at "from" side [VAr]
                'P_to',      # Active power at "to" side [W]
                'Q_to',      # Reactive power at "to" side [VAr]
                'I_real',    # Branch current (real part) [A]
                'I_imag',    # Branch current (imaginary part) [A]
                'S_max',     # Maximum apparent power [VA]
                'I_max',     # Maximum current [A]
                'length',    # Line length [km]
                'R_per_km',  # Resistance per unit length [Ω/km]
                'X_per_km',  # Reactance per unit length [Ω/km]
                'C_per_km',  # Capactity per unit length [F/km]
                'online',    # Boolean flag (True|False)
            ],
        },
    },
}


class PyPower(mosaik_api.Simulator):
    def __init__(self):
        super(PyPower, self).__init__(meta)
        self.step_size = None
        self.gridfile = None
        self.newgrid = None
        self.grideid = None  #self.eid = None
        self.sid=None
        self.rtu_info=None
        topoloader = topology_loader()
        conf = topoloader.get_config()
        global RECORD_TIMES
        RECORD_TIMES = bool(strtobool(conf['recordtimes'].lower()))
        global RTU_STATS_OUTPUT
        RTU_STATS_OUTPUT = bool(strtobool(conf['rtu_stats_output'].lower()))

        # In PYPOWER loads are positive numbers and feed-in is expressed via
        # negative numbers. "init()" will that this flag to "1" in this case.
        # If incoming values for loads are negative and feed-in is positive,
        # this attribute must be set to -1.
        self.pos_loads = None

        self._entities = {}
        self._relations = []  # List of pair-wise related entities (IDs)
        self._ppcs = []  # The pypower cases
        self._cache = {}  # Cache for load flow outputs

    def init(self, sid, step_size, pos_loads=True):
        logger.debug('Power flow will be computed every %d seconds.' %
                     step_size)
        signs = ('positive', 'negative')
        logger.debug('Loads will be %s numbers, feed-in %s numbers.' %
                     signs if pos_loads else tuple(reversed(signs)))

        self.step_size = step_size
        self.pos_loads = 1 if pos_loads else -1
        #topo
        self.sid = sid
        #self.eid = 'PyPower'
        return self.meta

    def create(self, num, modelname, gridfile, sheetnames=None):
        self.gridfile=gridfile
        self.newgrid=gridfile

        if modelname != 'Grid':
            raise ValueError('Unknown model: "%s"' % modelname)
        if not os.path.isfile(self.gridfile):
            raise ValueError('File "%s" does not exist!' % self.gridfile)

        if not sheetnames:
            sheetnames = {}

        grids = []
        for i in range(num):
            grid_idx = len(self._ppcs)
            ppc, entities = model.load_case(self.gridfile, grid_idx, sheetnames)

            self._ppcs.append(ppc)
            children = []
            for eid, attrs in sorted(entities.items()):
                assert eid not in self._entities
                self._entities[eid] = attrs

                # We'll only add relations from branches to nodes (and not from
                # nodes to branches) because this is sufficient for mosaik to
                # build the entity graph.
                relations = []
                if attrs['etype'] in ['Transformer', 'Branch']:
                    relations = attrs['related']

                children.append({
                    'eid': eid,
                    'type': attrs['etype'],
                    'rel': relations,
                })
            self.grideid = model.make_eid('grid', grid_idx)
            grids.append({
                'eid': self.grideid, #model.make_eid('grid', grid_idx),
                'type': 'Grid',
                'newgrid': self.gridfile,
                'rel': [],
                'children': children,
            })
        return grids

    def step(self, time, inputs): #inputs keys are eg '0-node_b24', '0-node_b14'
        for ppc in self._ppcs:
            model.reset_inputs(ppc)
        if 'PyPower' in inputs:
            if 'switchstates' in inputs['PyPower'].keys():   # sid: PyPower-0%    grideid: 0-grid
                self.rtu_info = inputs['PyPower']['switchstates']['RTUSim-0.0-rtu']
                if RECORD_TIMES:
                    myCsvRow = "{};{};{}\n".format("TOPOLOGY-API", "change of switchstates.... refreshing the topology",
                                                      format(datetime.now()))
                    fd = open('./outputs/times.csv', 'a')
                    fd.write(myCsvRow)
                    fd.close()
                self.newgrid = model.topology_refresh(self.newgrid, self.rtu_info)
                grids =[]
                if RECORD_TIMES:
                    myCsvRow = "{};{};{}\n".format("PYPOWER-API", "New topology received...",
                                                      format(datetime.now()))
                    fd = open('./outputs/times.csv', 'a')
                    fd.write(myCsvRow)
                    fd.close()
                grid_idx = 0
                sheetnames = {}
                #print("################\nself._entities OLD: \n\n{}\n################\n################\n".format(self._entities))
                self._entities = {}
                self._ppcs = []
                ppc, entities = model.load_case(self.newgrid, grid_idx, sheetnames)
                #print("################\nEntities NEW: \n\n{}\n################\n################\n".format(entities))
                self._ppcs.append(ppc)
                for ppc in self._ppcs:
                    model.reset_inputs(ppc)
                children = []
                for eid, attrs in sorted(entities.items()):
                    assert eid not in self._entities # problem?
                    self._entities[eid] = attrs

                    # We'll only add relations from branches to nodes (and not from
                    # nodes to branches) because this is sufficient for mosaik to
                    # build the entity graph.
                    relations = []
                    if attrs['etype'] in ['Transformer', 'Branch']:
                        relations = attrs['related']

                    children.append({
                        'eid': eid,
                        'type': attrs['etype'],
                        'rel': relations,
                    })
                grids.append({
                    'eid': self.grideid, #model.make_eid('grid', grid_idx),
                    'type': 'Grid',
                    'newgrid': self.newgrid,
                    'rel': [],
                    'children': children,
                })
                #print("################\nself._entities NEW: \n\n{}\n################\n################\n".format(entities))

        for eid, attrs in inputs.items():
            if 'PyPower' in eid:
                continue

            else:
                ppc = model.case_for_eid(eid, self._ppcs)
                idx = self._entities[eid]['idx']
                etype = self._entities[eid]['etype']
                static = self._entities[eid]['static']
                for name, values in attrs.items():
                    # values is a dict of p/q values, sum them up
                    attrs[name] = sum(float(v) for v in values.values())
                    if name == 'P':
                        attrs[name] *= self.pos_loads
                model.set_inputs(ppc, etype, idx, attrs, static)

        res = []
        for ppc in self._ppcs:
            res.append(model.perform_powerflow(ppc))
        if RECORD_TIMES:
            myCsvRow = "{};{};{}\n".format("PYPOWER-API", "Recalculated power flow equations", format(datetime.now()))
            fd = open('./outputs/times.csv', 'a')
            fd.write(myCsvRow)
            fd.close()
        self._cache = model.get_cache_entries(res, self._entities) #cases, entity map
        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            for attr in attrs:
                try:
                    if eid == self.grideid and attr == 'switchstates':
                        val = self.newgrid
                    else:
                        val = self._cache[eid][attr]
                        if attr == 'P':
                            val *= self.pos_loads
                        if attr == 'I_imag':
                            val = 0
                except KeyError:
                    val = self._entities[eid]['static'][attr]
                data.setdefault(eid, {})[attr] = val

        return data



def main():
    mosaik_api.start_simulation(PyPower(), 'The mosaik-PYPOWER adapter')
