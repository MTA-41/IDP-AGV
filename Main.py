from machine import Pin, PWM, ADC
from time import *
 
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



###### OPERATION FUNCTIONS ######
right = True   # if true, robot operates on right side of board
grab = False
box_present = False  # false if no box in loading bay
filled_bay = False # false if loading bay is full





 
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