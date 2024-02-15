"""
This code is an environment for use with the Street Sweeper World assignment.
"""

import osmnx as ox
import networkx as nx
import random
from matplotlib import pyplot as plt
import copy

class StreetSweeperWorld:
    
    def __init__(self,place='Des Moines, Iowa, USA',map_number=None,initial_battery_life=72000):
        
        print("Setting up the map. This may take a few minutes.")
        
        #allow for repeatable maps through random seeding
        if map_number:
            random.seed(map_number)
            
        # Load the graph for a specific area
        self._street_graph = ox.graph_from_place(place, network_type='drive')
        
        # impute speed on all edges missing data, treat missing values as 40kph ~25mph
        self._street_graph = ox.add_edge_speeds(self._street_graph,fallback=40)
        # calculate travel time (seconds) for all edges
        self._street_graph = ox.add_edge_travel_times(self._street_graph)

        # add the location id to the node info
        for node in self._street_graph.nodes:
            self._street_graph.nodes[node]["location_id"] = node
        
        self._dirty_regions = []

        # randomize dirty locations
        self._initialize_dirt()
        
        # randomly choose a starting intersection for the bot
        self._bot_location = random.choice(list(self._street_graph.nodes()))

        # initialize the bot's route as just the starting location
        self._bot_route = [self._bot_location]
        
        # initialize battery life
        self._battery_life = initial_battery_life #an abstract number, 72000 is equivalent to the number of seconds in 20 hours
        
        # intialize how much the bot cleaned
        self._meters_cleaned = 0
    
    def _initialize_dirt(self):
        
        #we'll use these to determine how big this map is
        num_nodes = len(self._street_graph.nodes)
        num_edges = len(self._street_graph.edges)
        #print("Number of nodes and edges:",num_nodes, num_edges)
        
        # Initialize all streets as 'clean'
        for u, v, key in self._street_graph.edges(keys=True):
            self._street_graph[u][v][key]['cleanliness'] = 'clean'

        # Randomly determine the number of dirty regions
        # between a fifth and a half of 1 percent of intersections
        num_dirty_regions = random.randint(max(int(num_nodes*0.002),1), max(int(num_nodes*0.005),1))

        # Create dirty regions
        for _ in range(num_dirty_regions):
            # Choose a random node as the center of a dirty region
            center_node = random.choice(list(self._street_graph.nodes()))

            # Random radius between 1 and 2000 meters
            radius = random.randint(1, 2000)

            self._dirty_regions.append({"center":center_node,"size":radius})

            # Get all nodes within this radius (in network distance)
            subgraph = nx.ego_graph(self._street_graph, center_node, radius=radius, distance='length')

            # Mark edges within this radius as 'dirty'
            for u, v, key in subgraph.edges(keys=True):
                if self._street_graph.has_edge(u, v, key):
                    self._street_graph[u][v][key]['cleanliness'] = 'dirty'
                    
    def display_map(self):
        # make dirty streets brown and clean streets white
        ec = ['brown' if data['cleanliness'] == 'dirty' else 'white' for u, v, key, data in self._street_graph.edges(keys=True, data=True)]
        # display the route itself in blue
        fig, ax = ox.plot_graph_route(self._street_graph,self._bot_route, route_color="blue", bgcolor="gray", edge_color=ec, node_size=0, show=False, close=False)
        
        plt.show()

    def _get_full_edge_data(self,u,v):
        # prepare info dict for the starting point
        u_data = copy.deepcopy(self._street_graph.nodes[u])
        # prepare info dict for the ending point
        v_data = copy.deepcopy(self._street_graph.nodes[v])
        # copy the street data - we don't want them to be able to edit this,
        # so we make a copy
        edge_data = copy.deepcopy(self._street_graph.get_edge_data(u,v)[0])
        full_street_info = {"start":u_data,"end":v_data,"street_data":edge_data}
        return full_street_info

    def _get_outgoing_streets_from_location(self,node_id,outgoing=True):
        # a list of all the streets going out from this location
        next_streets_info = []
        
        # loop over all edges/streets that have the current node
        # as a starting point, u an v are the node ids of the two endpoints of the edge
        edges_to_scan = None
        if outgoing:
            edges_to_scan = self._street_graph.out_edges(node_id)
        else:
            edges_to_scan = self._street_graph.in_edges(node_id)
        for u,v in edges_to_scan:
            curr_street_info = self._get_full_edge_data(u,v)
            next_streets_info.append(curr_street_info)
        return next_streets_info

    def scan_next_streets(self):
        return self._get_outgoing_streets_from_location(self._bot_location,outgoing=True)
        
    def move_to(self,other):
        
        # check if we can really move to that id
        if self._street_graph.has_edge(self._bot_location, other):
            
            # grab info about this street
            edge_info = self._street_graph.get_edge_data(self._bot_location, other)[0]
            
            # change the bot's location to the other end of the street
            self._bot_location = other
            
            # add the new location to the route
            self._bot_route.append(self._bot_location)
            
            # subtract the travel time from the bot's battery life
            self._battery_life -= edge_info["travel_time"]
            
            # return the id of the new location
            return self._bot_location
        
        else:
            return None
        
    def clean_and_move_to(self,other):
        
        # check if we can really move there
        if self._street_graph.has_edge(self._bot_location, other):
            
            # cleaning costs 3 times what it takes to just move
            # so we subtract extra beyond what it takes to move
            edge_info = self._street_graph.get_edge_data(self._bot_location, other)[0]
            self._battery_life -= 2*edge_info["travel_time"]
            
            # if this street isn't clean, we make it clean and count it
            # towards the total length of streets that have been cleaned
            if edge_info["cleanliness"] != "clean":
                self._meters_cleaned += edge_info["length"]
                edge_info["cleanliness"] = "clean"
                
            # use the other method to actually make the move
            return self.move_to(other)
        else:
            return None
        
    
    def backup(self,how_many=1):
        """ this is necessary if the bot gets stuck with no outgoing streets
            backing up costs the same as moving in the correct direction
        """
        for _ in range(how_many):
            removed_location = self._bot_route.pop() #remove the most recent node
            self._bot_location = self._bot_route[-1] #reset the location to the previous node
            edge_info = self._street_graph.get_edge_data(self._bot_location, removed_location)[0]
            self._battery_life -= edge_info["travel_time"]
        
            
    def get_battery_life(self):
        return self._battery_life
    
    def get_meters_cleaned(self):
        return self._meters_cleaned
    
    def get_current_location(self):
        curr_loc = copy.deepcopy(self._street_graph.nodes[self._bot_location])
        #curr_loc["location_id"] = self._bot_location
        return curr_loc
    
class FullyObservableStreetSweeperWorld(StreetSweeperWorld):
    
    def __init__(self, place='Des Moines, Iowa, USA', map_number=None, initial_battery_life=72000):
        super().__init__(place=place, map_number=map_number, initial_battery_life=initial_battery_life)
    
    # Example method to look up information about any node in the graph
    def get_location_info(self, node_id):
        if node_id in self._street_graph.nodes:
            node_info = copy.deepcopy(self._street_graph.nodes[node_id])
            return node_info
        else:
            return None

    # Example method to look up information about any edge in the graph
    def get_street_info(self, start_node, end_node):
        if self._street_graph.has_edge(start_node, end_node):
            street_info = self._get_full_edge_data(start_node,end_node)
            return street_info
        else:
            return None
        
    def get_outgoing_streets_from_location(self, node_id):
        return self._get_outgoing_streets_from_location(node_id,outgoing=True)
    
    def get_incoming_streets_from_location(self, node_id):
        return self._get_outgoing_streets_from_location(node_id,outgoing=False)
    
    def get_dirty_regions(self):
        return self._dirty_regions


testworld = FullyObservableStreetSweeperWorld()
print(testworld.get_current_location())
print(testworld.get_outgoing_streets_from_location(testworld.get_current_location()["location_id"]))
print(testworld.get_incoming_streets_from_location(testworld.get_current_location()["location_id"]))
print(testworld.get_dirty_regions())