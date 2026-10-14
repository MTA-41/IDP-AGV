#import servo and motor unit codes
import numpy as np
import time
import matplotlib.pyplot as plt
from initialise_components import move_forward, move_right, move_left
from machine import Pin, PWM, ADC


right_light_sensor = Pin(18, Pin.IN)
left_light_sensor = Pin(19, Pin.IN)
front_light_sensor = Pin(20, Pin.IN)
back_light_sensor = Pin(21, Pin.IN)


# while loop occurs in main loop to ensure it keeps going - this is for one 'step'
# currently got basic step infrastructure (I loop control)
# for two sensor need the idea of comparison

def line_follow():

    go = True
    while go == True:

        if right_light_sensor == 0 and left_light_sensor == 0 and front_light_sensor == 1 and back_light_sensor == 1:
            print('f')
            move_forward(0.5)

        elif right_light_sensor == 1 and left_light_sensor == 0 and front_light_sensor == 0 and back_light_sensor == 1:
            print('r')
            move_right(0.5)

        elif right_light_sensor == 0 and left_light_sensor == 1 and front_light_sensor == 0 and back_light_sensor == 1:
            print('l')
            move_left(0.5) 

        elif right_light_sensor == 0 and left_light_sensor == 1 and front_light_sensor == 1 and back_light_sensor == 1:
            print('jun')
            move_left(1)



line_follow()










#past = np.zeros(50)
# dt = 0.1
# integrals = []
# derivatives = []
# differences = []
# controls = []
# prev_diff = 0

# kp = 1.0
# ki = 1.0
# kd = 1.0

# read = reading()

# def PID_line_follow(read):

#     diff = read #INPUT FROM SENSOR AS SHOULD BE ZERO-ISH FROM BLACK
#     differences.append(diff)

#     #past.append(diff)

#     integral = diff * dt
#     integrals.append(integral)

#     deriv = (diff - prev_diff) / dt
#     derivatives.append(deriv)
#     prev_diff = diff

#     control = kp*diff + ki*integral + kd * deriv
#     controls.append(control)


#     # line follow logic
#     # control positive for clockwise

#     if control > diff:
#         turn_left()

#     elif control < diff:
#         turn_right()

#     else:
#         move_forward()


    
