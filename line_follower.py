#import servo and motor unit codes
#import numpy as np
import time
from track_mapping import *
#import matplotlib.pyplot as plt
from int import *
from machine import Pin, PWM, ADC



# while loop occurs in main loop to ensure it keeps going - this is for one 'step'
# currently got basic step infrastructure (I loop control)
# for two sensor need the idea of comparison

motion_log = []
at_junction = Falserunning = True
state = "home"
nxt_state = "get_parcel"
curr_node = None
nxt_node = None
prev_node = None
end = False

def line_follow():

    go = True
    while go == True:
        if not at_junction:
            if right_light_sensor == 0 and left_light_sensor == 0 and front_light_sensor == 1 and back_light_sensor == 1:
                print('f')
                motion_log.append('forward')
                move_forward(left_motor, right_motor, 0.5)

            elif right_light_sensor == 1 and left_light_sensor == 0 and front_light_sensor == 0 and back_light_sensor == 1:
                print('r')
                motion_log.append('right')
                turn_right(left_motor, right_motor, 0.5)

            elif right_light_sensor == 0 and left_light_sensor == 1 and front_light_sensor == 0 and back_light_sensor == 1:
                print('l')
                motion_log.append('left')
                turn_left(left_motor, right_motor, 0.5) 

            elif right_light_sensor == 0 and left_light_sensor == 1 and front_light_sensor == 1 and back_light_sensor == 1:
                print('jun')
                motion_log = []
                junction_motion(curr_node, nxt_node)
                return True #interrupt to show junction boundary. 

def junction_motion(current, next):
    try:
        if next is None:                 # no next node: we've arrived
            left_motor.off()
            right_motor.off()
            return

        # which way is 'next' from 'current'? (label from the track graph)
        direction = None
        for label, node in board_graph[current].items():
            if node == next:
                direction = label

        start = time.ticks_ms()

        if direction == "forward":
            motion_log.append('forward')
            move_forward(left_motor, right_motor, 0.5)
            # keep going until both side sensors are clear of the junction
            while left_light_sensor == 1 or right_light_sensor == 1:
                pass

        elif direction == "left" or direction == "right":
            motion_log.append(direction)
            if direction == "left":
                turn_left(left_motor, right_motor, 0.5)
            else:
                turn_right(left_motor, right_motor, 0.5)

            left_old_line = False
            while True:
                if front_light_sensor == 0:
                    left_old_line = True         # swung off the old line
                elif left_old_line and front_light_sensor == 1 \
                        and left_light_sensor == 0 and right_light_sensor == 0:
                    break                        # front is on the new line

        else:
            print("junction_motion: can't do", direction)   # e.g. a U-turn
            left_motor.off()
            right_motor.off()

    finally:
        at_junction = False
     
line_follow()

    
