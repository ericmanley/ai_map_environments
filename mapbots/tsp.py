import osmnx as ox
import networkx as nx
import random
from matplotlib import pyplot as plt
import copy
import numpy as np
from geopy.geocoders import Nominatim
from geopy.distance import great_circle



class TravellingSalesAgentProblem:

    def __init__(self,place='Des Moines, Iowa, USA', num_locations=10, locations=[], random_seed=None):
        """
        Initializes a new instance of the TravellingSalesAgentProblem.

        :param place: The area for which to construct the problem, defaults to 'Des Moines, Iowa, USA'.
        :param num_locations: The total number of locations (including the origin) to visit, defaults to 10.
        :param locations: A list of addresses or point names to include as specific destinations. If the size of this
            list is less than num_locations+1, random locations will also be generated
        :param random_seed: An optional seed for the random number generator to ensure reproducible results.
        """
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

        all_locations = [] # names for all locations on the map we'll use
        self._location_name_to_id_map = {}

        for address in locations:
            try:
                # Attempt to geocode the address
                lat, lng = ox.geocode(address)
                
                # Find the nearest node to the geocoded location
                nearest_node = ox.distance.nearest_nodes(self._street_graph, Y=lat, X=lng)
                nearest_node_point = (self._street_graph.nodes[nearest_node]['y'], self._street_graph.nodes[nearest_node]['x'])
                # Calculate the distance between the geocoded point and the nearest node
                distance = great_circle((lat, lng), nearest_node_point).meters
                
                # Check if the nearest node is actually within the graph's bounds
                if distance <= 1000:
                    all_locations.append(address)
                    self._location_name_to_id_map[address] = nearest_node
                else:
                    print(f"Found {address} too far away - probably outside the bounds of the map. Skipping.")
            except Exception as e:
                # Handle cases where geocoding fails or no nearest node is found
                print(f"Failed to find {address}. Skipping.")

        # determine how many more locations to generate randomly
        # selecting num_locations total from the graph nodes (intersections) 
        # plus 1 for the origin
        num_random = (num_locations+1)-len(all_locations)

        # randomly select num_locations from the graph nodes (intersections) plus 1 for the origin
        if num_random > 0:
            random_locations = random.sample(list(self._street_graph.nodes()),num_random)
            for loc in random_locations:
                loc_name = self._get_location_name(loc)
                self._location_name_to_id_map[loc_name] = loc
                all_locations.append(loc_name)

        self._origin_name = all_locations[0]
        self._destination_names = all_locations[1:]

        # cache all travel times
        print("calculating travel times - this may take some time")
        self._travel_times = self._calculate_pairwise_destination_costs()



    def _calculate_pairwise_destination_costs(self):
        """
        Calculates the travel time costs between all pairs of locations (including the origin and destinations)
        identified by their names. It uses the shortest path by travel time between each pair.

        :return: A dictionary of dictionaries, where costs[start][end] represents the travel time from 'start' to 'end'.
        """
        costs = {}

        # Iterate over all starting locations by name
        for start in self._location_name_to_id_map.keys():
            # Initialize a sub-dictionary for this start location
            costs[start] = {}

            # Iterate over all ending locations by name
            for end in self._location_name_to_id_map.keys():
                if start != end: # Ensure start and end are not the same location
                    # Find the shortest path by travel time between start and end locations
                    path = ox.shortest_path(self._street_graph,self._location_name_to_id_map[start],self._location_name_to_id_map[end],weight="travel_time")
                    
                    # loop over and accumulate travel time for the whole path 
                    total_travel_time = 0
                    from_loc = path[0]
                    for to_loc in path[1:]:
                        total_travel_time += self._street_graph.get_edge_data(from_loc, to_loc)[0]["travel_time"]
                        from_loc = to_loc

                    # Store the total travel time from start to end in the costs dictionary
                    costs[start][end] = total_travel_time
                else:
                    costs[start][end] = 0 # If start and end are the same, the travel cost is zero
        return costs

    def get_origin_location(self):
        return self._origin_name
    
    def get_destination_locations(self):
        return self._destination_names[:]
    
    def route_travel_time(self,route):
        """
        Calculates the total travel time for a specified route, starting from the origin,
        visiting each location in the order given by the route, and then returning to the origin.

        :param route: A list of location names representing the order in which locations are visited.
        :return: The total travel time for the entire route, including the return to the origin.
        """
        total_travel_time = 0
        from_loc = self._origin_name
        for to_loc in route:
            total_travel_time += self._travel_times[from_loc][to_loc]
            from_loc = to_loc
        total_travel_time += self._travel_times[from_loc][self._origin_name]
        return total_travel_time

    def _get_full_route(self,location_order=None):
        """
        Constructs the full route as a list of node IDs in the street graph, starting from the origin,
        visiting each location in the specified order, and returning to the origin at the end.

        :param location_order: An optional list of location names representing the order in which locations are visited.
                            If None, uses the default order of destinations stored in self._destination_names.
        :return: A list of node IDs representing the path through the street graph for the entire route.
        """
        if not location_order:
            location_order = self._destination_names

        # Iterate through each pair of consecutive locations, find the route between them, and accumulate it on to the full path
        from_loc = self._origin_name
        route_path = []
        for to_loc in location_order:
            from_loc_id = self._location_name_to_id_map[from_loc]
            to_loc_id = self._location_name_to_id_map[to_loc]
            route_path += ox.shortest_path(self._street_graph,from_loc_id,to_loc_id,weight="travel_time")[:-1]
            from_loc = to_loc
        # Do the same thing for the final destination back to the origin
        from_loc_id = self._location_name_to_id_map[from_loc]
        to_loc_id = self._location_name_to_id_map[self._origin_name]
        route_path += ox.shortest_path(self._street_graph,from_loc_id,to_loc_id,weight="travel_time")
        
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
    

    def _reverse_geocode(self, lat, lon):
        """Reverse geocode to get the address of a latitude and longitude."""
        try:
            geolocator = Nominatim(user_agent="DrakeCS143TSPExercises")
            location = geolocator.reverse((lat, lon), exactly_one=True)
            if location:
                return location.address
            return None
        except:
            return None

    def _get_intersection_name(self, node_id):
        """Construct an intersection name from the nearest edges to the node."""
        # Get edges connected to the node
        edges = list(self._street_graph.edges(node_id, data=True))
        if edges:
            streets = {edge[2].get('name') for edge in edges if edge[2].get('name')}
            if streets:
                return ' and '.join(sorted(streets))
        return None

    def _get_location_name(self, node_id):
        """
        Tries to come up with a descriptive name for a location. First it tries to use the 
        Nominatim service. Then it tries to name it based on the streets. Finally, it just uses the node id.
        """
        address = self._reverse_geocode(self._street_graph.nodes[node_id]['y'], self._street_graph.nodes[node_id]['x'])
        if address:
            return address
        
        intersection_name = self._get_intersection_name(node_id)
        if intersection_name:
            return intersection_name
        
        return str(node_id) #unknown location


    def _format_location_names(self,text, max_line_length=20):
        """
        Tries to grab a descriptive substring from the beginning of a place name
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

    def display_map(self,route=None):
        """
        Visualizes the map with the origin, destinations, and optionally a specified route.
        If a route is provided, it displays the route with a color gradient and directional arrows,
        showing the order number on top of each location
        Otherwise, it shows only the origin and destinations with their descriptive names

        :param route: An optional list of location names representing the travel route. If None, only the origin and destinations are displayed.
        """
        # If no specific route is provided, plot the graph and mark the origin and destinations
        if not route:
            fig, ax = ox.plot_graph(self._street_graph, bgcolor="gray", edge_color="white", node_size=0, show=False, close=False)

            # Plot each destination
            for destination in self._destination_names:
                destination_node_id = self._location_name_to_id_map[destination]
                destination_x = self._street_graph.nodes[destination_node_id]['x']
                destination_y = self._street_graph.nodes[destination_node_id]['y']
                ax.scatter(destination_x, destination_y, c='#228b22', s=200, label='Destination', zorder=4)
                formatted_destination = self._format_location_names(str(destination))
                ax.text(destination_x, destination_y, str(formatted_destination), color='black', fontsize=10, ha='center', va='center', zorder=6)
                
            # Plot the origin
            origin_id = self._location_name_to_id_map[self._origin_name]
            origin_x = self._street_graph.nodes[origin_id]['x']
            origin_y = self._street_graph.nodes[origin_id]['y']
            ax.scatter(origin_x, origin_y, c='purple', s=200, label='Origin', zorder=5)
            formatted_origin = self._format_location_names(str(self._origin_name))
            ax.text(origin_x, origin_y, str(formatted_origin), color='black', fontsize=10, ha='center', va='center', zorder=6)
                
        else:
            # A specific route is provided - get the full route and plot it with gradient colors and directional arrows
            full_route = self._get_full_route(location_order=route)
            fig, ax = ox.plot_graph(self._street_graph, bgcolor="gray", edge_color="white", node_size=0, show=False, close=False)

            # Get the x and y coordinates of each node in the route
            xs = [self._street_graph.nodes[node]['x'] for node in full_route]
            ys = [self._street_graph.nodes[node]['y'] for node in full_route]

            colormap = plt.cm.rainbow # color map for the route
            # Draw the route with a color gradient and directional arrows at intervals
            num_segments = len(full_route) - 1
            for i in range(num_segments):
                normalized_position = i / num_segments
                segment_color = colormap(normalized_position)
                x1, y1, x2, y2 = self._add_offset_to_line(xs[i], ys[i], xs[i+1], ys[i+1], offset_distance=0.0005)
                ax.plot([x1, x2], [y1, y2], color=segment_color, linewidth=4, zorder=3)
                # Annotation with an arrow indicating direction - do it every 10 segments
                if i % 10 == 0:
                    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),arrowprops=dict(arrowstyle="-|>",color="black", lw=2),zorder=4)

            # A dot for each destination and a number for their order along the route
            for destination_node_idx in range(len(route)):
                destination_node_id = self._location_name_to_id_map[route[destination_node_idx]]
                destination_x = self._street_graph.nodes[destination_node_id]['x']
                destination_y = self._street_graph.nodes[destination_node_id]['y']
                ax.scatter(destination_x, destination_y, c='#228b22', s=200, label='Destination', zorder=4)
                ax.text(destination_x, destination_y, str(destination_node_idx+1), color='black', fontsize=12, ha='center', va='center', zorder=6)
                
            # Plot the origin in another color
            origin_id = self._location_name_to_id_map[self._origin_name]
            origin_x = self._street_graph.nodes[origin_id]['x']
            origin_y = self._street_graph.nodes[origin_id]['y']
            ax.scatter(origin_x, origin_y, c='purple', s=200, label='Origin', zorder=5)

        # Explicitly draw the updated figure
        ax.figure.canvas.draw()

        plt.show()



