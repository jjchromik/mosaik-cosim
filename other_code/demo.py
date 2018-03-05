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
        'python': 'mosaik_pypower.mosaik:PyPower',
        # 'cmd': 'mosaik-pypower %(addr)s',
    },
    'WebVis': {
        'cmd': 'mosaik-web -s 0.0.0.0:8000 %(addr)s',
    },
#    'RTUSim': {             #adding the simulation of the RTU based on PyModbus
#        'cmd': 'python run.py %(addr)s',  #conf/rtu_info.xml
#        #TODO: change the run.py to a mosaik compatible simulator
#    },
    'RTUSim': {             #adding the simulation of the RTU based on PyModbus
        'cmd': 'python collector.py %(addr)s',  #conf/rtu_info.xml
        #TODO: change the run.py to a mosaik compatible simulator
    },
}

START = '2014-01-01 00:00:00'
END = 31 * 24 * 3600  # 1 day
PV_DATA = 'data/pv_10kw.csv'
PROFILE_FILE = 'data/profiles_mv.data.gz' # household profiles, which are processed by Mosaik-HouseholdSim
GRID_NAME = 'demo_mv_grid'
GRID_FILE = 'data/%s.json' % GRID_NAME
#RTU_FILE = 'conf/rtu_info.xml'


def main():
    random.seed(23)
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=END)  # As fast as possilb 
    # world.run(until=END, rt_factor=1/60)  # Real-time 1min -> 1sec


def create_scenario(world):
    # Start simulators
    pypower = world.start('PyPower', step_size=15*60)
    hhsim = world.start('HouseholdSim') #  TODO replace to the other randomized program of people from CAES
    pvsim = world.start('CSV', sim_start=START, datafile=PV_DATA)
    rtusim = world.start('RTUSim', step_size = 60)

    # Instantiate models
    grid = pypower.Grid(gridfile=GRID_FILE).children
    houses = hhsim.ResidentialLoads(sim_start=START,
                                    profile_file=PROFILE_FILE, # file with household profiles
                                    grid_name=GRID_NAME).children
    pvs = pvsim.PV.create(20)
    #rtus = rtusim.Sensors()
    monitor = rtusim.Monitor(addr=5)


    # Connect entities - this defines the data flow between the simulators 
    connect_buildings_to_grid(world, houses, grid)
    connect_randomly(world, pvs, [e for e in grid if 'node' in e.eid], 'P')
#    mosaik.util.connect_many_to_one(world, pvs, monitor, 'P')
#    world.connect(pvs[5], monitor, 'P')

    # Database
    db = world.start('DB', step_size=60, duration=END)
    hdf5 = db.Database(filename='demo.hdf5')
    connect_many_to_one(world, houses, hdf5, 'P_out')
    connect_many_to_one(world, pvs, hdf5, 'P')

    monitor_nodes = [e for e in grid if e.eid.split("-")[1] in ('branch_4', 'branch_10', 'branch_16')]
    mosaik.util.connect_many_to_one(world, monitor_nodes, monitor, ('P_from', 'P'), ('I_real', 'I'))


    nodes = [e for e in grid if e.type in ('RefBus, PQBus')]
    connect_many_to_one(world, nodes, hdf5, 'P', 'Q', 'Vl', 'Vm', 'Va')

    branches = [e for e in grid if e.type in ('Transformer', 'Branch')]
    connect_many_to_one(world, branches, hdf5,
                        'P_from', 'Q_from', 'P_to', 'P_from')

    # Web visualization
    webvis = world.start('WebVis', start_date=START, step_size=60)
    webvis.set_config(ignore_types=['Topology', 'ResidentialLoads', 'Grid',
                                    'Database', 'Monitor', 'Registers'])
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
            'cls': 'gen',
            'attr': 'P',
            'unit': 'P [W]',
            'default': 0,
            'min': -10000,
            'max': 0,
        },
    })


def connect_buildings_to_grid(world, houses, grid):
    buses = filter(lambda e: e.type == 'PQBus', grid)
    buses = {b.eid.split('-')[1]: b for b in buses}
    house_data = world.get_data(houses, 'node_id')
    for house in houses:
        node_id = house_data[house]['node_id']
        world.connect(house, buses[node_id], ('P_out', 'P'))

#def refresh_topology(grid, switch_settings):



if __name__ == '__main__':
    main()
