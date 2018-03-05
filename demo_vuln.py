# file: demo_vuln.py
# author: Justyna Chromik

"""""
This is the reference scenario for the mosaik co-simulation environment.
"""

import random
import logging
import time

from mosaik.util import connect_randomly, connect_many_to_one
import mosaik
import os
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
#        'cmd': 'mosaik-web -s 0.0.0.0:8000 %(addr)s',
        #'cmd': 'mosaik-web %(addr)s',
        'cmd': 'mosaik-web/mosaik-web.sh %(addr)s',
        #'python': 'mosaik-web.mosaik_web.mosaik:main',  #mosaik_web.mosaik:main
    },
   # 'TopologySim': {
   #     'python': 'mosaiktopology.topology:TopologySim',# %(addr)s',  #mosaik_topology.mosaik:Topology
   # },
    'RTUSim': {
        'python': 'mosaikrtu.rtu:MonitoringRTU',# %(addr)s',  #mosaik_topology.mosaik:Topology
    },
}

recordtimes = 1
demo_nr = 1




# Logging settings
logger = logging.getLogger('demo_main')
#ch = logging.StreamHandler()
#ch.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#ch.setFormatter(formatter)
#logger.addHandler(ch)

if recordtimes == 1 :
    try:
        os.remove('/Users/chromikjj/Code/mosaik-demo-integrated/times.csv')
    except OSError:
        pass

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
    global GEN_DATA
    GEN_DATA = os.path.join("data", conf['gen_data']) if 'gen_data' in conf else None
    global DEFAULT_VOLTAGE
    DEFAULT_VOLTAGE = float(conf['default_voltage'])
    global PROFILE_FILE
    PROFILE_FILE = os.path.join("data", conf['profile_file'])
    logger.warning("Profile file: {} ".format(PROFILE_FILE))
    global GRID_NAME
    GRID_NAME = conf['grid_name']
    global GRID_FILE
    GRID_FILE = os.path.join("data", conf['grid_file'])
    global RTU_FILE
    RTU_FILE = os.path.join("data", conf['rtu_file'])
    global RTU_STATS_OUTPUT
    RTU_STATS_OUTPUT = conf['rtu_stats_output']

    random.seed(23)
    start_time = time.time()
    world = mosaik.World(sim_config, {'start_timeout': 30})
    create_scenario(world)

    if RT_FACTOR == 1:
        world.run(until=END)
    else:
        world.run(until=END, rt_factor=RT_FACTOR)  # As fast as possilb
    elapsed_time = time.time() - start_time
    print("Elapsed time: {}".format(elapsed_time))

def create_scenario(world):
    # Start simulators
    pypower = world.start('PyPower', step_size=60)
    hhsim = world.start('HouseholdSim')
    pvsim = world.start('CSV', sim_start=START, datafile=PV_DATA)
    if not GEN_DATA == None:
        gensim = world.start('HouseholdSim')
    rtusim = world.start('RTUSim')


    # Instantiate models
    grid_inf = pypower.Grid(gridfile=GRID_FILE)
    #topology = toposim.TopologyModel()
    grid = grid_inf.children
    houses = hhsim.ResidentialLoads(sim_start=START,
                                    profile_file=PROFILE_FILE, # file with household profiles
                                    grid_name=GRID_NAME).children
    pvs = pvsim.PV.create(0)
    if not GEN_DATA == None:
        gens = gensim.ResidentialLoads(sim_start=START,
                                        profile_file=GEN_DATA,  # file with generators profiles
                                        grid_name=GRID_NAME).children
    rtu_sim = rtusim.RTU(rtu_ref=RTU_FILE)
    rtu=rtu_sim.children

    # Connect entities - this defines the data flow between the simulators 
    # A provides input for B connect(A, B); but B provides "schedule" or control to A
   # world.connect(grid_inf, topology, 'newgrid', async_requests=True)
    connect_buildings_to_grid(world, houses, grid)
    if not GEN_DATA == None:
        connect_buildings_to_grid(world, gens, grid)

    connect_randomly(world, pvs, [e for e in grid if 'node' in e.eid], 'P')
    #if not GEN_DATA == None:
        #connect_randomly(world, gens, [e for e in grid if 'node' in e.eid], 'P')

    # Database
    db = world.start('DB', step_size=60, duration=END)
    hdf5 = db.Database(filename='demo.hdf5')
    connect_many_to_one(world, houses, hdf5, 'P_out')
    connect_many_to_one(world, pvs, hdf5, 'P')
    if not GEN_DATA == None:
        connect_many_to_one(world, gens, hdf5, 'P_out')

    # TODO: get the house h_11 and make the PV panel not connect to this particular house?


    logger.warning("Connecting sensors to grid...")
    connect_sensors_to_grid(world, rtu, grid)



    world.connect(grid_inf, rtu_sim, 'switchstates',  async_requests=True)

    nodes = [e for e in grid if e.type in ('RefBus, PQBus')]
    connect_many_to_one(world, nodes, hdf5, 'P', 'Q', 'Vl', 'Vm', 'Va')   # connect_many_to_one : (world, source, destibation)

    branches = [e for e in grid if e.type in ('Transformer', 'Branch')]
    connect_many_to_one(world, branches, hdf5,
                        'P_from', 'Q_from', 'P_to', 'Q_to')



    # Web visualization
    webvis = world.start('WebVis', start_date=START, step_size=60)
    webvis.set_config(ignore_types=['Topology', 'ResidentialLoads', 'Grid',
                                    'Database', 'TopologyModel', 'RTU', 'sensor', 'switch'])
    vis_topo = webvis.Topology()

    connect_many_to_one(world, nodes, vis_topo, 'P', 'Vm')
    webvis.set_etypes({
        'None': {
            'cls': 'none',
            'attr': 'Vm',
            'unit': 'U [V]',
            'default': 0,
            'min': 0,
            'max': 0,
        },
        'RefBus': {
            'cls': 'refbus',
            'attr': 'P',
            'unit': 'P [W]',
            'default': 10000,
            'min': 0,
            'max': 30000,
        },
        'PQBus': {
            'cls': 'pqbus',
            'attr': 'Vm',
            'unit': 'U [V]',
            'default': 10000,
            'min': 0.99 * 10000,
            'max': 1.01 * 10000,
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
            'cls': 'pv',
            'attr': 'P',
            'unit': 'P [W]',
            'default': 0,
            'min': -10000,
            'max': 0,
        },
    })

    if not GEN_DATA == None:
        connect_many_to_one(world, gens, vis_topo, 'P_out')
    webvis.set_etypes({
        'GEN': {
            'cls': 'gen',
            'attr': 'P',
            'unit': 'P [W]',
            'default': 0,
            'min': -10000,
            'max': 0,
        },
    })


def connect_buildings_to_grid(world, houses, grid):
    buses = filter(lambda e: e.type in ('PQBus', 'None'), grid)     # getting buses entities from grid.children
    buses = {b.eid.split('-')[1]: b for b in buses}                 # getting just the names of the buses, e.g. node_d1
    house_data = world.get_data(houses, 'node_id')                  # getting house information: 'node_id's from houses
    for house in houses:                                            # iterating per house
        node_id = house_data[house]['node_id']                      # get ID of the node from house information
        world.connect(house, buses[node_id], ('P_out', 'P'))        # connect

def connect_sensors_to_grid(world, rtu, grid):
    buses = filter(lambda e: e.type in ('PQBus', 'None'), grid)
    buses = {b.eid.split('-')[1]: b for b in buses}
    branches = filter(lambda e: e.type =='Branch', grid)
    branches = {b.eid.split('-')[1]: b for b in branches}
    sensors = filter(lambda e: e.type == 'sensor', rtu)
    voltage_data = world.get_data(rtu, 'node') # get_data(entity_set, *attributes) ; Get and return the values of all attributes for each entity of an entity_set. 
    # The return value is a dict mapping the entities of entity_set to dicts containing the values of each attribute in attributes:
    #   Entity(...): {
        #'attr_1': 'val_1',
    current_data = world.get_data(rtu, 'branch')
    #type_data = world.get_data(rtu, 'etype')
    for sensor in sensors: # get Id of node from sensors
        node_id = voltage_data[sensor]['node']
        world.connect(buses[node_id], sensor, 'Vm')
        branch_id = current_data[sensor]['branch']
        world.connect(branches[branch_id], sensor, 'I_imag', 'I_real')

# TODO: connect RTUs to grid ? 
# def connect_switches_to_grid(world, rtu, grid):


if __name__ == '__main__':
    main()
