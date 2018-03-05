"""
A simple RTU controller.

"""
import mosaik_api


META = {
    'models': {
        'SwitchAgent': {
            'public': True,
            'params': [],
            'attrs': ['switch_state'],
        },
    },
}


class Controller(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.agents = []

    def create(self, num, model):
        n_agents = len(self.agents)
        entities = []
        for i in range(n_agents, n_agents + num):
            eid = 'Agent_%d' % i
            self.agents.append(eid)
            entities.append({'eid': eid, 'type': model})

        return entities

    def step(self, time, inputs):
        commands = {}
        for agent_eid, attrs in inputs.items():
            values = attrs.get('switch_state', {})
            for model_eid, value in values.items():

                if value == 0:
                    #remove the branch from the topology file 
                elif value == 1:
                    #add the branch to the topology file if doesn't exist yet. 
                else:
                    #error wrong Switch setting

                if agent_eid not in commands:
                    commands[agent_eid] = {}
                if model_eid not in commands[agent_eid]:
                    commands[agent_eid][model_eid] = {}
                commands[agent_eid][model_eid]['delta'] = delta

        yield self.mosaik.set_data(commands)

        return time + 60 #this works only for Python versions >=3.3. 
        #For older versions use: raise StopIteration(time + 60)


def main():
    return mosaik_api.start_simulation(Controller())


if __name__ == '__main__':
    main()