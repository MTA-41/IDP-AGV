#import servo and motor unit codes
import numpy as np
import time
import matplotlib.pyplot as plt
from movement_functions import turn_left, turn_right, move_forward
from light_sensor import reading


# while loop occurs in main loop to ensure it keeps going - this is for one 'step'
# currently got basic step infrastructure (I loop control)
# for two sensor need the idea of comparison

# def line_follow():

#     if LIGHT SENSOR1 < value and LIGHT SENSOR2 < value:
#         STRAIGHT ONE

#     elif lightsensor1 > value:
#         left wheel turns more

#     elif lightsensor2 < value:
#         right wheel turns More 

#past = np.zeros(50)
dt = 0.1
integrals = []
derivatives = []
differences = []
controls = []
prev_diff = 0

kp = 1.0
ki = 1.0
kd = 1.0

read = reading()

def PID_line_follow(read):

    diff = read #INPUT FROM SENSOR AS SHOULD BE ZERO-ISH FROM BLACK
    differences.append(diff)

    #past.append(diff)

    integral = diff * dt
    integrals.append(integral)

    deriv = (diff - prev_diff) / dt
    derivatives.append(deriv)
    prev_diff = diff

    control = kp*diff + ki*integral + kd * deriv
    controls.append(control)


    # line follow logic
    # control positive for clockwise

    if control > diff:
        turn_left()

    elif control < diff:
        turn_right()

    else:
        move_forward()


    
