#from line_follower import line_follow
from initialise_components import *
from track_mapping import *
from line_follower import *


#assumptions while coding, th line follower function returns true when a junction is detected. 
#the next junction is updated through logic, 

while running:
    if state == "home":
        curr_junction = 0
    if state == "get_parcel":
        target = 3
    while not end:
        if line_follow():
            prev_node = curr_node
            curr_node = nxt_node
            nxt_node = next_node(board_graph, curr_node, target)
        if nxt_node is None:        # next_node returns None once curr_node == target
            end = True


