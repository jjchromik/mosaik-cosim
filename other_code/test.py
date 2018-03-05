import itertools
import random

from mosaik.util import connect_randomly, connect_many_to_one
import mosaik


sim_config = {
    'CSV': {
        'python': 'mosaik_csv:CSV',
    },
    'DB': {
        'cmd': 'mosaik-hdf5 %(addr)s',
    },
    'HouseholdSim': {
        'python': 'householdsim.mosaik:HouseholdSim',
        # 'cmd': 'mosaik-householdsim %(addr)s',
    },
    'PyPower': {
        'python': 'mosaikpypower.mosaik:PyPower',
        #'cmd': 'python mosaik-pypower/mosaik.py %(addr)s',
    },
    'WebVis': {
        'cmd': 'mosaik-web -s 0.0.0.0:8000 %(addr)s',
    },
    'TopologySim': {
        'cmd': 'python topology.py %(addr)s',  #mosaik_topology.mosaik:Topology
    },
}

START = '2014-01-01 00:00:00'
END = 3600  # 1 day
PV_DATA = 'data/pv_10kw.csv'
PROFILE_FILE = 'data/profiles_mv.data.gz' # household profiles, which are processed by Mosaik-HouseholdSim
GRID_NAME = 'demo_mv_grid'
GRID_FILE = 'data/%s.json' % GRID_NAME

world = mosaik.World(sim_config)

#start simulators
pypower = world.start('PyPower', step_size=15*60)
toposim = world.start('TopologySim', step_size=15*60)

#instantiate
topology = toposim.TopologyModel()
grid_inf = pypower.Grid(gridfile=GRID_FILE)
grid = grid_inf.children

#grid_ref = [e for e in grid if e.type in('Grid')]
#connect
world.connect(grid_inf, topology, 'newgrid', async_requests=True)

world.run(until=END)