import osmnx as ox
import networkx as nx
import random
from matplotlib import pyplot as plt
import copy

class TravellingSalesAgentProblem:

    def __init__(self,place='Des Moines, Iowa, USA', num_locations=10, random_seed=None):
        if random_seed:
            random.seed(random_seed)  # Seed the random number generator for repeatable maps

        # Load the street graph from OpenStreetMap data
        self._street_graph = ox.graph_from_place(place, network_type='drive')

        # Impute missing speed data and calculate travel times for all edges
        self._street_graph = ox.add_edge_speeds(self._street_graph, fallback=40)  # Assuming 40kph for missing data
        self._street_graph = ox.add_edge_travel_times(self._street_graph)

        # Add location IDs to nodes for easier reference
        for node in self._street_graph.nodes:
            self._street_graph.nodes[node]["location_id"] = node

        # randomly select num_locations from the graph nodes (intersections) plus 1 for the origin
        random_locations = random.sample(list(self._street_graph.nodes()),num_locations+1)
        self._origin = random_locations[0]
        self._destinations = random_locations[1:]

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

    def get_origin_location(self):
        return self._origin
    
    def get_destination_locations(self):
        return self._destinations
    
    def route_travel_time(self,route):
        full_route = self._get_full_route(location_order=route)
        total_travel_time = 0
        from_loc = full_route[0]
        for to_loc in full_route[1:]:
            total_travel_time += self._street_graph.get_edge_data(from_loc, to_loc)[0]["travel_time"]
            from_loc = to_loc
        return total_travel_time
    
    def _get_full_route(self,location_order=None):
        if not location_order:
            location_order = self._destinations

        from_loc = self._origin
        route_path = []
        for to_loc in location_order:
            route_path += ox.shortest_path(self._street_graph,from_loc,to_loc,weight="travel_time")[:-1]
            from_loc = to_loc
        route_path += ox.shortest_path(self._street_graph,from_loc,self._origin,weight="travel_time")

        #print("route_path",route_path)
        
        return route_path



    def display_map(self,route=None):

        if not route:
            fig, ax = ox.plot_graph_route(self._street_graph,[self._origin], route_color="blue", bgcolor="gray", edge_color="white", node_size=0, show=False, close=False)
        else:
            full_route = self._get_full_route(location_order=route)
            fig, ax = ox.plot_graph_route(self._street_graph,full_route, route_color="blue", bgcolor="gray", edge_color="white", node_size=0, show=False, close=False)

            for destination_node_idx in range(len(route)):
                ax.text(self._street_graph.nodes[route[destination_node_idx]]['x'], self._street_graph.nodes[route[destination_node_idx]]['y'], str(destination_node_idx+1), color='black', fontsize=12, ha='center', va='center', zorder=6)

            # Get the x and y coordinates of each node in the route
            xs = [self._street_graph.nodes[node]['x'] for node in full_route]
            ys = [self._street_graph.nodes[node]['y'] for node in full_route]

            # Plot direction indicators
            for i in range(len(full_route) - 1):
                if i % 10 == 0:
                    start_x, start_y = xs[i], ys[i]
                    end_x, end_y = xs[i + 1], ys[i + 1]
                    
                    # Calculate the direction vector
                    dx = end_x - start_x
                    dy = end_y - start_y
                    
                    # Plot an arrow from start to end
                    ax.arrow(start_x, start_y, dx, dy, length_includes_head=True, head_width=0.004, head_length=0.004, fc='blue', ec='blue', zorder=2)
        

        ax.scatter(self._street_graph.nodes[self._origin]['x'], self._street_graph.nodes[self._origin]['y'], c='purple', s=100, label='Origin', zorder=5)

        # Plot the destinations
        for destination in self._destinations:
            destination_node = self._street_graph.nodes[destination]
            #print(destination_node)
            ax.scatter(destination_node['x'], destination_node['y'], c='#228b22', s=100, label='Destination', zorder=4)

        # Explicitly draw the updated figure
        ax.figure.canvas.draw()

        plt.show()


# testing
tsp = TravellingSalesAgentProblem()
tsp.display_map()
# print("origin",tsp.get_origin_location())
# dests = tsp.get_destination_locations()
# print("dests",dests)

# tsp.display_map(route=dests)
# print(tsp.route_travel_time(dests))
