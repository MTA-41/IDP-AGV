#from line_follower import line_follow
from movement_functions import *

left_motor, right_motor = create_motors()

move_forward(left_motor, right_motor, 1)

turn_left(left_motor, right_motor, 1)

turn_right(left_motor, right_motor, 1)

# while GO COMMAND is True:
#     line_follow()