import itertools
import random
import logging
import os

from mosaik.util import connect_randomly, connect_many_to_one
import mosaik
import pprint
from topology_loader.topology_loader import topology_loader

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
        #'cmd': 'python mosaik-pypower %(addr)s',
    },
    'WebVis': {
        #'cmd': 'mosaik-web -s 0.0.0.0:8000 %(addr)s',
        'python': 'webvis.webvis:WebVis'
    },
    'TopologySim': {
        # %(addr)s',  #mosaik_topology.mosaik:Topology
        'python': 'mosaiktopology.topology:TopologySim',
    },
    'RTUSim': {
        # %(addr)s',  #mosaik_topology.mosaik:Topology
        'python': 'mosaikrtu.rtu:MonitoringRTU',
    },
}

START = '2014-01-01 00:00:00'
END = 31 * 24 * 360  # 1 day 31*24
RT_FACTOR = 1
PV_DATA = 'data/pv_10kw.csv'
DEFAULT_VOLTAGE = 10000.0
# PROFILE_FILE = 'data/profiles_mv.data.gz' # household profiles, which
# are processed by Mosaik-HouseholdSim
PROFILE_FILE = 'data/profiles_nl.data.gz'
GRID_NAME = 'demo_mv_grid'
GRID_FILE = 'data/%s.json' % GRID_NAME
RTU_FILE = 'mosaikrtu/conf'
RTU_STATS_OUTPUT = "False"
pp = pprint.PrettyPrinter(indent=4)
logger = logging.getLogger('demo_main')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def main():

    topoloader = topology_loader()
    conf = topoloader.get_config()

    global START
    START = conf['start']
    global END
    END = int(conf['end'])
    global RT_FACTOR
    RT_FACTOR = float(conf['rt_factor'])
    global PV_DATA
    PV_DATA = os.path.join("data", conf['pv_data'])
    global DEFAULT_VOLTAGE
    DEFAULT_VOLTAGE = float(conf['default_voltage'])
    global PROFILE_FILE
    PROFILE_FILE = os.path.join("data", conf['profile_file'])
    global GRID_NAME
    GRID_NAME = conf['grid_name']
    global GRID_FILE
    GRID_FILE = os.path.join("data", conf['grid_file'])
    global RTU_FILE
    RTU_FILE = os.path.join("data", conf['rtu_file'])
    global RTU_STATS_OUTPUT
    RTU_STATS_OUTPUT = conf['rtu_stats_output']
    
    random.seed(23)
    world = mosaik.World(sim_config)
    create_scenario(world)

    if RT_FACTOR == 1:
        world.run(until=END)
    else:
        world.run(until=END, rt_factor=RT_FACTOR)  # As fast as possilb
    # world.run(until=END, rt_factor=1 / 120)  # Real-time 1min -> 1sec


def create_scenario(world):
    # Start simulators
    pypower = world.start('PyPower', step_size=15 * 60)
    # TODO replace to the other randomized program of people from CAES
    hhsim = world.start('HouseholdSim')
    pvsim = world.start('CSV', sim_start=START, datafile=PV_DATA)
    toposim = world.start('TopologySim', step_size=15 * 60)
    rtusim = world.start('RTUSim')

    # Instantiate models
    print("[*] Loading grid from file: '" + GRID_FILE + "'.")
    topology = toposim.TopologyModel()
    grid_inf = pypower.Grid(gridfile=GRID_FILE)
    grid = grid_inf.children
    houses = hhsim.ResidentialLoads(sim_start=START,
                                    profile_file=PROFILE_FILE,  # file with household profiles
                                    grid_name=GRID_NAME).children
    pvs = pvsim.PV.create(20)

    rtu_sim = rtusim.RTU(rtu_ref=RTU_FILE, rtu_stats_output=RTU_STATS_OUTPUT)
    rtus = rtu_sim.children
    rtu = []
    for i in range(0, len(rtus)):
        for r in rtus[i].children:
            rtu.append(r)

    # Connect entities - this defines the data flow between the simulators
    # A provides input for B connect(A, B); but B provides "schedule" or
    # control to A
    world.connect(grid_inf, topology, 'newgrid', async_requests=True)
    #world.connect(rtu, worker)
    connect_buildings_to_grid(world, houses, grid)
    connect_randomly(world, pvs, [e for e in grid if 'node' in e.eid], 'P')

    # Database
    db = world.start('DB', step_size=60, duration=END)
    hdf5 = db.Database(filename='demo.hdf5')
    connect_many_to_one(world, houses, hdf5, 'P_out')
    connect_many_to_one(world, pvs, hdf5, 'P')

    #logger.warn("Connecting sensors to grid...")
    connect_sensors_to_grid(world, rtu, grid)


############TEST###############
    world.connect(topology, rtu_sim, 'switchstates',  async_requests=True)
#

    nodes = [e for e in grid if e.type in ('RefBus, PQBus')]
    connect_many_to_one(world, nodes, hdf5, 'P', 'Q', 'Vl', 'Vm', 'Va')

    branches = [e for e in grid if e.type in ('Transformer', 'Branch')]
    connect_many_to_one(world, branches, hdf5, 'P_from', 'Q_from', 'P_to')
# TODO: connect many to one or something: for sensor in RTU connect first only e.g. nodes,
#

    # Web visualization
    webvis = world.start('WebVis', start_date=START, step_size=60)
    webvis.set_config(ignore_types=['Topology', 'ResidentialLoads', 'Grid',
                                    'Database', 'TopologyModel', 'RTU', 'sensor', 'switch'])
    vis_topo = webvis.Topology()

    connect_many_to_one(world, nodes, vis_topo, 'P', 'Vm')
    webvis.set_etypes({
        'RefBus': {
            'cls': 'refbus',
            'attr': 'P',
            'unit': 'P [W]',
            'default': 0,
            'min': 0,
            'max': 30000,
        },
        'PQBus': {
            'cls': 'pqbus',
            'attr': 'Vm',
            'unit': 'U [V]',
            'default': DEFAULT_VOLTAGE,
            'min': 0.9 * DEFAULT_VOLTAGE,
            'max': 1.1 * DEFAULT_VOLTAGE,
        },
        'None': {
            'cls': 'none',
            'attr': 'Vm',
            'unit': 'U [V]',
            'default': 0,
            'min': 0,
            'max': 0,
        },
    })

    connect_many_to_one(world, houses, vis_topo, 'P_out')
    webvis.set_etypes({
        'House': {
            'cls': 'load',
            'attr': 'P_out',
            'unit': 'P [W]',
            'default': 0,
            'min': 0,
            'max': 3000,
        },
    })

    connect_many_to_one(world, pvs, vis_topo, 'P')
    webvis.set_etypes({
        'PV': {
            'cls': 'gen',
            'attr': 'P',
            'unit': 'P [W]',
            'default': 0,
            'min': -10000,
            'max': 0,
        },
    })

    webvis._build_topology()

    rtusim.start_webclient()


def connect_buildings_to_grid(world, houses, grid):
    # getting buses entities from grid.children
    buses = filter(lambda e: e.type in ('PQBus', 'None'), grid)
    # getting just the names of the buses, e.g. node_d1
    buses = {b.eid.split('-')[1]: b for b in buses}
    # getting house information: 'node_id's from houses
    house_data = world.get_data(houses, 'node_id')
    for house in houses:                                            # iterating per house
        # get ID of the node from house information
        node_id = house_data[house]['node_id']
        world.connect(house, buses[node_id], ('P_out', 'P'))        # connect


def connect_sensors_to_grid(world, rtu, grid):
    buses = filter(lambda e: e.type in ('PQBus', 'None'), grid)
    buses = {b.eid.split('-')[1]: b for b in buses}
    branches = filter(lambda e: e.type == 'Branch', grid)
    branches = {b.eid.split('-')[1]: b for b in branches}
    sensors = filter(lambda e: e.type == 'sensor', rtu)
    # get_data(entity_set, *attributes) ; Get and return the values of all
    # attributes for each entity of an entity_set.
    voltage_data = world.get_data(rtu, 'node')
    # The return value is a dict mapping the entities of entity_set to dicts containing the values of each attribute in attributes:
    #   Entity(...): {
    #'attr_1': 'val_1',
    current_data = world.get_data(rtu, 'branch')
    #type_data = world.get_data(rtu, 'etype')
    for sensor in sensors:  # get Id of node from sensors
        node_id = voltage_data[sensor]['node']
        world.connect(buses[node_id], sensor, 'Vm', 'Va', 'P')
        branch_id = current_data[sensor]['branch']
        world.connect(branches[branch_id], sensor,
                      'I_imag', 'I_real', 'P_to', 'P_from')

# TODO: connect RTUs to grid ?
# def connect_switches_to_grid(world, rtu, grid):


if __name__ == '__main__':
    main()
