import json
i=1
#rtu_info is a dict of the branch name and "True" or "False" indicator, e.g. {"branch_1: 1. branch_16: 0"}


def topology_refresh(ref_topology, rtu_info=""):
    newtopology = "" #string
    if rtu_info:
        with open(ref_topology) as ref_topology_file:    
            data = json.load(ref_topology_file)
        for branch in rtu_info.keys():
            for b in data['branch']:
                if branch in b: # b is a list
                    if b[-1] !=rtu_info[branch]:
                        b[-1] = rtu_info[branch]  
    conn = connected_buses(data, 'tr_pri')
    for n in data['bus']:
        if n[0] not in conn:
            #print("Disconnect bus {}".format(n[0]))
            if n[1] != 'NONE':
                n[1] = 'NONE'
        else:
            if n[1] == 'NONE':
                n[1] = 'PQ'

    with open('data/topo/demo_mv_grid.json', 'w') as outfile:
        json.dump(data, outfile, sort_keys = True, indent = 4)
    with open('data/topo/demo_mv_grid'+i+'.json', 'w') as outfile2:
        json.dump(data, outfile2, sort_keys = True, indent = 4)
        i=i+1
    newtopology='data/topo/demo_mv_grid.json'
    # save 
    return newtopology
    

def connected_buses(json_data, init_bus='tr_pri'):
    g=Graph()
    g.clear() # create a new graph each time because we add edges if they exist. 
    connected_nodes=[]
    nodes={}
    for node in json_data['bus']:
        node_name = node[0]
        nodes[node_name] = g.add_vertex(node_name)
    branches={}
    for branch in json_data['branch']:
        branch_name = branch[0]
        if branch[-1]:
            branches[branch_name] = g.add_edge((branch[1], branch[2]))
    for branch in json_data['trafo']:
        branch_name = branch[0]
        branches[branch_name] = g.add_edge((branch[1], branch[2]))
    connected_nodes = []
    for node in json_data['bus']:
        if g.find_path(init_bus, node[0]) is not None:
            connected_nodes.append(node[0])
    return connected_nodes


class Graph(object):

    def __init__(self, graph_dict={}):
        """ initializes a graph object """
        self.__graph_dict = graph_dict

    def vertices(self):
        """ returns the vertices of a graph """
        return list(self.__graph_dict.keys())

    def edges(self):
        """ returns the edges of a graph """
        return self.__generate_edges()

    def add_vertex(self, vertex):
        """ If the vertex "vertex" is not in 
            self.__graph_dict, a key "vertex" with an empty
            list as a value is added to the dictionary. 
            Otherwise nothing has to be done. 
        """
        if vertex not in self.__graph_dict:
            self.__graph_dict[vertex] = []

    def add_edge(self, edge):
        """ assumes that edge is of type set, tuple or list; 
            between two vertices can be multiple edges! 
        """
        edge = set(edge)
        (vertex1, vertex2) = tuple(edge)
        if vertex1 in self.__graph_dict:
            self.__graph_dict[vertex1].append(vertex2)
            if vertex2 in self.__graph_dict:
                self.__graph_dict[vertex2].append(vertex1)
            else:
                self.__graph_dict[vertex2] = [vertex1]
        else:
            self.__graph_dict[vertex1] = [vertex2]
            if vertex2 in self.__graph_dict:
                self.__graph_dict[vertex2].append(vertex1)
            else:
                self.__graph_dict[vertex2] = [vertex1]

    def find_path(self, start_vertex, end_vertex, path=None):
        """ find a path from start_vertex to end_vertex 
            in graph """
        if path == None:
            path = []
        graph = self.__graph_dict
        path.append(start_vertex)
        if start_vertex == end_vertex:
            return path
        if start_vertex not in graph:
            return None
        for vertex in graph[start_vertex]:
            if vertex not in path:
                extended_path = self.find_path(vertex, end_vertex, path)
                if extended_path: 
                    return extended_path
        return None

    def __generate_edges(self):
        """ A static method generating the edges of the 
            graph "graph". Edges are represented as sets 
            with one (a loop back to the vertex) or two 
            vertices 
        """
        edges = []
        for vertex in self.__graph_dict:
            for neighbour in self.__graph_dict[vertex]:
                if {neighbour, vertex} not in edges:
                    edges.append({vertex, neighbour})
        return edges

    def __str__(self):
        res = "vertices: "
        for k in self.__graph_dict:
            res += str(k) + " "
        res += "\nedges: "
        for edge in self.__generate_edges():
            res += str(edge) + " "
        return res

    def clear(self):
        self.__graph_dict = {}
