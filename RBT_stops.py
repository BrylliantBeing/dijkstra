import osmium
from dotenv import dotenv_values
import matplotlib
matplotlib.use('Agg')  # Headless mode
import matplotlib.pyplot as plt
import os
import psutil
import ctypes
import time
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from shapely.ops import nearest_points
import functions
from matplotlib.lines import Line2D
import random
import numpy as np
import ast

class AmenityPoint:
    def __init__(self, point, tags):
        self.point = point
        self.tags = tags

class PopulationBusStops:
    def __init__(self, bus_stops, config, amenity_points):
        self.bus_stops = bus_stops
        self.fitness = self.fitness(config, amenity_points)
    def fitness(self, config, amenity_points):
        bus_points = []
        for i in self.bus_stops:
            bus_points.append(Point(i.lon, i.lat))
        bus_STRTree = STRtree(bus_points)
        costFunction = 0
        amenities = ast.literal_eval(config["IMPORTANT_AMENITIES"])
        for amenity_point in amenity_points:
            nearest_line = bus_STRTree.nearest(amenity_point.point)
            nearest_point = nearest_points(amenity_point.point, bus_points[nearest_line])[1]
            distance = functions.distanceP2P(nearest_point.xy, amenity_point.point.xy)

            try:
                amenity_weight = amenities[amenity_point.tags["amenity"]]
            except:
                amenity_weight = 1
            costFunction += functions.activationFunction(distance, int(config["BUS_STOP_DISTANCE"])) * amenity_weight
        #print(f"costFunction = {costFunction}")
        return costFunction
            
    def __repr__(self):
        return f"PopulationBusStops(bus_stops={self.bus_stops}, fitness={self.fitness})"

class BusStop:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.line_segments = []

    def __repr__(self):
        return f"BusStop(id={self.id}, lon={self.lon}, lat={self.lat})"

class OSMHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.ways = []
        
        config = dotenv_values(".env")
    
        self.min_lon = float(config["MIN_LON"])
        self.max_lon = float(config["MAX_LON"])
        self.min_lat = float(config["MIN_LAT"])
        self.max_lat = float(config["MAX_LAT"])
        self.counter = 0
        self.important_amenities = list(ast.literal_eval(config["IMPORTANT_AMENITIES"]).keys())
        # self.f = open("amenities.txt", "a")
        self.way_types = set()
        
    def node(self, n):
        self.counter += 1
        in_bounds = n.location.valid() and \
            self.min_lon <= n.location.lon <= self.max_lon and \
            self.min_lat <= n.location.lat <= self.max_lat
        if in_bounds:
            tags = dict(n.tags)
            if tags != {}:       
                try:
                    if tags["amenity"] in self.important_amenities:
                        
                        node = {
                            "id": n.id,
                            "lon": n.location.lon,
                            "lat": n.location.lat,
                            "tags": tags
                        }
                        self.nodes.append(node)
                except KeyError:
                    pass
        if self.counter % 1000000 == 0:
            print(self.counter)
            
    def way(self, w):
        if w.is_way():
            
            self.counter += 1
            in_bounds = any(
                n.location.valid() and
                self.min_lon <= n.location.lon <= self.max_lon and
                self.min_lat <= n.location.lat <= self.max_lat
                for n in w.nodes
            )
            if self.counter % 1000000 == 0:
                print(self.counter)
            tags = dict(w.tags)
            
            if in_bounds: 
                if any(key in tags for key in ("highway", "foot")):
                    if any(key in tags for key in ("route")):
                        print("Route found")
                        pass
                    else:
                        self.way_types.add(tuple(sorted((tag.k, tag.v) for tag in w.tags)))
                        self.ways.append(list(w.nodes))
                # elif not any(key in tags for key in ("building", "waterway", "natural")):
                #     if tags !={}:
                #         self.f.write(f"{tags}\n")
            

#! Fix for the issue of not being able to kill threads. Needed with Windows apparently
def apply_file_hardcore(handler, filepath, use_location=True):
    def list_thread_ids():
        process = psutil.Process(os.getpid())
        threads = process.threads()
        return {thread.id for thread in threads}

    threads_before = list_thread_ids()

    handler.apply_file(filepath, use_location)

    threads_after = list_thread_ids()
    new_threads = threads_after - threads_before

    def kill_thread(thread_id):
        THREAD_TERMINATE = 0x0001
        handle = ctypes.windll.kernel32.OpenThread(THREAD_TERMINATE, False, thread_id)
        if not handle:
            print(f"Failed to open thread {thread_id}")
            return False

        result = ctypes.windll.kernel32.TerminateThread(handle, 0)
        ctypes.windll.kernel32.CloseHandle(handle)

        if result == 0:
            print(f"Failed to terminate thread {thread_id}")
            return False

        return True

    for thread_id in new_threads:
        kill_thread(thread_id)

def main():
    start_time = time.time()
    config = dotenv_values(".env")
    assets_dir = config["ASSETS_DIR"]
    colour_way = {
        "road": "#0000FF",
        "amenity": "#FF0000",
        "bus_stop": "#004949"
    }

    handler = OSMHandler()
    apply_file_hardcore(handler, assets_dir, use_location=True)

    #plt.plot(handler.x, handler.y, 'ro', markersize=1)

    # * Plotting the roads
    print("Plotting the Roads")
    
    road_line_segments = []
    
    for way_nodes in handler.ways:
        for node1, node2 in zip(way_nodes[:-1], way_nodes[1:]):
            if node1.location.valid() and node2.location.valid():
                # plot line segments
                # plt.plot(
                #     [node1.location.lon, node2.location.lon],
                #     [node1.location.lat, node2.location.lat],
                #     color=colour_way["road"],
                #     linestyle='solid',
                #     linewidth=float(config["WAY_WIDTH"])
                # )
                road_line_segments.append( LineString([(node1.location.lon,node1.location.lat), (node2.location.lon,node2.location.lat) ]) )
                # plot points
                # plt.plot(
                #     [node1.location.lon, node2.location.lon],
                #     [node1.location.lat, node2.location.lat],
                #     'o', markersize=1, color="yellow"
                # )
                
                
    amenities_points = []
    # * Plotting the amenities
    print("Plotting the Amenities")
    for node in handler.nodes:
        amenities_points.append(AmenityPoint(Point(node["lon"], node["lat"]), node["tags"]))
        # plt.scatter(node["lon"], node["lat"], 
        #          color = colour_way["amenity"],
        #          s=float(config["AMENITY_POINT_SIZE"]),
        #          )
        
    # plt.xlim(config["MIN_LON"], config["MAX_LON"])
    # plt.title("RBT Stops")
    # plt.xlabel("Longitude")
    # plt.ylabel("Latitude")
    
        
    file_name = config["ASSETS_DIR"].split("\\")[-1].split(".")[0]
    print(f"Saving map as {file_name}.jpg")


    # * 1. Generate a grid of bus stops on a grid
    init_bus_stops_count = int(config["INIT_BUS_STOPS_COUNT"])
    #
    
    if config["ASSETS_DIR"] == "assets\philippines-latest.osm.pbf":
        centre = (float(config["MIN_LON"]) + float(config["MAX_LON"])) / 2, (float(config["MIN_LAT"]) + float(config["MAX_LAT"])) / 2
    elif config["ASSETS_DIR"] == "assets\zamboanga.osm.pbf" or config["ASSETS_DIR"] == "assets\zamboanga-small.osm.pbf":
        centre = 122.0775 , 6.925
    else:
        centre = 122.0775 , 6.907
        
    # * 2. Create an STR Tree of the bus stops
    
    road_tree = STRtree(road_line_segments)
    
    bus_stop_distance = float(config["BUS_STOP_DISTANCE"])
    
    
        
    # * 3. Initialise multiple versions of populations of bus stops
    population = []
    step_size = float(config["RANDOM_STEP_SIZE"])
    random_step_size_range = (-step_size, step_size)
    for i in range(int(config["POPULATION_SIZE"])):
        # populate the hexagonal grid with bus stops
        bus_stops = [BusStop(id = 0, lon = centre[0], lat = centre[1])]
        direction_order = [0,120,180,240,300,360,60]
        index_pattern = functions.index_pattern(init_bus_stops_count-1)
        new_centre = centre
        for i in range(init_bus_stops_count-1):
            new_centre = functions.pointFromCentreToPoint(centre=new_centre + (random.uniform(*random_step_size_range),random.uniform(*random_step_size_range)), 
                                                          theta=direction_order[index_pattern[i]] + np.degrees(random.uniform(*np.multiply(random_step_size_range, 10))), 
                                                          distance=bus_stop_distance + random.uniform(*random_step_size_range)
                                                          )
            bus_stops.append(BusStop(id=i+1, lon=new_centre[0], lat=new_centre[1]))
            try:    
                if index_pattern[i+1] == 0:
                    multiplier = functions.countZeros(index_pattern[:i])
                    new_centre = functions.pointFromCentreToPoint(centre=centre, theta=0, distance=bus_stop_distance*multiplier)
            except IndexError:
                pass
        for bus_stop in bus_stops:
            
            query_point = Point(bus_stop.lon, bus_stop.lat)
            nearest_line = road_tree.nearest(query_point)
            snapped_point = nearest_points(query_point, road_line_segments[nearest_line])[1]
            bus_stop.lon, bus_stop.lat = snapped_point.xy
        population.append(PopulationBusStops(bus_stops, config, amenities_points))
        
    # * 4. Do Evolition Algorithm
    for i in range(int(config["MAX_GENERATIONS"])):
        new_population = []
        print(f"Generation {i+1}/{config['MAX_GENERATIONS']}")
        # * Tournament
        print("Tournament Selection")
        for i in range(int(config["POPULATION_SIZE"])-int(config["ELITISM_SIZE"])):
            winner = functions.tournamentSelection(population, int(config["TOURNAMENT_SIZE"]))
            new_population.append(winner)


        # * Crossover
        print("Crossover")
        crossover_toggle = 0
        crossover_prev_population = {"population": None, "index" : 0}
        for index, popu in enumerate(new_population):
            if random.random() < float(config["CROSSOVER_RATE"]):
                if crossover_toggle == 0:
                    crossover_prev_population["population"] = popu.bus_stops
                    crossover_prev_population["index"] = index
                    crossover_toggle = 1
                else:
                    child1, child2 = functions.crossover(crossover_prev_population["population"], popu.bus_stops)
                    new_population[crossover_prev_population["index"]]=PopulationBusStops(child1, config, amenities_points)
                    new_population[index]=PopulationBusStops(child2, config, amenities_points)
                    crossover_toggle = 0
        # * Mutation
        
        # * Elitism
        elitism_size = int(config["ELITISM_SIZE"])
        elitism_top_indecies = functions.takeTop(population, elitism_size)
        print(f"Elitism: {elitism_top_indecies}")
        for index in elitism_top_indecies:
            new_population.append(population[index[1]])
        population = new_population
        
        
    functions.plotBusStops(bus_stops, colour_way, config, file_name )
    
    
    plt.close('all')
    print(f"Execution time: {time.time() - start_time:.2f} seconds")
    #print(handler.way_types)
    os._exit(0)
if __name__ == "__main__":
    main()

