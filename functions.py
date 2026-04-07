import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import os
import random

def distanceP2P(p1, p2):
    """
    Calculate the Euclidean distance between two points in a spherical surface.
    
    Parameters:
    p1 (tuple): A tuple representing the coordinates of the first point (Longitude1, Latitude1).
    p2 (tuple): A tuple representing the coordinates of the second point (Longitude2, Latitude2).
    
    Returns:
    float: The Euclidean distance between the two points.
    """
    lon1, lon2, lat1, lat2 = np.radians(p1[0]), np.radians(p2[0]), np.radians(p1[1]), np.radians(p2[1])
    deltaSigma = np.acos(np.sin(lat1) * np.sin(lat2) + np.cos(lat1) * np.cos(lat2) * np.cos(lon1 - lon2))
    if np.isnan(deltaSigma):
        deltaSigma = 0
    R = 6378000  # Radius of the Earth in Meters
    d = R * deltaSigma
    return d

def distanceP2LS(p, ls):
    """
    Calculate the distance from a point to a line segment.
    
    Parameters:
    p (tuple): A tuple representing the coordinates of the point (Longitude, Latitude).
    ls (tuple): A tuple of two tuples representing the coordinates of the line segment (Point1, Point2).
    
    Returns:
    tuple: The distance from the point to the line segment and the point on the line segment (distance, point).
    """
    gradient_ls = (ls[1][1] - ls[0][1]) / (ls[1][0] - ls[0][0])
    gradient_p = -1 / gradient_ls
    x = (gradient_ls * ls[0][0] - gradient_p * p[0] + p[1] - ls[0][1]) / (gradient_ls - gradient_p)
    y = gradient_p * (x - p[0]) + p[1]
    point = (x, y)
    distance = distanceP2P(p, point)
    return distance, point

def pointFromCentreToPoint(centre, theta, distance):
    """
    Calculate the coordinates of a point at a given distance from a centre point in a spherical surface.
    
    Parameters:
    centre (tuple): A tuple representing the coordinates of the centre point (Longitude, Latitude).
    theta (tuple): An angle in degrees representing the direction from the centre point to the new point. 0 is North, 90 is East.
    distance (float): The distance from the centre point to the new point.
    
    Returns:
    tuple: The coordinates of the new point (Longitude, Latitude).
    """
    R = 6378000  # Radius of the Earth in Meters
    theta = np.radians(theta)
    lat1 = np.radians(centre[1])
    lon1 = np.radians(centre[0])

    lat2 = np.asin(np.sin(lat1) * np.cos(distance / R) +
                     np.cos(lat1) * np.sin(distance / R) * np.cos(theta))

    lon2 = lon1 + np.atan2(np.sin(theta) * np.sin(distance / R) * np.cos(lat1),
                             np.cos(distance / R) - np.sin(lat1) * np.sin(lat2))

    return (np.degrees(lon2), np.degrees(lat2))

def index_pattern(n):
    """
    Generate a pattern for the index of the directions list to fill out the hexagonal grid.
    
    Parameters:
    n (int): The number of points to generate.
    
    Returns:
    list: A list of integers representing the index pattern.
    """
    result = []
    count = 0
    cycle = 1
    while count < n:
        added = [0] + sorted(cycle * [1,2,3,4,5,6])
        added.pop(-1)
        result += added
        count+=len(added)
        cycle += 1
        

    return result[:n]

def countZeros(n):
    """
    Count the number of zeros in a list.
    
    Parameters:
    n (list): A list of integers.
    
    Returns:
    int: The number of zeros in the list.
    """
    count = 0
    for i in n:
        if i == 0:
            count += 1
    return count
    
def plotBusStops(bus_stops, colour_way, config, file_name):
    """
    Plot the bus stops on a map.
    
    Parameters:
    
    Returns:
    None
    """
    for i in bus_stops:
        plt.scatter(i.lon, i.lat, 
                 color=colour_way["bus_stop"],
                 s=float(config["AMENITY_POINT_SIZE"]) * 1.5,
                 )
    
    plt.axis('square')
    if config["ASSETS_DIR"] == "assets\\philippines-latest.osm.pbf" or config["ASSETS_DIR"] == "assets\\zamboanga.osm.pbf" or config["ASSETS_DIR"] == "assets\\zamboanga-small.osm.pbf":
        plt.xlim(float(config["MIN_LON"]), float(config["MAX_LON"]))
        plt.ylim(float(config["MIN_LAT"]), float(config["MAX_LAT"]))
    custom_legend = [
        Line2D([0], [0], color=colour_way["road"], lw=2, label='Roads'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=colour_way["amenity"], markersize=8, label='Amenities'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor=colour_way["bus_stop"], markersize=8, label='Bus Stops')
    ]

    plt.legend(handles=custom_legend, loc = 'lower right')
    plt.savefig(f"{os.path.join(config['OUTPUT_DIR'], file_name)}.jpg", dpi=int(config["DPI"]), bbox_inches = 'tight')
    
def activationFunction(x, inflection_point):
    if x < inflection_point:
        return x
    else:
        return inflection_point + (x - inflection_point)**2
    
def takeTop(population, elitism_size):
    top = [[np.inf,np.inf]]*elitism_size
    for index, sample in enumerate(population):
        if sample.fitness < top[elitism_size-1][0]:
            top.append([sample.fitness, index])
            top = sorted(top, key=lambda x: x[0], reverse=False)[:elitism_size]
    return top

def tournamentSelection(population, tournament_size):
    """
    Select a sample from the population using tournament selection.
    
    Parameters:
    population (list): A list of samples.
    tournament_size (int): The size of the tournament.
    
    Returns:
    Sample: The selected sample.
    """
    tournament = np.random.choice(population, size=tournament_size, replace=False)
    winner = min(tournament, key=lambda x: x.fitness)
    return winner

def crossover(parent1, parent2):
    """
    Perform crossover between two parents to create a child.
    
    Parameters:
    parent1 (Sample): The first parent sample.
    parent2 (Sample): The second parent sample.
    Returns:
    Sample: The two child samples created from the parents.
    """
    cutoff_point = int(np.floor(random.random() * len(parent1)))
    random.shuffle(parent1)
    random.shuffle(parent2)
    child1 = parent1[:cutoff_point] + parent2[cutoff_point:]
    child2 = parent2[:cutoff_point] + parent1[cutoff_point:]
    return child1, child2