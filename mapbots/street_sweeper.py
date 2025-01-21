"""
This code is an environment for use with the Street Sweeper World assignment.
"""

import osmnx as ox
import networkx as nx
import random
from matplotlib import pyplot as plt
import copy

class StreetSweeperWorld:
    """
    A simulation environment for a street sweeper bot operating in a specified geographical area.
    The environment is based on real-world map data and includes functionalities for moving the bot,
    tracking its path, and managing its battery life and cleaning operations.
    """
    
    def __init__(self, place='Des Moines, Iowa, USA', map_number=None, initial_battery_life=72000):
        """
        Initializes the street sweeper world environment with a specified location and optional parameters.
        
        :param place: The name of the area to load as the environment.
        :param map_number: Optional seed for random number generator to allow repeatable scenarios.
        :param initial_battery_life: The initial battery life for the bot, representing its operational time.
        """
        print("Setting up the map. This may take a few minutes.")
        
        if map_number:
            random.seed(map_number)  # Seed the random number generator for repeatable maps
        
        # Load the street graph from OpenStreetMap data
        self._street_graph = ox.graph_from_place(place, network_type='drive')
        
        # Impute missing speed data and calculate travel times for all edges
        self._street_graph = ox.add_edge_speeds(self._street_graph, fallback=40)  # Assuming 40kph for missing data
        self._street_graph = ox.add_edge_travel_times(self._street_graph)
        
        # Add location IDs to nodes for easier reference
        for node in self._street_graph.nodes:
            self._street_graph.nodes[node]["location_id"] = node
        
        self._dirty_regions = []  # To keep track of dirty regions
        
        self._initialize_dirt()  # Randomize dirty locations
        
        # Randomly choose a starting location for the bot
        self._bot_location = random.choice(list(self._street_graph.nodes()))
        self._bot_route = [self._bot_location]  # Initialize bot's route
        
        # Initialize battery life and cleaning metrics
        self._battery_life = initial_battery_life
        self._meters_cleaned = 0
    
    def _initialize_dirt(self):
        """
        Randomly marks certain regions of the map as dirty based on random selection of nodes
        and radii to define dirty areas.
        """
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
        """
        Displays the current map with dirty streets marked in brown and clean streets in white.
        The bot's route is highlighted in blue.
        """
        # make dirty streets brown and clean streets white
        ec = ['brown' if data['cleanliness'] == 'dirty' else 'white' for u, v, key, data in self._street_graph.edges(keys=True, data=True)]
        # display the route itself in blue
        fig, ax = ox.plot_graph_route(self._street_graph,self._bot_route, route_color="blue", bgcolor="gray", edge_color=ec, node_size=0, show=False, close=False)
        
        plt.show()

    def _get_full_edge_data(self,u,v):
        """
        Retrieves detailed information about a street (edge) including data about its start and end nodes.

        :param u: The starting node ID of the edge.
        :param v: The ending node ID of the edge.
        :return: A dictionary containing detailed information about the edge and its nodes.
        """
        # Deep copy ensures that changes to this data won't affect the original graph
        u_data = copy.deepcopy(self._street_graph.nodes[u])  # Start node data
        v_data = copy.deepcopy(self._street_graph.nodes[v])  # End node data
        edge_data = copy.deepcopy(self._street_graph.get_edge_data(u, v)[0])  # Edge data
        full_street_info = {"start": u_data, "end": v_data, "street_data": edge_data}
        return full_street_info

    def _get_outgoing_streets_from_location(self,node_id,outgoing=True):
        """
        Retrieves information about either outgoing or incoming streets from a specified node.

        :param node_id: The node ID from which streets are being queried.
        :param outgoing: Boolean flag indicating whether to fetch outgoing (True) or incoming (False) streets.
        :return: A list of dictionaries, each containing detailed information about a street.
        """
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
        """
        Retrieves information about all outgoing streets from the bot's current location.

        :return: A list of dictionaries, each containing detailed information about an outgoing street.
        """
        return self._get_outgoing_streets_from_location(self._bot_location,outgoing=True)
        
    def move_to(self,other):
        """
        Attempts to move the bot to another location if there is a direct street connection.

        :param other: The node ID of the location to move to.
        :return: The new location ID if the move is successful, None otherwise.
        """
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
        """
        Cleans the street and moves the bot to another location if there is a direct street connection.

        :param other: The node ID of the location to move to.
        :return: The new location ID if the move and clean operation are successful, None otherwise.
        """
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
        """
        Moves the bot backwards along its route a specified number of steps. Useful if the bot
        reaches a dead end or needs to retreat. Each backup operation costs as much battery life
        as moving forward.

        :param how_many: The number of steps to back up.
        """
        for _ in range(how_many):
            removed_location = self._bot_route.pop() #remove the most recent node
            self._bot_location = self._bot_route[-1] #reset the location to the previous node
            edge_info = self._street_graph.get_edge_data(self._bot_location, removed_location)[0]
            self._battery_life -= edge_info["travel_time"]
        
            
    def get_battery_life(self):
        """
        Retrieves the current battery life of the bot.

        :return: The current battery life.
        """
        return self._battery_life
    
    def get_meters_cleaned(self):
        """
        Retrieves the total length of streets that the bot has cleaned.

        :return: The total meters of streets cleaned.
        """
        return self._meters_cleaned
    
    def get_current_location(self):
        """
        Retrieves detailed information about the bot's current location.

        :return: A dictionary containing information about the current location.
        """
        curr_loc = copy.deepcopy(self._street_graph.nodes[self._bot_location])
        #curr_loc["location_id"] = self._bot_location
        return curr_loc
    
class FullyObservableStreetSweeperWorld(StreetSweeperWorld):
    """
    A subclass of StreetSweeperWorld that provides additional functionalities
    for querying detailed information about the street map, including specific
    locations, streets, and the ability to identify dirty regions within the map.
    This class allows for a fully observable environment where agents can
    access comprehensive data about the environment's current state.
    """

    def __init__(self, place='Des Moines, Iowa, USA', map_number=None, initial_battery_life=72000):
        """
        Initializes the FullyObservableStreetSweeperWorld with a specific location,
        an optional map number for repeatable environments, and an initial battery life
        for the street sweeping bot.

        :param place: The geographical area to load into the street map.
        :param map_number: An optional seed for generating repeatable maps.
        :param initial_battery_life: The initial battery life for the street sweeping bot.
        """
        super().__init__(place=place, map_number=map_number, initial_battery_life=initial_battery_life)
    
    def get_location_info(self, node_id):
        """
        Retrieves detailed information about a specific location (node) within the map.

        :param node_id: The identifier of the node for which information is requested.
        :return: A dictionary containing the node's information or None if the node does not exist.
        """
        if node_id in self._street_graph.nodes:
            node_info = copy.deepcopy(self._street_graph.nodes[node_id])
            return node_info
        else:
            return None

    def get_street_info(self, start_node, end_node):
        """
        Retrieves detailed information about a specific street (edge) within the map,
        identified by its start and end nodes.

        :param start_node: The starting node of the street.
        :param end_node: The ending node of the street.
        :return: A dictionary containing the street's information or None if the street does not exist.
        """
        if self._street_graph.has_edge(start_node, end_node):
            street_info = self._get_full_edge_data(start_node, end_node)
            return street_info
        else:
            return None
        
    def get_outgoing_streets_from_location(self, node_id):
        """
        Retrieves a list of all outgoing streets from a specified location.

        :param node_id: The identifier of the location (node) from which outgoing streets are requested.
        :return: A list of outgoing streets from the specified location.
        """
        return self._get_outgoing_streets_from_location(node_id, outgoing=True)
    
    def get_incoming_streets_from_location(self, node_id):
        """
        Retrieves a list of all incoming streets to a specified location.

        :param node_id: The identifier of the location (node) to which incoming streets are requested.
        :return: A list of incoming streets to the specified location.
        """
        return self._get_outgoing_streets_from_location(node_id, outgoing=False)
    
    def get_dirty_regions(self):
        """
        Retrieves a list of dirty regions, containing the center location and size
        generated in the StreetSweeperWorld_initialize_dirt method

        :return: A list of dirty regions within the map.
        """
        return self._dirty_regions


#doing some quick tests
#testworld = FullyObservableStreetSweeperWorld()
#print(testworld.get_current_location())
#print(testworld.get_outgoing_streets_from_location(testworld.get_current_location()["location_id"]))
#print(testworld.get_incoming_streets_from_location(testworld.get_current_location()["location_id"]))
#print(testworld.get_dirty_regions())