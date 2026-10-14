#state machine for robot will be coded later
from collections import deque

forward, backward, left, right = "forward", "backward", "left", "right"
curr_node = 0
board_graph = {
    # start box
    0:  {forward: 35,   backward: None, left: 18,   right: 1},
    18: {forward: 19,   backward: 0,    left: None, right: None},
    1:  {forward: 2,    backward: 0,    left: None, right: None},

    # right wall (heading up, branches go left)
    2:  {forward: 4,    backward: 1,  left: 3,    right: None},
    3:  {forward: None, backward: 2,  left: None, right: None},
    4:  {forward: 6,    backward: 2,  left: 5,    right: None},
    5:  {forward: None, backward: 4,  left: None, right: None},
    6:  {forward: 8,    backward: 4,  left: 7,    right: None},
    7:  {forward: None, backward: 6,  left: None, right: None},
    8:  {forward: 10,   backward: 6,  left: 9,    right: None},
    9:  {forward: None, backward: 8,  left: None, right: None},
    10: {forward: 12,   backward: 8,  left: 11,   right: None},
    11: {forward: None, backward: 10, left: None, right: None},
    12: {forward: 14,   backward: 10, left: 13,   right: None},
    13: {forward: None, backward: 12, left: None, right: None},
    14: {forward: 16,   backward: 12, left: 15,   right: None},
    15: {forward: None, backward: 14, left: None, right: None},
    16: {forward: None, backward: 14, left: 17,   right: None},
    17: {forward: None, backward: 16, left: None, right: None},

    # left wall (heading up, branches go right)
    19: {forward: 21,   backward: 18, left: None, right: 20},
    20: {forward: None, backward: 19, left: None, right: None},
    21: {forward: 23,   backward: 19, left: None, right: 22},
    22: {forward: None, backward: 21, left: None, right: None},
    23: {forward: 25,   backward: 21, left: None, right: 24},
    24: {forward: None, backward: 23, left: None, right: None},
    25: {forward: 27,   backward: 23, left: None, right: 26},
    26: {forward: None, backward: 25, left: None, right: None},
    27: {forward: 29,   backward: 25, left: None, right: 28},
    28: {forward: None, backward: 27, left: None, right: None},
    29: {forward: 31,   backward: 27, left: None, right: 30},
    30: {forward: None, backward: 29, left: None, right: None},
    31: {forward: 33,   backward: 29, left: None, right: 32},
    32: {forward: None, backward: 31, left: None, right: None},
    33: {forward: None, backward: 31, left: None, right: 34},
    34: {forward: None, backward: 33, left: None, right: None},

    # centre line (heading up, left/right arms)
    35: {forward: 36,   backward: 0,  left: None, right: None},
    36: {forward: 39,   backward: 35, left: 37,   right: 38},
    37: {forward: None, backward: 36, left: None, right: None},
    38: {forward: None, backward: 36, left: None, right: None},
    39: {forward: 42,   backward: 36, left: 40,   right: 41},
    40: {forward: None, backward: 39, left: None, right: None},
    41: {forward: None, backward: 39, left: None, right: None},
    42: {forward: 45,   backward: 39, left: 43,   right: 44},
    43: {forward: None, backward: 42, left: None, right: None},
    44: {forward: None, backward: 42, left: None, right: None},
    45: {forward: 48,   backward: 42, left: 46,   right: 47},
    46: {forward: None, backward: 45, left: None, right: None},
    47: {forward: None, backward: 45, left: None, right: None},
    48: {forward: 51,   backward: 45, left: 49,   right: 50},
    49: {forward: None, backward: 48, left: None, right: None},
    50: {forward: None, backward: 48, left: None, right: None},
    51: {forward: None, backward: 48, left: 52,   right: 53},
    52: {forward: None, backward: 51, left: None, right: None},
    53: {forward: None, backward: 51, left: None, right: None},
}


from collections import deque

def find_path(graph, curr_node, target):
    #implemetation of BFS
    if curr_node == target:
        return [curr_node]
    parents = {curr_node: None}
    queue = deque([curr_node]) #adds discovered but not visited nodes
    while queue:
        node = queue.popleft()
        for neighbour in graph[node].values():
            if neighbour is None or neighbour in parents:
                continue
            parents[neighbour] = node
            if neighbour == target:
                # walk back through the parents to rebuild the path
                path = [neighbour]
                while parents[path[-1]] is not None:
                    path.append(parents[path[-1]])
                return path[::-1]
            queue.append(neighbour)
    return None


def next_node(graph, current, target):
    #gets next node
    path = find_path(graph, current, target)
    if path is None or len(path) < 2:
        return None
    return path[1]


def next_direction(graph, current, target):
    #get direction of next node
    nxt = next_node(graph, current, target)
    if nxt is None:
        return None
    for direction, neighbour in graph[current].items():
        if neighbour == nxt:
            return direction