import osmnx as ox
import networkx as nx
import random
from matplotlib import pyplot as plt
import copy
#import matplotlib.colors as mcolors
import numpy as np
from geopy.geocoders import Nominatim

def reverse_geocode(lat, lon):
    """Reverse geocode to get the address of a latitude and longitude."""
    try:
        geolocator = Nominatim(user_agent="DrakeCS143TSPExercises")
        location = geolocator.reverse((lat, lon), exactly_one=True)
        if location:
            return location.address
        return None
    except:
        return None

def get_intersection_name(G, node_id):
    """Construct an intersection name from the nearest edges to the node."""
    # Get edges connected to the node
    edges = list(G.edges(node_id, data=True))
    if edges:
        streets = {edge[2].get('name') for edge in edges if edge[2].get('name')}
        if streets:
            return ' and '.join(sorted(streets))
    return None

def get_location_name(G, node_id):
    address = reverse_geocode(G.nodes[node_id]['y'], G.nodes[node_id]['x'])
    if address:
        return address
    
    intersection_name = get_intersection_name(G, node_id)
    if intersection_name:
        return intersection_name
    
    return str(node_id) #unknown location


def format_location_names(text, max_line_length=20):
    """
    Inserts newline characters into text to ensure that each line is at most max_line_length,
    trying not to break words.
    """
    parts = text.split(",")
    disp_text = parts[0]
    if len(disp_text) <= 7 and len(parts) > 1:
        disp_text += " "+parts[1]

    words = disp_text.split()
    lines = []
    current_line = []

    for word in words:
        # Check if adding the next word would exceed the max line length
        if len(' '.join(current_line + [word])) > max_line_length:
            lines.append(' '.join(current_line))
            current_line = [word]
        else:
            current_line.append(word)

    # Add the last line
    lines.append(' '.join(current_line))

    return '\n'.join(lines)

class TravellingSalesAgentProblem:

    def __init__(self,place='Des Moines, Iowa, USA', num_locations=10, locations=[], random_seed=None):
        if random_seed:
            random.seed(random_seed)  # Seed the random number generator for repeatable maps

        print("preparing map - this may take some time")
        # Load the street graph from OpenStreetMap data
        self._street_graph = ox.graph_from_place(place, network_type='drive')

        # Impute missing speed data and calculate travel times for all edges
        self._street_graph = ox.add_edge_speeds(self._street_graph, fallback=40)  # Assuming 40kph for missing data
        self._street_graph = ox.add_edge_travel_times(self._street_graph)

        # Add location IDs to nodes for easier reference
        for node in self._street_graph.nodes:
            self._street_graph.nodes[node]["location_id"] = node

        all_locations = []
        self._location_map = {}

        for address in locations:
            try:
                # Attempt to geocode the address
                lat, lng = ox.geocode(address)
                
                # Find the nearest node to the geocoded location
                nearest_node = ox.distance.nearest_nodes(self._street_graph, Y=lat, X=lng)
                
                # Check if the nearest node is actually within the graph's bounds
                if nearest_node in self._street_graph.nodes:
                    all_locations.append(address)
                    self._location_map[address] = nearest_node
                else:
                    print(f"Found {address} outside the bounds of the map. Skipping.")
            except Exception as e:
                # Handle cases where geocoding fails or no nearest node is found
                print(f"Failed to find {address}. Skipping.")

        num_random = (num_locations+1)-len(all_locations)

        # randomly select num_locations from the graph nodes (intersections) plus 1 for the origin
        if num_random > 0:
            random_locations = random.sample(list(self._street_graph.nodes()),num_random)
            for loc in random_locations:
                loc_name = get_location_name(self._street_graph, loc)
                self._location_map[loc_name] = loc
                all_locations.append(loc_name)

        self._origin = all_locations[0]
        self._destinations = all_locations[1:]

        # cache all travel times
        print("calculating travel times - this may take some time")
        self._travel_times = self._calculate_pairwise_destination_costs()



    def _calculate_pairwise_destination_costs(self):
        costs = {}
        #locations = self._destinations[:]+[self._origin]
        for start in self._location_map.keys():
            costs[start] = {}
            for end in self._location_map.keys():
                if start != end:
                    path = ox.shortest_path(self._street_graph,self._location_map[start],self._location_map[end],weight="travel_time")
                    total_travel_time = 0
                    from_loc = path[0]
                    for to_loc in path[1:]:
                        total_travel_time += self._street_graph.get_edge_data(from_loc, to_loc)[0]["travel_time"]
                        from_loc = to_loc
                    costs[start][end] = total_travel_time
                else:
                    costs[start][end] = 0
        return costs


    # def get_location_info(self, node_id):
    #     """
    #     Retrieves detailed information about a specific location (node) within the map.

    #     :param node_id: The identifier of the node for which information is requested.
    #     :return: A dictionary containing the node's information or None if the node does not exist.
    #     """
    #     if node_id in self._street_graph.nodes:
    #         node_info = copy.deepcopy(self._street_graph.nodes[node_id])
    #         return node_info
    #     else:
    #         return None

    def get_origin_location(self):
        return self._origin
    
    def get_destination_locations(self):
        return self._destinations[:]
    
    def route_travel_time(self,route):
        # commenting out the old method that recalculated every time this was called
        """
        full_route = self._get_full_route(location_order=route)
        total_travel_time = 0
        from_loc = full_route[0]
        for to_loc in full_route[1:]:
            total_travel_time += self._street_graph.get_edge_data(from_loc, to_loc)[0]["travel_time"]
            from_loc = to_loc
        return total_travel_time
        """
        total_travel_time = 0
        from_loc = self._origin
        for to_loc in route:
            total_travel_time += self._travel_times[from_loc][to_loc]
            from_loc = to_loc
        total_travel_time += self._travel_times[from_loc][self._origin]
        return total_travel_time


    
    def _get_full_route(self,location_order=None):
        if not location_order:
            location_order = self._destinations

        from_loc = self._origin
        route_path = []
        for to_loc in location_order:
            from_loc_id = self._location_map[from_loc]
            to_loc_id = self._location_map[to_loc]
            route_path += ox.shortest_path(self._street_graph,from_loc_id,to_loc_id,weight="travel_time")[:-1]
            from_loc = to_loc
        from_loc_id = self._location_map[from_loc]
        to_loc_id = self._location_map[self._origin]
        route_path += ox.shortest_path(self._street_graph,from_loc_id,to_loc_id,weight="travel_time")

        #print("route_path",route_path)
        
        return route_path

    def _add_offset_to_line(self,x1, y1, x2, y2, offset_distance):
        """
        function generated by ChatGPT

        Calculate a perpendicular offset for a line segment and apply it.
        
        :param x1, y1: Coordinates of the start point of the line segment.
        :param x2, y2: Coordinates of the end point of the line segment.
        :param offset_distance: The distance by which to offset the line.
        :return: Adjusted coordinates (x1, y1, x2, y2) with offset applied.
        """
        # Calculate the direction vector (dx, dy) of the line segment
        dx = x2 - x1
        dy = y2 - y1
        
        # Calculate the length of the direction vector
        length = np.sqrt(dx**2 + dy**2)
        
        # Calculate the perpendicular offset vector (perp_dx, perp_dy)
        perp_dx = -dy / length * offset_distance
        perp_dy = dx / length * offset_distance
        
        # Apply the offset to the original coordinates
        return x1 + perp_dx, y1 + perp_dy, x2 + perp_dx, y2 + perp_dy

    def display_map(self,route=None):

        if not route:
            #fig, ax = ox.plot_graph_route(self._street_graph,[self._origin], route_color="blue", bgcolor="gray", edge_color="white", node_size=0, show=False, close=False)
            fig, ax = ox.plot_graph(self._street_graph, bgcolor="gray", edge_color="white", node_size=0, show=False, close=False)

            for destination in self._destinations:
                destination_node_id = self._location_map[destination]
                destination_x = self._street_graph.nodes[destination_node_id]['x']
                destination_y = self._street_graph.nodes[destination_node_id]['y']
                ax.scatter(destination_x, destination_y, c='#228b22', s=200, label='Destination', zorder=4)
                formatted_destination = format_location_names(str(destination))
                ax.text(destination_x, destination_y, str(formatted_destination), color='black', fontsize=8, ha='center', va='center', zorder=6)
                

            origin_id = self._location_map[self._origin]
            origin_x = self._street_graph.nodes[origin_id]['x']
            origin_y = self._street_graph.nodes[origin_id]['y']
            ax.scatter(origin_x, origin_y, c='purple', s=200, label='Origin', zorder=5)
            formatted_origin = format_location_names(str(self._origin))
            ax.text(origin_x, origin_y, str(formatted_origin), color='black', fontsize=8, ha='center', va='center', zorder=6)
                
        else:
            full_route = self._get_full_route(location_order=route)
            #fig, ax = ox.plot_graph_route(self._street_graph,full_route, route_color="blue", bgcolor="gray", edge_color="white", node_size=0, show=False, close=False)
            fig, ax = ox.plot_graph(self._street_graph, bgcolor="gray", edge_color="white", node_size=0, show=False, close=False)


            # Get the x and y coordinates of each node in the route
            xs = [self._street_graph.nodes[node]['x'] for node in full_route]
            ys = [self._street_graph.nodes[node]['y'] for node in full_route]

            colormap = plt.cm.rainbow
            num_segments = len(full_route) - 1
            for i in range(num_segments):
                normalized_position = i / num_segments
                segment_color = colormap(normalized_position)
                x1, y1, x2, y2 = self._add_offset_to_line(xs[i], ys[i], xs[i+1], ys[i+1], offset_distance=0.0005)
                ax.plot([x1, x2], [y1, y2], color=segment_color, linewidth=4, zorder=3)
                # Annotation with an arrow indicating direction
                if i % 10 == 0:
                    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),arrowprops=dict(arrowstyle="-|>",color="black", lw=2),zorder=4)

            for destination_node_idx in range(len(route)):
                destination_node_id = self._location_map[route[destination_node_idx]]
                destination_x = self._street_graph.nodes[destination_node_id]['x']
                destination_y = self._street_graph.nodes[destination_node_id]['y']
                ax.scatter(destination_x, destination_y, c='#228b22', s=200, label='Destination', zorder=4)
                ax.text(destination_x, destination_y, str(destination_node_idx+1), color='black', fontsize=12, ha='center', va='center', zorder=6)
                

            origin_id = self._location_map[self._origin]
            origin_x = self._street_graph.nodes[origin_id]['x']
            origin_y = self._street_graph.nodes[origin_id]['y']
            ax.scatter(origin_x, origin_y, c='purple', s=200, label='Origin', zorder=5)

            # # Plot the destinations
            # for destination in self._destinations:
            #     destination_id = self._location_map[destination]
            #     destination_node = self._street_graph.nodes[destination_id]
            #     #print(destination_node)
            #     ax.scatter(destination_node['x'], destination_node['y'], c='#228b22', s=200, label='Destination', zorder=4)

        # Explicitly draw the updated figure
        ax.figure.canvas.draw()

        plt.show()



