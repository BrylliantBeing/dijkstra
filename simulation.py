import numpy as np
from scipy.spatial.distance import euclidean
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import dijkstra
from dotenv import dotenv_values
from RBT_stops import OSMHandler, apply_file_hardcore
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def dijkstraAlgorithm(roadNodes, roadConnections):
    n = len(roadNodes)
    adjecencyMatrix = lil_matrix((n, n))

    for connection in roadConnections:
        dist = euclidean(roadNodes[connection[0]], roadNodes[connection[1]])
        adjecencyMatrix[connection[0], connection[1]] = dist
        adjecencyMatrix[connection[1], connection[0]] = dist

    distances, predecessors = dijkstra(adjecencyMatrix.tocsr(), return_predecessors=True)
    print(distances)
    print(predecessors)

    return distances, predecessors

def linearInterpolation(nodes, start, end, d):
    path = []
    totalDist = euclidean(nodes[start], nodes[end])
    numPoints = int(totalDist / d)

    for i in range(numPoints):
        t = i / (numPoints - 1) if numPoints > 1 else 0
        point = tuple((1 - t) * a + t * b for a, b in zip(nodes[start], nodes[end]))
        path.append(point)

    return path

def visualize(roadNodes, roadConnections, path):
    movingSpeed = 0.00005

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')

    for connection in roadConnections:
        x = [roadNodes[connection[0]][0], roadNodes[connection[1]][0]]
        y = [roadNodes[connection[0]][1], roadNodes[connection[1]][1]]
        ax.plot(x, y, color='black', linewidth=0.5)

    runningPath = []
    for i in range(len(path) - 1):
        runningPath.extend(linearInterpolation(roadNodes, path[i], path[i + 1], movingSpeed))

    dot, = ax.plot([], [], 'go', markersize=5)

    def update(frame):
        if frame < len(runningPath):
            dot.set_data([runningPath[frame][0]], [runningPath[frame][1]])
        return dot,

    ani = animation.FuncAnimation(fig, update, frames=len(runningPath), interval=16, blit=True)
    plt.show()

def recreatePath(predecessors, origin_node, destination_node):
    lastNode = destination_node
    path = [lastNode]

    while lastNode != -9999:
        path.append(predecessors[origin_node][lastNode])
        lastNode = predecessors[origin_node][lastNode]
    path.pop(-1)
    return list(reversed(path))

def main():
    config = dotenv_values(".env")
    assets_dir = config["ASSETS_DIR"]

    handler = OSMHandler()
    apply_file_hardcore(handler, assets_dir, use_location=True)

    node_id_to_index = {}
    roadNodes = []
    roadConnections = []

    for way_nodes in handler.ways:
        for node1, node2 in zip(way_nodes[:-1], way_nodes[1:]):
            if node1.location.valid() and node2.location.valid():
                if node1.ref not in node_id_to_index:
                    node_id_to_index[node1.ref] = len(roadNodes)
                    roadNodes.append((node1.location.lon, node1.location.lat))
                if node2.ref not in node_id_to_index:
                    node_id_to_index[node2.ref] = len(roadNodes)
                    roadNodes.append((node2.location.lon, node2.location.lat))
                roadConnections.append((node_id_to_index[node1.ref], node_id_to_index[node2.ref]))

    origin_node = 0
    destination_node = len(roadNodes) - 1
    distances, predecessors = dijkstraAlgorithm(roadNodes, roadConnections)
    path = recreatePath(predecessors, origin_node, destination_node)
    np.set_printoptions(legacy='1.25')
    print("Writing distances")
    distances_length = len(distances)
    with open("distances.txt", "w") as f:
        curr_length = 1
        for distance in distances:
            if curr_length % 10 == 0:
                print(f"Distances: {curr_length}/{distances_length}")
            f.write("[")
            for d in distance:
                f.write(f"{d},")
            f.write("]\n")
    print("Writing predecessors")
    predecessors_length = len(predecessors)
    with open("predecessors.txt", "w") as f:
        curr_length = 1
        for distance in predecessors:
            if curr_length % 10 == 0:
                print(f"Predecessors: {curr_length}/{predecessors_length}")
            f.write("[")
            for d in distance:
                f.write(f"{d},")
            f.write("]\n")
    with open("path.txt", "w") as f:    
        f.write(str(path))
    # visualize(roadNodes, roadConnections, path)

if __name__ == "__main__":
    main()
