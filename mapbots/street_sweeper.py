"""
This code is an environment for use with the Street Sweeper Bot assignment.
"""

import osmnx as ox
import networkx as nx
import random
from matplotlib import pyplot as plt
import copy

class StreetSweeperBotEnvironment:
    
    def __init__(self,place='Des Moines, Iowa, USA',map_number=None):
        
        print("Setting up the map. This may take a few minutes.")
        
        #allow for repeatable maps through random seeding
        if map_number:
            random.seed(map_number)
            
        # Load the graph for a specific area
        self.__street_graph = ox.graph_from_place(place, network_type='drive')
        
        # impute speed on all edges missing data, treat missing values as 40kph ~25mph
        self.__street_graph = ox.add_edge_speeds(self.__street_graph,fallback=40)
        # calculate travel time (seconds) for all edges
        self.__street_graph = ox.add_edge_travel_times(self.__street_graph)
        
        # randomize dirty locations
        self.__initialize_dirt()
        
        # randomly choose a starting intersection for the bot
        self.__bot_location = random.choice(list(self.__street_graph.nodes()))

        # initialize the bot's route as just the starting location
        self.__bot_route = [self.__bot_location]
        
        # initialize battery life
        self.__battery_life = 72000 #an abstract number, equivalent to the number of seconds in 20 hours
        
        # intialize how much the bot cleaned
        self.__meters_cleaned = 0
        
        
    def __initialize_dirt(self):
        
        #we'll use these to determine how big this map is
        num_nodes = len(self.__street_graph.nodes)
        num_edges = len(self.__street_graph.edges)
        #print("Number of nodes and edges:",num_nodes, num_edges)
        
        # Initialize all streets as 'clean'
        for u, v, key in self.__street_graph.edges(keys=True):
            self.__street_graph[u][v][key]['cleanliness'] = 'clean'

        # Randomly determine the number of dirty regions
        # between a fifth and a half of 1 percent of intersections
        num_dirty_regions = random.randint(max(int(num_nodes*0.002),1), max(int(num_nodes*0.005),1))

        # Create dirty regions
        for _ in range(num_dirty_regions):
            # Choose a random node as the center of a dirty region
            center_node = random.choice(list(self.__street_graph.nodes()))

            # Random radius between 1 and 2000 meters
            radius = random.randint(1, 2000)

            # Get all nodes within this radius (in network distance)
            subgraph = nx.ego_graph(self.__street_graph, center_node, radius=radius, distance='length')

            # Mark edges within this radius as 'dirty'
            for u, v, key in subgraph.edges(keys=True):
                if self.__street_graph.has_edge(u, v, key):
                    self.__street_graph[u][v][key]['cleanliness'] = 'dirty'
                    
    def display_map(self):
        # make dirty streets brown and clean streets white
        ec = ['brown' if data['cleanliness'] == 'dirty' else 'white' for u, v, key, data in self.__street_graph.edges(keys=True, data=True)]
        # display the route itself in blue
        fig, ax = ox.plot_graph_route(self.__street_graph,self.__bot_route, route_color="blue", bgcolor="gray", edge_color=ec, node_size=0, show=False, close=False)
        
        plt.show()
        
    def scan_next_streets(self):
        
        # a list of all the streets going out from this location
        next_streets_info = []
        
        # loop over all edges/streets that have the current node
        # as a starting point, u an v are the node ids of the two endpoints of the edge
        for u,v in self.__street_graph.out_edges(self.__bot_location):
            # prepare info dict for the starting point
            u_data = copy.deepcopy(self.__street_graph.nodes[u])
            u_data["location_id"] = u
            
            # prepare info dict for the ending point
            v_data = copy.deepcopy(self.__street_graph.nodes[v])
            v_data["location_id"] = v
            
            # copy the street data - we don't want them to be able to edit this,
            # so we make a copy
            street_data = copy.deepcopy(self.__street_graph.get_edge_data(u,v)[0])
            curr_street_info = {"start":u_data,"end":v_data,"street_data":street_data}
            
            next_streets_info.append(curr_street_info)
        return next_streets_info
    
    def move_to(self,other):
        
        # check if we can really move to that id
        if self.__street_graph.has_edge(self.__bot_location, other):
            
            # grab info about this street
            edge_info = self.__street_graph.get_edge_data(self.__bot_location, other)[0]
            
            # change the bot's location to the other end of the street
            self.__bot_location = other
            
            # add the new location to the route
            self.__bot_route.append(self.__bot_location)
            
            # subtract the travel time from the bot's battery life
            self.__battery_life -= edge_info["travel_time"]
            
            # return the id of the new location
            return self.__bot_location
        
        else:
            return None
        
    def clean_and_move_to(self,other):
        
        # check if we can really move there
        if self.__street_graph.has_edge(self.__bot_location, other):
            
            # cleaning costs 3 times what it takes to just move
            # so we subtract extra beyond what it takes to move
            edge_info = self.__street_graph.get_edge_data(self.__bot_location, other)[0]
            self.__battery_life -= 2*edge_info["travel_time"]
            
            # if this street isn't clean, we make it clean and count it
            # towards the total length of streets that have been cleaned
            if edge_info["cleanliness"] != "clean":
                self.__meters_cleaned += edge_info["length"]
                edge_info["cleanliness"] = "clean"
                
            # use the other method to actually make the move
            return self.move_to(other)
        else:
            return None
        
    
    def backup(self,how_many=1):
        """ this is necessary if the bot gets stuck with no outgoing streets
            if so, a free back up is allowed
        """
        for _ in range(how_many):
            self.__bot_route.pop() #remove the most recent node
        self.__bot_location = self.__bot_route[-1] #reset the location to the previous node
            
    def get_battery_life(self):
        return self.__battery_life
    
    def get_meters_cleaned(self):
        return self.__meters_cleaned
    
    def get_current_location(self):
        curr_loc = copy.deepcopy(self.__street_graph.nodes[self.__bot_location])
        curr_loc["location_id"] = self.__bot_location
        return curr_loc