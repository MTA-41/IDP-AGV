from machine import Pin, PWM, ADC
from time import *
from collections import deque
 
#############  motor functions  ###########################
class Motor:
    def __init__(self, dirPin, PWMPin):
        self.mDir = Pin(dirPin, Pin.OUT)  # set motor direction pin
        self.pwm = PWM(Pin(PWMPin))  # set motor pwm pin
        self.pwm.freq(1000)  # set PWM frequency
        self.pwm.duty_u16(0)  # set duty cycle - 0=off
        
    def off(self):
        self.pwm.duty_u16(0)
        
    def Forward(self, speed=100):
        self.mDir.value(0)                     # forward = 0 reverse = 1 motor
        self.pwm.duty_u16(int(65535 * speed / 100))  # speed range 0-100 motor
 
    def Reverse(self, speed=100):
        self.mDir.value(1)
        self.pwm.duty_u16(int(65535 * speed / 100))
 
 
def move_forward(motor_left, motor_right, duration):
    motor_left.Forward()
    motor_right.Forward()
    sleep(duration)
    
 
def turn_left(motor_left, motor_right, duration):
    motor_left.off()
    motor_right.Forward()
    sleep(duration)
    
 
def turn_right(motor_left, motor_right, duration):
    motor_right.off()
    motor_left.Forward()
    sleep(duration)
    
 
def move_back(motor_left, motor_right, duration):
    motor_left.Reverse()
    motor_right.Reverse()
    sleep(duration)
    
 
def rotateacw90(motor_left, motor_right, duration=0.60):
    # motor_right.off()
    # motor_left.off()
    # move_forward(motor_left, motor_right, 0.6)
    motor_left.off()
    motor_right.off()
    motor_right.Forward()
    #print('rr')
    motor_left.Reverse()
    #print('rl')
    sleep(duration)                 # CHANGED: the rotation never waited, so it never turned
    motor_right.off()
    motor_left.off()
 
def rotatecw90(motor_left, motor_right, duration=0.60):
    # motor_right.off()
    # motor_left.off()
    # move_forward(motor_left, motor_right, 0.6)
    motor_right.off()
    motor_left.off()
    motor_left.Forward()
    print('rl')
    motor_right.Reverse()
    print('rr')
    sleep(duration)                 # CHANGED: same fix as above
    motor_right.off()
    motor_left.off()
 
############  light sensor function  #######################
def get_light_values(forward, backward, left, right):
    sensor_values = [right.value(), left.value(), forward.value(), backward.value()]
    return sensor_values
 
 
###########.  component declaration. #########################
 
button = Pin(17, Pin.IN, Pin.PULL_DOWN)

right_light_sensor = Pin(18, Pin.IN)
left_light_sensor = Pin(20, Pin.IN)
front_light_sensor = Pin(19, Pin.IN)
back_light_sensor = Pin(21, Pin.IN)
 
left_motor = Motor(dirPin=7, PWMPin=6)
right_motor = Motor(dirPin=4, PWMPin=5)
 
 
home = False
BOX_CONFIRM = 3         # all-three-sensors pattern must be seen this many reads in a row

box_armed = True        # False after a box has been handled, until the sensors clear it
box_reads = 0           # consecutive reads of the all-on pattern





###### OPERATION FUNCTIONS ######
right = True   # if true, robot operates on right side of board
grab = False
box_present = False  # false if no box in loading bay
filled_bay = False # false if loading bay is full














#state machine for robot will be coded later


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

def u_turn():
    # same sequence your junction 3 handler uses
    move_back(left_motor, right_motor, 0.6)
    rotateacw90(left_motor, right_motor)
    move_back(left_motor, right_motor, 0.6)
    rotateacw90(left_motor, right_motor)

# ---------------- junction debounce settings (counted in sensor reads) ----------------
JUNCTION_CONFIRM = 3    # junction pattern must be seen this many reads IN A ROW to count
JUNCTION_CLEAR = 20     # pattern must be ABSENT this many reads before another junction can count
 
# CHANGED: these live at module level now. junction_num used to be reset to 0
# at the top of every line_follow() call, so it never counted past 1.
junction_num = 0
junction_armed = True   # False from the moment a junction is reported until the sensors clear it
junction_reads = 0      # consecutive reads of the junction pattern
clear_reads = 0         # consecutive reads WITHOUT the junction pattern
button_flag = False

DELIVERY_FOLLOW_MS = 1500   # TUNE: how long to follow the line after junction 6 before turning back
delivery_deadline = None    # None = no delivery timer running


 
def line_follow():
    #get_button_flag()
    global junction_num, junction_armed, junction_reads, clear_reads
    global box_armed, box_reads
    global delivery_deadline

    if junction_num == 0:
        sleep(6)
        rotatecw90(left_motor, right_motor)
        move_forward(left_motor, right_motor, 0.5)

    go = True
 
    while go == True:

        right, left, front, back = get_light_values(front_light_sensor, back_light_sensor, left_light_sensor, right_light_sensor)
 
        on_junction = ((right == 0 and left == 1 and front == 1) or (right == 1 and left == 0 and front == 1))
        on_box = (right == 1 and left == 1 and front == 1)
 
        # ----- debounce bookkeeping -----
        if on_junction or on_box:
            junction_reads += 1
        else:
            junction_reads = 0

        if on_box:
            box_reads += 1
        else:
            box_reads = 0

        if on_junction or on_box:
            clear_reads = 0
        else:
            clear_reads += 1
            if clear_reads >= JUNCTION_CLEAR:
                junction_armed = True       # fully clear: both latches reset
                box_armed = True

        # ----- driving -----
        if right == 0 and left == 0 and front == 1:
            #print('f')
            move_forward(left_motor, right_motor, 0.001)

        elif right == 1 and left == 0 and front == 0:
            #print('r')
            turn_right(left_motor, right_motor, 0.001)

        elif right == 0 and left == 1 and front == 0:
            #print('l')
            turn_left(left_motor, right_motor, 0.001)

        elif on_junction:
            if junction_armed and junction_reads >= JUNCTION_CONFIRM:
                #print('JUNCTION')
                junction_armed = False
                return True
            move_forward(left_motor, right_motor, 0.001)

        if delivery_deadline is not None and ticks_diff(ticks_ms(), delivery_deadline) >= 0:
            delivery_deadline = None
        #print('DELIVERY U-TURN')
            rotateacw90(left_motor, right_motor)
            rotateacw90(left_motor, right_motor)
 
        # elif right == 0 and left == 0 and front == 0:
        #     print('DELIVERY')
        #     move_back(left_motor, right_motor, 0.5)
        #     rotateacw90(left_motor, right_motor)
        #     rotateacw90(left_motor, right_motor)
 
 
def junction_handling():
    global delivery_deadline

    if junction_num == 1:
        turn_left(left_motor, right_motor, 0.9)

    # CHANGED: this was a chain of separate ifs with >=, so once junction_num
    # reached 5+ every later case fired as well. Now one case per junction.
    if junction_num == 2:
        right_motor.off()
        left_motor.off()
        move_forward(left_motor, right_motor, 0.6)
        rotateacw90(left_motor, right_motor)
        #print(f"entering depot: {junction_num}")
 
    elif junction_num == 3:
        left_motor.off()
        right_motor.off()
        sleep(2)
        move_forward(left_motor, right_motor, 0.6)
        left_motor.off()
        right_motor.off()
        sleep(5)
        #move_back(left_motor, right_motor, 0.6)
        rotateacw90(left_motor, right_motor)
        #move_back(left_motor, right_motor, 0.6)
        rotateacw90(left_motor, right_motor)
        #print(f"u turn: {junction_num}")
 
    elif junction_num == 4:
        right_motor.off()
        left_motor.off()
        move_forward(left_motor, right_motor, 0.6)
        rotateacw90(left_motor, right_motor)
        #print(f"back on track: {junction_num}")
 
    elif junction_num == 5:
        move_forward(left_motor, right_motor, 0.1)
        #print("ignore depot")
 
    elif junction_num == 6:
        right_motor.off()
        left_motor.off()
        move_forward(left_motor, right_motor, 0.6)
        rotateacw90(left_motor, right_motor)    # CHANGED: was duration 0.1, far too short for 90 degrees
        delivery_deadline = ticks_add(ticks_ms(), DELIVERY_FOLLOW_MS)
        #print(f"enter delivery: {junction_num}")
        
 
    elif junction_num == 7:
        # NOTE: 7 is the delivery dead end, counted inside line_follow, so this never runs
        turn_right(left_motor, right_motor, 0.9)
        #print(f"enter delivery: {junction_num}")
 
    elif junction_num == 8:
        move_forward(left_motor, right_motor, 0.3)
        #print(f"enter delivery: {junction_num}")


    elif junction_num == 9:
        move_forward(left_motor, right_motor, 0.3)
        #print(f"enter delivery: {junction_num}")

    elif junction_num == 10:
        turn_right(left_motor, right_motor, 0.9)
        print(f"last corner: {junction_num}")

    elif junction_num >= 11:
        print('home')
        move_forward(left_motor, right_motor, 1)
        right_motor.off()
        left_motor.off()
        sleep(100)




# def get_button_flag():
#     if button.value() == 1:
#         if button_flag == False:
#             button_flag = True 
#         if button_flag== True:
#             button_flag = False 
                        
while True:
    #if button_flag:
    line_follow()
    junction_num += 1
    junction_handling()
    #get_button_flag()
    #print (button_flag)